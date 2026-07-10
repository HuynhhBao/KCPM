import pytest
from unittest.mock import patch, MagicMock
from rest_framework.exceptions import ValidationError
from accounts.serializers import RegisterSerializer


class TestRegisterSerializerValidateCrossField:
    """
    White-box tests for RegisterSerializer.validate() — lines 98–157
    of backend/accounts/serializers.py.

    Strategy:
    - No real database is used (no @pytest.mark.django_db).
    - User.objects.filter() is patched at 'accounts.serializers.User'.
    - Each patch uses side_effect so the first call (email lookup) and
      the second call (username lookup) return independent mock objects.
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_filter_mock(first_return_value):
        """Return a mock queryset whose .first() yields *first_return_value*."""
        qs = MagicMock()
        qs.first.return_value = first_return_value
        return qs

    @staticmethod
    def _serializer_with_attrs(email="test@example.com", username="testuser"):
        """Instantiate a bare RegisterSerializer and attach minimal attrs."""
        serializer = RegisterSerializer.__new__(RegisterSerializer)
        return serializer, {"email": email, "username": username}

    # ------------------------------------------------------------------
    # Nhánh 1 — lines 113–122
    # if existing_email_user and existing_email_user.email_verified:
    #     raise ValidationError({'email': 'Email đã tồn tại'})
    # ------------------------------------------------------------------

    def test_TC1_branch1_hit_email_exists_and_verified(self):
        """
        Tests lines 113–122 (Branch 1 — HIT).

        Condition: email exists in DB AND email_verified=True.
        Expected : ValidationError raised with key 'email'.
        """
        email_user = MagicMock()
        email_user.email_verified = True

        serializer, attrs = self._serializer_with_attrs()

        with patch("accounts.serializers.User.objects.filter") as mock_filter:
            mock_filter.side_effect = [
                self._make_filter_mock(email_user),   # 1st call — email lookup
                self._make_filter_mock(None),          # 2nd call — username lookup (never reached)
            ]
            with pytest.raises(ValidationError) as exc_info:
                serializer.validate(attrs)

        assert "email" in exc_info.value.detail
        assert str(exc_info.value.detail["email"]) == "Email đã tồn tại"

    def test_TC2_branch1_miss_email_exists_not_verified(self):
        """
        Tests lines 113–122 (Branch 1 — MISS).

        Condition: email exists in DB BUT email_verified=False.
        Expected : Branch 1 is NOT triggered; no ValidationError from branch 1.
        """
        email_user = MagicMock()
        email_user.email_verified = False
        email_user.username = "other_user"

        username_user = MagicMock()
        username_user.pk = 99
        email_user.pk = 1

        serializer, attrs = self._serializer_with_attrs(
            email="test@example.com", username="testuser"
        )

        with patch("accounts.serializers.User.objects.filter") as mock_filter:
            mock_filter.side_effect = [
                self._make_filter_mock(email_user),
                self._make_filter_mock(None),  # no username conflict
            ]
            # Branch 3 would fire here because email_user.username != attrs username.
            # We only assert branch 1 does NOT raise 'Email đã tồn tại'.
            try:
                serializer.validate(attrs)
            except ValidationError as exc:
                assert "email" not in exc.detail, (
                    "Branch 1 must NOT raise 'Email đã tồn tại' when email_verified=False"
                )

    def test_TC3_branch1_miss_email_not_exists(self):
        """
        Tests lines 113–122 (Branch 1 — MISS).

        Condition: email does NOT exist in DB (existing_email_user is None).
        Expected : Branch 1 is NOT triggered.
        """
        serializer, attrs = self._serializer_with_attrs()

        with patch("accounts.serializers.User.objects.filter") as mock_filter:
            mock_filter.side_effect = [
                self._make_filter_mock(None),  # no email match
                self._make_filter_mock(None),  # no username match
            ]
            result = serializer.validate(attrs)

        assert result == attrs

    # ------------------------------------------------------------------
    # Nhánh 2 — lines 128–141
    # if existing_username_user and (not existing_email_user or
    #         existing_username_user.pk != existing_email_user.pk):
    #     raise ValidationError({'username': 'Tên đăng nhập đã tồn tại'})
    # ------------------------------------------------------------------

    def test_TC4_branch2_hit_username_exists_no_email_user(self):
        """
        Tests lines 128–141 (Branch 2 — HIT, sub-condition: not existing_email_user).

        Condition: username exists in DB; email does NOT exist in DB.
        Expected : ValidationError raised with key 'username'.
        """
        username_user = MagicMock()
        username_user.pk = 10

        serializer, attrs = self._serializer_with_attrs()

        with patch("accounts.serializers.User.objects.filter") as mock_filter:
            mock_filter.side_effect = [
                self._make_filter_mock(None),          # no email match
                self._make_filter_mock(username_user), # username match
            ]
            with pytest.raises(ValidationError) as exc_info:
                serializer.validate(attrs)

        assert "username" in exc_info.value.detail
        assert str(exc_info.value.detail["username"]) == "Tên đăng nhập đã tồn tại"

    def test_TC5_branch2_hit_username_exists_different_pk(self):
        """
        Tests lines 128–141 (Branch 2 — HIT, sub-condition: pk mismatch).

        Condition: username exists in DB; email also exists in DB but belongs
                   to a DIFFERENT user (pk differs).
        Expected : ValidationError raised with key 'username'.
        """
        email_user = MagicMock()
        email_user.email_verified = False
        email_user.pk = 1
        email_user.username = "testuser"  # same username → branch 3 won't fire

        username_user = MagicMock()
        username_user.pk = 2  # different pk

        serializer, attrs = self._serializer_with_attrs()

        with patch("accounts.serializers.User.objects.filter") as mock_filter:
            mock_filter.side_effect = [
                self._make_filter_mock(email_user),
                self._make_filter_mock(username_user),
            ]
            with pytest.raises(ValidationError) as exc_info:
                serializer.validate(attrs)

        assert "username" in exc_info.value.detail
        assert str(exc_info.value.detail["username"]) == "Tên đăng nhập đã tồn tại"

    def test_TC6_branch2_miss_same_pk(self):
        """
        Tests lines 128–141 (Branch 2 — MISS, same pk).

        Condition: username exists in DB; email also exists in DB and BOTH
                   records are the SAME user (pk identical).
        Expected : Branch 2 is NOT triggered.
        """
        shared_user = MagicMock()
        shared_user.email_verified = False
        shared_user.pk = 5
        shared_user.username = "testuser"  # same as attrs → branch 3 won't fire

        serializer, attrs = self._serializer_with_attrs()

        with patch("accounts.serializers.User.objects.filter") as mock_filter:
            mock_filter.side_effect = [
                self._make_filter_mock(shared_user),  # email lookup → same user
                self._make_filter_mock(shared_user),  # username lookup → same user
            ]
            result = serializer.validate(attrs)

        assert result == attrs

    def test_TC7_branch2_miss_username_not_exists(self):
        """
        Tests lines 128–141 (Branch 2 — MISS, username absent).

        Condition: username does NOT exist in DB.
        Expected : Branch 2 is NOT triggered.
        """
        serializer, attrs = self._serializer_with_attrs()

        with patch("accounts.serializers.User.objects.filter") as mock_filter:
            mock_filter.side_effect = [
                self._make_filter_mock(None),  # no email match
                self._make_filter_mock(None),  # no username match
            ]
            result = serializer.validate(attrs)

        assert result == attrs

    # ------------------------------------------------------------------
    # Nhánh 3 — lines 143–155
    # if existing_email_user and not existing_email_user.email_verified
    #         and existing_email_user.username != username:
    #     raise ValidationError({'username': 'Email này đang có đăng ký ...'})
    # ------------------------------------------------------------------

    def test_TC8_branch3_hit_pending_registration_different_username(self):
        """
        Tests lines 143–155 (Branch 3 — HIT).

        Condition: email exists in DB, email_verified=False, and the username
                   stored in DB differs from the username being registered now.
        Expected : ValidationError raised with key 'username' and the
                   'pending registration' message.
        """
        email_user = MagicMock()
        email_user.email_verified = False
        email_user.pk = 7
        email_user.username = "old_username"  # different from attrs username

        serializer, attrs = self._serializer_with_attrs(
            email="test@example.com", username="new_username"
        )

        with patch("accounts.serializers.User.objects.filter") as mock_filter:
            mock_filter.side_effect = [
                self._make_filter_mock(email_user),  # email lookup
                self._make_filter_mock(None),         # no username conflict
            ]
            with pytest.raises(ValidationError) as exc_info:
                serializer.validate(attrs)

        assert "username" in exc_info.value.detail
        assert (
            str(exc_info.value.detail["username"])
            == "Email này đang có đăng ký chờ xác thực với tên đăng nhập khác"
        )

    def test_TC9_branch3_miss_same_username_in_db(self):
        """
        Tests lines 143–155 (Branch 3 — MISS, username matches DB record).

        Condition: email exists in DB, email_verified=False, but the username
                   stored in DB is the SAME as the one being registered.
        Expected : Branch 3 is NOT triggered; validate() returns attrs.
        """
        email_user = MagicMock()
        email_user.email_verified = False
        email_user.pk = 8
        email_user.username = "testuser"  # same as attrs username

        serializer, attrs = self._serializer_with_attrs(
            email="test@example.com", username="testuser"
        )

        with patch("accounts.serializers.User.objects.filter") as mock_filter:
            mock_filter.side_effect = [
                self._make_filter_mock(email_user),  # email lookup
                self._make_filter_mock(email_user),  # username lookup → same user, same pk
            ]
            result = serializer.validate(attrs)

        assert result == attrs

    def test_TC10_branch3_miss_email_not_exists(self):
        """
        Tests lines 143–155 (Branch 3 — MISS, email absent).

        Condition: email does NOT exist in DB at all.
        Expected : Branch 3 is NOT triggered; validate() returns attrs.
        """
        serializer, attrs = self._serializer_with_attrs()

        with patch("accounts.serializers.User.objects.filter") as mock_filter:
            mock_filter.side_effect = [
                self._make_filter_mock(None),  # no email match
                self._make_filter_mock(None),  # no username match
            ]
            result = serializer.validate(attrs)

        assert result == attrs

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_TC11_happy_path_no_existing_email_or_username(self):
        """
        Happy path — Tests lines 98–157 end-to-end.

        Condition: Neither email nor username exists in DB.
        Expected : All three branches are skipped; validate() returns attrs
                   unchanged.
        """
        serializer, attrs = self._serializer_with_attrs(
            email="brand_new@example.com", username="brand_new_user"
        )

        with patch("accounts.serializers.User.objects.filter") as mock_filter:
            mock_filter.side_effect = [
                self._make_filter_mock(None),  # no email match
                self._make_filter_mock(None),  # no username match
            ]
            result = serializer.validate(attrs)

        assert result == attrs
        assert result["email"] == "brand_new@example.com"
        assert result["username"] == "brand_new_user"
