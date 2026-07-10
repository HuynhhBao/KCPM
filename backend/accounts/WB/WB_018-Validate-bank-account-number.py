import pytest
from rest_framework.exceptions import ValidationError
from accounts.serializers import UserProfileSerializer


class TestUserProfileSerializerValidateBankAccountNumber:
    """
    White-box tests for UserProfileSerializer.validate_bank_account_number() — lines 259–273

    Covers:
      - Branch 1 (lines 260–261): value is None          → return ''
      - Branch 2 (lines 265–266): after strip() is empty → return ''
      - Branch 3 (lines 268–271): not match ^[0-9]{4,30}$ → ValidationError('Số tài khoản chỉ được chứa chữ số, từ 4 đến 30 ký tự')
      - Happy path (line 273)   : valid digits-only string → returns stripped value
    """

    @staticmethod
    def _serializer():
        """Create a UserProfileSerializer instance without calling __init__."""
        return UserProfileSerializer.__new__(UserProfileSerializer)

    # ------------------------------------------------------------------
    # Branch 1 — lines 260–261  (value is None → return '')
    # ------------------------------------------------------------------

    def test_TC1_branch1_hit_none(self):
        """
        Tests lines 260–261 (Branch 1 — HIT).
        Condition: value = None → `value is None` is True
        Expected : returns '' immediately, no ValidationError raised
        """
        serializer = self._serializer()
        result = serializer.validate_bank_account_number(None)
        assert result == ''

    # ------------------------------------------------------------------
    # Branch 2 — lines 265–266  (after strip() is empty → return '')
    # ------------------------------------------------------------------

    def test_TC2_branch2_hit_empty_string(self):
        """
        Tests lines 265–266 (Branch 2 — HIT).
        Condition: value = "" → after strip() still "" → `not value` is True
        Expected : returns '' immediately, no ValidationError raised
        """
        serializer = self._serializer()
        result = serializer.validate_bank_account_number("")
        assert result == ''

    def test_TC3_branch2_hit_whitespace_only(self):
        """
        Tests lines 265–266 (Branch 2 — HIT).
        Condition: value = "   " → after strip() becomes "" → `not value` is True
        Expected : returns '' immediately, no ValidationError raised
        """
        serializer = self._serializer()
        result = serializer.validate_bank_account_number("   ")
        assert result == ''

    def test_TC4_branch2_miss_non_empty(self):
        """
        Tests lines 265–266 (Branch 2 — MISS).
        Condition: value = "12345678" → after strip() = "12345678" → `not value` is False
        Expected : Branch 2 is NOT taken; execution continues to regex check
        """
        serializer = self._serializer()
        # Valid digits-only value — should not return '' from branch 2
        result = serializer.validate_bank_account_number("12345678")
        assert result != '' and result == "12345678"

    # ------------------------------------------------------------------
    # Branch 3 — lines 268–271  (not match ^[0-9]{4,30}$)
    # ------------------------------------------------------------------

    def test_TC5_branch3_hit_contains_letters(self):
        """
        Tests lines 268–271 (Branch 3 — HIT).
        Condition: value = "1234abc" → contains non-digit chars → regex fails
        Expected : ValidationError('Số tài khoản chỉ được chứa chữ số, từ 4 đến 30 ký tự')
        """
        serializer = self._serializer()
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_bank_account_number("1234abc")
        assert str(exc_info.value.detail[0]) == "Số tài khoản chỉ được chứa chữ số, từ 4 đến 30 ký tự"

    def test_TC6_branch3_hit_too_short(self):
        """
        Tests lines 268–271 (Branch 3 — HIT).
        Condition: value = "123" → only 3 digits → len < 4 → regex ^[0-9]{4,30}$ fails
        Expected : ValidationError('Số tài khoản chỉ được chứa chữ số, từ 4 đến 30 ký tự')
        """
        serializer = self._serializer()
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_bank_account_number("123")
        assert str(exc_info.value.detail[0]) == "Số tài khoản chỉ được chứa chữ số, từ 4 đến 30 ký tự"

    def test_TC7_branch3_hit_too_long(self):
        """
        Tests lines 268–271 (Branch 3 — HIT).
        Condition: value = "1" * 31 → 31 digits → len > 30 → regex ^[0-9]{4,30}$ fails
        Expected : ValidationError('Số tài khoản chỉ được chứa chữ số, từ 4 đến 30 ký tự')
        """
        serializer = self._serializer()
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_bank_account_number("1" * 31)
        assert str(exc_info.value.detail[0]) == "Số tài khoản chỉ được chứa chữ số, từ 4 đến 30 ký tự"

    def test_TC8_branch3_hit_contains_special_chars(self):
        """
        Tests lines 268–271 (Branch 3 — HIT).
        Condition: value = "1234-5678" → contains hyphen → regex fails
        Expected : ValidationError('Số tài khoản chỉ được chứa chữ số, từ 4 đến 30 ký tự')
        """
        serializer = self._serializer()
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_bank_account_number("1234-5678")
        assert str(exc_info.value.detail[0]) == "Số tài khoản chỉ được chứa chữ số, từ 4 đến 30 ký tự"

    def test_TC9_branch3_miss_exactly_4_digits(self):
        """
        Tests lines 268–271 (Branch 3 — MISS).
        Condition: value = "1234" → exactly 4 digits → regex ^[0-9]{4,30}$ matches
        Expected : Branch 3 is NOT raised; function returns "1234"
        """
        serializer = self._serializer()
        result = serializer.validate_bank_account_number("1234")
        assert result == "1234"

    def test_TC10_branch3_miss_exactly_30_digits(self):
        """
        Tests lines 268–271 (Branch 3 — MISS).
        Condition: value = "1" * 30 → exactly 30 digits → regex ^[0-9]{4,30}$ matches
        Expected : Branch 3 is NOT raised; function returns "1" * 30
        """
        serializer = self._serializer()
        value = "1" * 30
        result = serializer.validate_bank_account_number(value)
        assert result == value

    # ------------------------------------------------------------------
    # Happy path — line 273  (return value)
    # ------------------------------------------------------------------

    def test_TC11_happy_path_valid_account_number(self):
        """
        Tests line 273 (Happy path).
        Condition: value = "9876543210" → all digits, len=10 → passes all branches
        Expected : returns "9876543210"
        """
        serializer = self._serializer()
        result = serializer.validate_bank_account_number("9876543210")
        assert result == "9876543210"

    def test_TC12_happy_path_strip_applied(self):
        """
        Tests line 263 + line 273 (Happy path — strip is applied).
        Condition: value = "  12345678  " → after strip = "12345678" → passes all branches
        Expected : returns "12345678" (leading/trailing spaces removed)
        """
        serializer = self._serializer()
        result = serializer.validate_bank_account_number("  12345678  ")
        assert result == "12345678"