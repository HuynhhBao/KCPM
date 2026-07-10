import pytest
from rest_framework import serializers
from decimal import Decimal
from expenses.serializers import ExpenseCreateUpdateSerializer


@pytest.fixture
def serializer():
    return ExpenseCreateUpdateSerializer()


# ── TC_WB058_01: hợp lệ (> 0) ──
def test_validate_amount_positive_value_returns_value(serializer):
    result = serializer.validate_amount(Decimal('100000'))
    assert result == Decimal('100000')


# ── TC_WB058_02: số âm ──
def test_validate_amount_negative_raises(serializer):
    with pytest.raises(serializers.ValidationError):
        serializer.validate_amount(Decimal('-500'))


# ── TC_WB058_03: bằng 0 ──
def test_validate_amount_zero_raises(serializer):
    with pytest.raises(serializers.ValidationError):
        serializer.validate_amount(Decimal('0'))


# ── TC_WB058_04: boundary > 0 ──
def test_validate_amount_just_above_zero_returns_value(serializer):
    result = serializer.validate_amount(Decimal('1'))
    assert result == Decimal('1')