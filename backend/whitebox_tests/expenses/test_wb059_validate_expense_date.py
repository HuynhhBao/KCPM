import pytest
from datetime import date, timedelta
from unittest.mock import patch
from rest_framework import serializers
from expenses.serializers import ExpenseCreateUpdateSerializer


@pytest.fixture
def serializer():
    return ExpenseCreateUpdateSerializer()


FAKE_TODAY = date(2026, 6, 26)


# ── TC_WB059_01: quá khứ (valid) ──
@patch('expenses.serializers.timezone.localdate', return_value=FAKE_TODAY)
def test_validate_expense_date_past_date_returns_value(mock_localdate, serializer):
    past_date = FAKE_TODAY - timedelta(days=1)
    result = serializer.validate_expense_date(past_date)
    assert result == past_date


# ── TC_WB059_02: tương lai (invalid) ──
@patch('expenses.serializers.timezone.localdate', return_value=FAKE_TODAY)
def test_validate_expense_date_future_date_raises(mock_localdate, serializer):
    future_date = FAKE_TODAY + timedelta(days=1)
    with pytest.raises(serializers.ValidationError):
        serializer.validate_expense_date(future_date)


# ── TC_WB059_03: hôm nay (valid) ──
@patch('expenses.serializers.timezone.localdate', return_value=FAKE_TODAY)
def test_validate_expense_date_today_returns_value(mock_localdate, serializer):
    result = serializer.validate_expense_date(FAKE_TODAY)
    assert result == FAKE_TODAY


# ── TC_WB059_04: boundary > today ──
@patch('expenses.serializers.timezone.localdate', return_value=FAKE_TODAY)
def test_validate_expense_date_one_day_ahead_raises(mock_localdate, serializer):
    with pytest.raises(serializers.ValidationError):
        serializer.validate_expense_date(FAKE_TODAY + timedelta(days=1))