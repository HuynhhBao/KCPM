import pytest
from rest_framework.exceptions import ValidationError
from accounts.serializers import UserProfileSerializer


class TestUserProfileSerializerValidateFullName:
    """
    White-box tests for UserProfileSerializer.validate_full_name() — lines 235–248

    Covers:
      - Branch 1 (lines 238–241): `not value` after strip → ValidationError('Họ và tên không được để trống')
      - Branch 2 (lines 243–246): `len(value) < 2`        → ValidationError('Họ và tên tối thiểu 2 ký tự')
      - Happy path (line 248)   : returns stripped value
    """

    @staticmethod
    def _serializer():
        """Create a UserProfileSerializer instance without calling __init__."""
        return UserProfileSerializer.__new__(UserProfileSerializer)

    # ------------------------------------------------------------------
    # Branch 1 — lines 238–241  (`not value` after strip)
    # ------------------------------------------------------------------

    def test_TC1_branch1_hit_empty_string(self):
        """
        Tests lines 238–241 (Branch 1 — HIT).
        Condition: value = "" → after strip still empty → `not value` is True
        Expected : ValidationError('Họ và tên không được để trống')
        """
        serializer = self._serializer()
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_full_name("")
        assert str(exc_info.value.detail[0]) == "Họ và tên không được để trống"

    def test_TC2_branch1_hit_whitespace_only(self):
        """
        Tests lines 238–241 (Branch 1 — HIT).
        Condition: value = "   " → after strip becomes "" → `not value` is True
        Expected : ValidationError('Họ và tên không được để trống')
        """
        serializer = self._serializer()
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_full_name("   ")
        assert str(exc_info.value.detail[0]) == "Họ và tên không được để trống"

    def test_TC3_branch1_miss_non_empty(self):
        """
        Tests lines 238–241 (Branch 1 — MISS).
        Condition: value = "An" → after strip = "An" → `not value` is False
        Expected : Branch 1 is NOT raised; execution continues past line 241
        """
        serializer = self._serializer()
        # Should not raise ValidationError for branch 1
        try:
            result = serializer.validate_full_name("An")
            # If we reach here, branch 1 was correctly missed
            assert result == "An"
        except ValidationError as e:
            assert str(e.detail[0]) != "Họ và tên không được để trống", (
                "Branch 1 should NOT be hit for non-empty value"
            )

    # ------------------------------------------------------------------
    # Branch 2 — lines 243–246  (`len(value) < 2`)
    # ------------------------------------------------------------------

    def test_TC4_branch2_hit_single_char(self):
        """
        Tests lines 243–246 (Branch 2 — HIT).
        Condition: value = "A" → after strip = "A" → len=1 < 2 → True
        Expected : ValidationError('Họ và tên tối thiểu 2 ký tự')
        """
        serializer = self._serializer()
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_full_name("A")
        assert str(exc_info.value.detail[0]) == "Họ và tên tối thiểu 2 ký tự"

    def test_TC5_branch2_hit_single_char_with_spaces(self):
        """
        Tests lines 243–246 (Branch 2 — HIT).
        Condition: value = "  A  " → after strip = "A" → len=1 < 2 → True
        Expected : ValidationError('Họ và tên tối thiểu 2 ký tự')
        """
        serializer = self._serializer()
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_full_name("  A  ")
        assert str(exc_info.value.detail[0]) == "Họ và tên tối thiểu 2 ký tự"

    def test_TC6_branch2_miss_exactly_2_chars(self):
        """
        Tests lines 243–246 (Branch 2 — MISS).
        Condition: value = "An" → after strip = "An" → len=2, NOT < 2 → False
        Expected : Branch 2 is NOT raised; function returns "An"
        """
        serializer = self._serializer()
        result = serializer.validate_full_name("An")
        assert result == "An"

    def test_TC7_branch2_miss_longer(self):
        """
        Tests lines 243–246 (Branch 2 — MISS).
        Condition: value = "Nguyễn Văn An" → len > 2 → False
        Expected : Branch 2 is NOT raised; function returns "Nguyễn Văn An"
        """
        serializer = self._serializer()
        result = serializer.validate_full_name("Nguyễn Văn An")
        assert result == "Nguyễn Văn An"

    # ------------------------------------------------------------------
    # Happy path — line 248  (return value)
    # ------------------------------------------------------------------

    def test_TC8_happy_path_valid_full_name(self):
        """
        Tests line 248 (Happy path).
        Condition: value = "Nguyễn Văn An" → passes both branches
        Expected : returns "Nguyễn Văn An" unchanged
        """
        serializer = self._serializer()
        result = serializer.validate_full_name("Nguyễn Văn An")
        assert result == "Nguyễn Văn An"

    def test_TC9_happy_path_strip_applied(self):
        """
        Tests line 236 + line 248 (Happy path — strip is applied).
        Condition: value = "  Trần Thị B  " → after strip = "Trần Thị B" → passes both branches
        Expected : returns "Trần Thị B" (leading/trailing spaces removed)
        """
        serializer = self._serializer()
        result = serializer.validate_full_name("  Trần Thị B  ")
        assert result == "Trần Thị B"
