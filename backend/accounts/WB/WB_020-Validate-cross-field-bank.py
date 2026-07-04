import pytest
from unittest.mock import MagicMock
from rest_framework.exceptions import ValidationError
from accounts.serializers import UserProfileSerializer


class TestUserProfileSerializerValidateCrossFieldBank:
    """
    White-box tests for UserProfileSerializer.validate() — lines 384–417

    Covers:
      - Branch 1 (lines 406–409): all 3 bank fields are empty/whitespace
                                   → has_any_bank_info=False → return attrs (valid)
      - Branch 2 (lines 409–415): some but not all bank fields filled
                                   → has_any_bank_info=True, has_all_bank_info=False
                                   → ValidationError({'bank_account_number': '...'})
      - Branch 3 (line 417)     : all 3 bank fields filled correctly
                                   → has_any_bank_info=True, has_all_bank_info=True
                                   → return attrs (valid)
    """

    @staticmethod
    def _serializer(instance=None):
        """Create a UserProfileSerializer instance without calling __init__."""
        serializer = UserProfileSerializer.__new__(UserProfileSerializer)
        serializer.instance = instance
        return serializer

    @staticmethod
    def _make_instance(bank_name='', bank_account_number='', bank_account_holder=''):
        """Helper: build a mock model instance with bank fields."""
        instance = MagicMock()
        instance.bank_name = bank_name
        instance.bank_account_number = bank_account_number
        instance.bank_account_holder = bank_account_holder
        return instance

    # ------------------------------------------------------------------
    # Branch 1 — lines 406–409  (all bank fields empty → return attrs)
    # ------------------------------------------------------------------

    def test_TC1_branch1_hit_all_fields_absent(self):
        """
        Tests lines 406–409 (Branch 1 — HIT: has_any_bank_info=False).
        Condition: attrs has none of the 3 bank fields; instance also has empty strings
        Expected : no ValidationError raised; returns attrs unchanged
        """
        serializer = self._serializer(instance=self._make_instance())
        attrs = {}
        result = serializer.validate(attrs)
        assert result == attrs

    def test_TC2_branch1_hit_all_fields_empty_string(self):
        """
        Tests lines 406–409 (Branch 1 — HIT: has_any_bank_info=False).
        Condition: all 3 fields present in attrs but set to ""
        Expected : no ValidationError raised; returns attrs unchanged
        """
        serializer = self._serializer(instance=self._make_instance())
        attrs = {
            'bank_name': '',
            'bank_account_number': '',
            'bank_account_holder': '',
        }
        result = serializer.validate(attrs)
        assert result == attrs

    def test_TC3_branch1_hit_all_fields_whitespace_only(self):
        """
        Tests lines 406–409 (Branch 1 — HIT: has_any_bank_info=False after strip).
        Condition: all 3 fields contain only whitespace → after strip all become ""
        Expected : no ValidationError raised; returns attrs unchanged
        """
        serializer = self._serializer(instance=self._make_instance())
        attrs = {
            'bank_name': '   ',
            'bank_account_number': '   ',
            'bank_account_holder': '   ',
        }
        result = serializer.validate(attrs)
        assert result == attrs

    # ------------------------------------------------------------------
    # Branch 2 — lines 409–415  (some but not all fields filled → ValidationError)
    # ------------------------------------------------------------------

    def test_TC4_branch2_hit_only_bank_name(self):
        """
        Tests lines 409–415 (Branch 2 — HIT).
        Condition: only bank_name filled; bank_account_number and bank_account_holder empty
                   → has_any_bank_info=True, has_all_bank_info=False
        Expected : ValidationError({'bank_account_number': 'Vui lòng nhập đầy đủ tên ngân hàng, số tài khoản và chủ tài khoản'})
        """
        serializer = self._serializer(instance=self._make_instance())
        attrs = {
            'bank_name': 'Vietcombank',
            'bank_account_number': '',
            'bank_account_holder': '',
        }
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate(attrs)
        assert 'bank_account_number' in exc_info.value.detail
        assert str(exc_info.value.detail['bank_account_number']) == \
            'Vui lòng nhập đầy đủ tên ngân hàng, số tài khoản và chủ tài khoản'

    def test_TC5_branch2_hit_only_bank_account_number(self):
        """
        Tests lines 409–415 (Branch 2 — HIT).
        Condition: only bank_account_number filled; other two empty
                   → has_any_bank_info=True, has_all_bank_info=False
        Expected : ValidationError with key 'bank_account_number'
        """
        serializer = self._serializer(instance=self._make_instance())
        attrs = {
            'bank_name': '',
            'bank_account_number': '12345678',
            'bank_account_holder': '',
        }
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate(attrs)
        assert 'bank_account_number' in exc_info.value.detail
        assert str(exc_info.value.detail['bank_account_number']) == \
            'Vui lòng nhập đầy đủ tên ngân hàng, số tài khoản và chủ tài khoản'

    def test_TC6_branch2_hit_only_bank_account_holder(self):
        """
        Tests lines 409–415 (Branch 2 — HIT).
        Condition: only bank_account_holder filled; other two empty
                   → has_any_bank_info=True, has_all_bank_info=False
        Expected : ValidationError with key 'bank_account_number'
        """
        serializer = self._serializer(instance=self._make_instance())
        attrs = {
            'bank_name': '',
            'bank_account_number': '',
            'bank_account_holder': 'Nguyễn Văn An',
        }
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate(attrs)
        assert 'bank_account_number' in exc_info.value.detail
        assert str(exc_info.value.detail['bank_account_number']) == \
            'Vui lòng nhập đầy đủ tên ngân hàng, số tài khoản và chủ tài khoản'

    def test_TC7_branch2_hit_two_fields_filled_missing_holder(self):
        """
        Tests lines 409–415 (Branch 2 — HIT).
        Condition: bank_name + bank_account_number filled; bank_account_holder empty
                   → has_any_bank_info=True, has_all_bank_info=False
        Expected : ValidationError with key 'bank_account_number'
        """
        serializer = self._serializer(instance=self._make_instance())
        attrs = {
            'bank_name': 'Vietcombank',
            'bank_account_number': '12345678',
            'bank_account_holder': '',
        }
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate(attrs)
        assert 'bank_account_number' in exc_info.value.detail
        assert str(exc_info.value.detail['bank_account_number']) == \
            'Vui lòng nhập đầy đủ tên ngân hàng, số tài khoản và chủ tài khoản'

    def test_TC8_branch2_hit_two_fields_filled_missing_name(self):
        """
        Tests lines 409–415 (Branch 2 — HIT).
        Condition: bank_account_number + bank_account_holder filled; bank_name empty
                   → has_any_bank_info=True, has_all_bank_info=False
        Expected : ValidationError with key 'bank_account_number'
        """
        serializer = self._serializer(instance=self._make_instance())
        attrs = {
            'bank_name': '',
            'bank_account_number': '12345678',
            'bank_account_holder': 'Nguyễn Văn An',
        }
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate(attrs)
        assert 'bank_account_number' in exc_info.value.detail
        assert str(exc_info.value.detail['bank_account_number']) == \
            'Vui lòng nhập đầy đủ tên ngân hàng, số tài khoản và chủ tài khoản'

    def test_TC9_branch2_hit_whitespace_counts_as_empty(self):
        """
        Tests lines 409–415 (Branch 2 — HIT).
        Condition: bank_name = "  " (whitespace only) → after strip = "" → treated as empty
                   bank_account_number + bank_account_holder filled
                   → has_any_bank_info=True, has_all_bank_info=False
        Expected : ValidationError with key 'bank_account_number'
        """
        serializer = self._serializer(instance=self._make_instance())
        attrs = {
            'bank_name': '   ',
            'bank_account_number': '12345678',
            'bank_account_holder': 'Nguyễn Văn An',
        }
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate(attrs)
        assert 'bank_account_number' in exc_info.value.detail
        assert str(exc_info.value.detail['bank_account_number']) == \
            'Vui lòng nhập đầy đủ tên ngân hàng, số tài khoản và chủ tài khoản'

    # ------------------------------------------------------------------
    # Branch 3 — line 417  (all 3 fields filled → return attrs)
    # ------------------------------------------------------------------

    def test_TC10_branch3_hit_all_fields_filled(self):
        """
        Tests line 417 (Branch 3 — HIT: all bank fields provided).
        Condition: all 3 fields filled with valid non-empty values
                   → has_any_bank_info=True, has_all_bank_info=True
        Expected : no ValidationError raised; returns attrs unchanged
        """
        serializer = self._serializer(instance=self._make_instance())
        attrs = {
            'bank_name': 'Vietcombank',
            'bank_account_number': '12345678',
            'bank_account_holder': 'Nguyễn Văn An',
        }
        result = serializer.validate(attrs)
        assert result == attrs

    def test_TC11_branch3_hit_fields_from_instance_fallback(self):
        """
        Tests lines 385–398 + line 417 (Branch 3 — HIT via instance fallback).
        Condition: attrs is empty dict; instance already has all 3 bank fields set
                   → values are read from self.instance → all filled
        Expected : no ValidationError raised; returns attrs unchanged
        """
        instance = self._make_instance(
            bank_name='Techcombank',
            bank_account_number='987654321',
            bank_account_holder='Trần Thị B',
        )
        serializer = self._serializer(instance=instance)
        attrs = {}
        result = serializer.validate(attrs)
        assert result == attrs

    def test_TC12_branch3_hit_attrs_override_instance(self):
        """
        Tests lines 385–417 (Branch 3 — HIT: attrs values take priority over instance).
        Condition: instance has all 3 fields; attrs also provides all 3 with new values
        Expected : no ValidationError raised; returns attrs unchanged
        """
        instance = self._make_instance(
            bank_name='OldBank',
            bank_account_number='00000000',
            bank_account_holder='Old Name',
        )
        serializer = self._serializer(instance=instance)
        attrs = {
            'bank_name': 'BIDV',
            'bank_account_number': '11223344',
            'bank_account_holder': 'Lê Văn C',
        }
        result = serializer.validate(attrs)
        assert result == attrs