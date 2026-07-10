#WB_067
"""
WB_067 — DebtSerializer.get_pending_payment_status
expenses-service

get_pending_payment() có test riêng ở WB_065 -> mock trực tiếp.
"""
from types import SimpleNamespace
from unittest.mock import patch

from expenses.serializers import DebtSerializer


# ── TC_WB067_01: N2-True ──
def test_get_pending_payment_status_returns_status_when_exists():
    serializer = DebtSerializer()
    fake_payment = SimpleNamespace(status='pending')

    with patch.object(DebtSerializer, 'get_pending_payment', return_value=fake_payment):
        result = serializer.get_pending_payment_status(obj=None)

    assert result == 'pending'


# ── TC_WB067_02: N2-False ──
def test_get_pending_payment_status_returns_empty_when_not_exists():
    serializer = DebtSerializer()

    with patch.object(DebtSerializer, 'get_pending_payment', return_value=None):
        result = serializer.get_pending_payment_status(obj=None)

    assert result == ''