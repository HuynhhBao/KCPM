#WB 066
"""
WB_066 — DebtSerializer.get_pending_payment_id
expenses-service

get_pending_payment() có test riêng ở WB_065 -> mock trực tiếp qua patch.object,
không dựng lại DB pending payment thật ở đây.
"""
from types import SimpleNamespace
from unittest.mock import patch

from expenses.serializers import DebtSerializer


# ── TC_WB066_01: N2-True ──
def test_get_pending_payment_id_returns_str_id_when_exists():
    serializer = DebtSerializer()
    fake_payment = SimpleNamespace(id='11111111-1111-1111-1111-111111111111')

    with patch.object(DebtSerializer, 'get_pending_payment', return_value=fake_payment):
        result = serializer.get_pending_payment_id(obj=None)

    assert result == str(fake_payment.id)


# ── TC_WB066_02: N2-False ──
def test_get_pending_payment_id_returns_none_when_not_exists():
    serializer = DebtSerializer()

    with patch.object(DebtSerializer, 'get_pending_payment', return_value=None):
        result = serializer.get_pending_payment_id(obj=None)

    assert result is None