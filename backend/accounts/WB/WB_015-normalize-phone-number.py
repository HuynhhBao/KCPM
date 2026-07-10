import pytest
from rest_framework.exceptions import ValidationError
from accounts.serializers import normalize_phone_number


class TestNormalizePhoneNumber:
    """
    White-box tests for normalize_phone_number() — lines 34–51 (serializers.py)

    Covers:
      - Branch 1 (lines 35–36): value is None              → return ''
      - Branch 2 (lines 40–41): after strip() is empty     → return ''
      - Branch 3 (lines 43–49): not match \\+?[0-9]{9,15}  → ValidationError('Số điện thoại không hợp lệ')
      - Happy path (line 51)  : valid phone number          → return stripped value
    """

    # ------------------------------------------------------------------
    # Branch 1 — lines 35–36  (value is None → return '')
    # ------------------------------------------------------------------

    def test_TC1_branch1_hit_none(self):
        """
        Tests lines 35–36 (Branch 1 — HIT).
        Condition: value = None → `value is None` is True
        Expected : returns '' immediately
        """
        result = normalize_phone_number(None)
        assert result == ''

    def test_TC2_branch1_miss_string_value(self):
        """
        Tests lines 35–36 (Branch 1 — MISS).
        Condition: value = '0901234567' → `value is None` is False
        Expected : Branch 1 not taken; execution continues to strip check
        """
        result = normalize_phone_number('0901234567')
        assert result == '0901234567'

    # ------------------------------------------------------------------
    # Branch 2 — lines 40–41  (after strip() empty → return '')
    # ------------------------------------------------------------------

    def test_TC3_branch2_hit_empty_string(self):
        """
        Tests lines 40–41 (Branch 2 — HIT).
        Condition: value = '' → after strip() still '' → `not value` is True
        Expected : returns ''
        """
        result = normalize_phone_number('')
        assert result == ''

    def test_TC4_branch2_hit_whitespace_only(self):
        """
        Tests lines 40–41 (Branch 2 — HIT).
        Condition: value = '   ' → after strip() becomes '' → `not value` is True
        Expected : returns ''
        """
        result = normalize_phone_number('   ')
        assert result == ''

    def test_TC5_branch2_miss_non_empty(self):
        """
        Tests lines 40–41 (Branch 2 — MISS).
        Condition: value = '0901234567' → after strip() non-empty → `not value` is False
        Expected : Branch 2 not taken; execution continues to regex check
        """
        result = normalize_phone_number('0901234567')
        assert result == '0901234567'

    # ------------------------------------------------------------------
    # Branch 3 — lines 43–49  (not match regex → ValidationError)
    # ------------------------------------------------------------------

    def test_TC6_branch3_hit_too_short(self):
        """
        Tests lines 43–49 (Branch 3 — HIT: fewer than 9 digits).
        Condition: value = '12345678' → only 8 digits → regex \\+?[0-9]{9,15} fails
        Expected : ValidationError('Số điện thoại không hợp lệ')
        """
        with pytest.raises(ValidationError) as exc_info:
            normalize_phone_number('12345678')
        assert str(exc_info.value.detail[0]) == 'Số điện thoại không hợp lệ'

    def test_TC7_branch3_hit_too_long(self):
        """
        Tests lines 43–49 (Branch 3 — HIT: more than 15 digits).
        Condition: value = '1234567890123456' → 16 digits → regex fails
        Expected : ValidationError('Số điện thoại không hợp lệ')
        """
        with pytest.raises(ValidationError) as exc_info:
            normalize_phone_number('1234567890123456')
        assert str(exc_info.value.detail[0]) == 'Số điện thoại không hợp lệ'

    def test_TC8_branch3_hit_contains_letters(self):
        """
        Tests lines 43–49 (Branch 3 — HIT: contains non-digit characters).
        Condition: value = '090abc1234' → contains letters → regex fails
        Expected : ValidationError('Số điện thoại không hợp lệ')
        """
        with pytest.raises(ValidationError) as exc_info:
            normalize_phone_number('090abc1234')
        assert str(exc_info.value.detail[0]) == 'Số điện thoại không hợp lệ'

    def test_TC9_branch3_hit_plus_in_middle(self):
        """
        Tests lines 43–49 (Branch 3 — HIT: '+' not at start).
        Condition: value = '090+1234567' → '+' in middle → fullmatch fails
        Expected : ValidationError('Số điện thoại không hợp lệ')
        """
        with pytest.raises(ValidationError) as exc_info:
            normalize_phone_number('090+1234567')
        assert str(exc_info.value.detail[0]) == 'Số điện thoại không hợp lệ'

    def test_TC10_branch3_hit_contains_spaces(self):
        """
        Tests lines 43–49 (Branch 3 — HIT: internal spaces after strip).
        Condition: value = '090 123 4567' → spaces inside → fullmatch fails
        Expected : ValidationError('Số điện thoại không hợp lệ')
        """
        with pytest.raises(ValidationError) as exc_info:
            normalize_phone_number('090 123 4567')
        assert str(exc_info.value.detail[0]) == 'Số điện thoại không hợp lệ'

    def test_TC11_branch3_miss_exactly_9_digits(self):
        """
        Tests lines 43–49 (Branch 3 — MISS: exactly 9 digits).
        Condition: value = '123456789' → 9 digits → regex matches
        Expected : Branch 3 not raised; returns '123456789'
        """
        result = normalize_phone_number('123456789')
        assert result == '123456789'

    def test_TC12_branch3_miss_exactly_15_digits(self):
        """
        Tests lines 43–49 (Branch 3 — MISS: exactly 15 digits).
        Condition: value = '123456789012345' → 15 digits → regex matches
        Expected : Branch 3 not raised; returns '123456789012345'
        """
        result = normalize_phone_number('123456789012345')
        assert result == '123456789012345'

    def test_TC13_branch3_miss_plus_prefix(self):
        """
        Tests lines 43–49 (Branch 3 — MISS: '+' prefix with 9 digits).
        Condition: value = '+84901234567' → '+' then 11 digits → regex matches
        Expected : Branch 3 not raised; returns '+84901234567'
        """
        result = normalize_phone_number('+84901234567')
        assert result == '+84901234567'

    # ------------------------------------------------------------------
    # Happy path — line 51  (valid phone → return stripped value)
    # ------------------------------------------------------------------

    def test_TC14_happy_path_valid_local_number(self):
        """
        Tests line 51 (Happy path).
        Condition: value = '0901234567' → 10 digits → passes all checks
        Expected : returns '0901234567'
        """
        result = normalize_phone_number('0901234567')
        assert result == '0901234567'

    def test_TC15_happy_path_valid_international_number(self):
        """
        Tests line 51 (Happy path).
        Condition: value = '+84901234567' → '+' + 11 digits → passes all checks
        Expected : returns '+84901234567'
        """
        result = normalize_phone_number('+84901234567')
        assert result == '+84901234567'

    def test_TC16_happy_path_strip_applied(self):
        """
        Tests lines 38 + 51 (Happy path — strip applied before return).
        Condition: value = '  0901234567  ' → after strip = '0901234567' → valid
        Expected : returns '0901234567' (leading/trailing spaces removed)
        """
        result = normalize_phone_number('  0901234567  ')
        assert result == '0901234567'
