import pytest
from rest_framework.exceptions import ValidationError
from accounts.serializers import ChangePasswordSerializer


class TestChangePasswordSerializerValidate:
    """
    White-box tests for ChangePasswordSerializer.validate() — lines 436–445

    Covers:
      - Branch 1 (lines 437–443): new_password != confirm_password
                                   → ValidationError({'confirm_password': 'Mật khẩu xác nhận không khớp'})
      - Branch 2 (line 445)     : new_password == confirm_password
                                   → return attrs (valid)
    """

    @staticmethod
    def _serializer():
        """Create a ChangePasswordSerializer instance without calling __init__."""
        return ChangePasswordSerializer.__new__(ChangePasswordSerializer)

    # ------------------------------------------------------------------
    # Branch 1 — lines 437–443  (new_password != confirm_password → ValidationError)
    # ------------------------------------------------------------------

    def test_TC1_branch1_hit_passwords_differ(self):
        """
        Tests lines 437–443 (Branch 1 — HIT).
        Condition: new_password = 'NewPass@123', confirm_password = 'WrongPass@123' → not equal
        Expected : ValidationError({'confirm_password': 'Mật khẩu xác nhận không khớp'})
        """
        serializer = self._serializer()
        attrs = {
            'old_password': 'OldPass@123',
            'new_password': 'NewPass@123',
            'confirm_password': 'WrongPass@123',
        }
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate(attrs)
        assert 'confirm_password' in exc_info.value.detail
        assert str(exc_info.value.detail['confirm_password']) == 'Mật khẩu xác nhận không khớp'

    def test_TC2_branch1_hit_confirm_empty(self):
        """
        Tests lines 437–443 (Branch 1 — HIT).
        Condition: new_password = 'NewPass@123', confirm_password = '' → not equal
        Expected : ValidationError({'confirm_password': 'Mật khẩu xác nhận không khớp'})
        """
        serializer = self._serializer()
        attrs = {
            'old_password': 'OldPass@123',
            'new_password': 'NewPass@123',
            'confirm_password': '',
        }
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate(attrs)
        assert 'confirm_password' in exc_info.value.detail
        assert str(exc_info.value.detail['confirm_password']) == 'Mật khẩu xác nhận không khớp'

    def test_TC3_branch1_hit_case_sensitive(self):
        """
        Tests lines 437–443 (Branch 1 — HIT: case-sensitive comparison).
        Condition: new_password = 'NewPass@123', confirm_password = 'newpass@123' → differ by case
        Expected : ValidationError({'confirm_password': 'Mật khẩu xác nhận không khớp'})
        """
        serializer = self._serializer()
        attrs = {
            'old_password': 'OldPass@123',
            'new_password': 'NewPass@123',
            'confirm_password': 'newpass@123',
        }
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate(attrs)
        assert 'confirm_password' in exc_info.value.detail
        assert str(exc_info.value.detail['confirm_password']) == 'Mật khẩu xác nhận không khớp'

    def test_TC4_branch1_hit_extra_whitespace(self):
        """
        Tests lines 437–443 (Branch 1 — HIT: trailing space makes them differ).
        Condition: new_password = 'NewPass@123', confirm_password = 'NewPass@123 ' (trailing space)
        Expected : ValidationError({'confirm_password': 'Mật khẩu xác nhận không khớp'})
        """
        serializer = self._serializer()
        attrs = {
            'old_password': 'OldPass@123',
            'new_password': 'NewPass@123',
            'confirm_password': 'NewPass@123 ',
        }
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate(attrs)
        assert 'confirm_password' in exc_info.value.detail
        assert str(exc_info.value.detail['confirm_password']) == 'Mật khẩu xác nhận không khớp'

    # ------------------------------------------------------------------
    # Branch 2 — line 445  (new_password == confirm_password → return attrs)
    # ------------------------------------------------------------------

    def test_TC5_branch2_miss_passwords_match(self):
        """
        Tests line 445 (Branch 2 — MISS: passwords are equal).
        Condition: new_password == confirm_password = 'NewPass@123'
        Expected : no ValidationError raised; returns attrs unchanged
        """
        serializer = self._serializer()
        attrs = {
            'old_password': 'OldPass@123',
            'new_password': 'NewPass@123',
            'confirm_password': 'NewPass@123',
        }
        result = serializer.validate(attrs)
        assert result == attrs

    def test_TC6_branch2_miss_passwords_match_special_chars(self):
        """
        Tests line 445 (Branch 2 — MISS: passwords with special characters match).
        Condition: new_password == confirm_password = 'P@$$w0rd!#%'
        Expected : no ValidationError raised; returns attrs unchanged
        """
        serializer = self._serializer()
        attrs = {
            'old_password': 'OldPass@123',
            'new_password': 'P@$$w0rd!#%',
            'confirm_password': 'P@$$w0rd!#%',
        }
        result = serializer.validate(attrs)
        assert result == attrs

    def test_TC7_branch2_miss_returns_full_attrs(self):
        """
        Tests line 445 (Branch 2 — MISS: return value contains all original keys).
        Condition: passwords match; attrs has all 3 keys
        Expected : returned dict is identical to input attrs (all keys preserved)
        """
        serializer = self._serializer()
        attrs = {
            'old_password': 'OldPass@123',
            'new_password': 'Secure#2024',
            'confirm_password': 'Secure#2024',
        }
        result = serializer.validate(attrs)
        assert result is attrs
        assert set(result.keys()) == {'old_password', 'new_password', 'confirm_password'}
