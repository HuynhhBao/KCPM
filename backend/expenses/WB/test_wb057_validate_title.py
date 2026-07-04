import pytest
from rest_framework import serializers
from expenses.serializers import ExpenseCreateUpdateSerializer


@pytest.fixture
def serializer():
    return ExpenseCreateUpdateSerializer()


def test_validate_title_valid_value_returns_stripped(serializer):
    result = serializer.validate_title("Tiền điện")
    assert result == "Tiền điện"


def test_validate_title_empty_string_raises(serializer):
    with pytest.raises(serializers.ValidationError):
        serializer.validate_title("")


def test_validate_title_whitespace_only_raises(serializer):
    with pytest.raises(serializers.ValidationError):
        serializer.validate_title("   ")


def test_validate_title_strips_surrounding_whitespace(serializer):
    result = serializer.validate_title("  Tiền điện  ")
    assert result == "Tiền điện"