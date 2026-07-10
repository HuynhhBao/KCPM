#WB_068
"""
WB_068 — DebtSerializer.get_can_mark_paid
expenses-service

get_pending_payment (WB_065) và get_has_virtual_member được mock qua patch.object,
obj (Debt) được giả lập bằng SimpleNamespace vì hàm chỉ đọc is_paid/from_user_id/to_user_id,
không cần Debt thật trong DB.
"""
from types import SimpleNamespace
from unittest.mock import patch

from expenses.serializers import DebtSerializer


def make_request(user_id):
    return SimpleNamespace(user=SimpleNamespace(id=user_id))


def make_debt(is_paid=False, from_user_id=1, to_user_id=2):
    return SimpleNamespace(is_paid=is_paid, from_user_id=from_user_id, to_user_id=to_user_id)


# ── TC_WB068_01: N2-True (D1: not request) ──
def test_get_can_mark_paid_no_request_returns_false():
    serializer = DebtSerializer(context={})
    obj = make_debt()

    result = serializer.get_can_mark_paid(obj)

    assert result is False


# ── TC_WB068_02: N2-True (D1: obj.is_paid) ──
def test_get_can_mark_paid_already_paid_returns_false():
    request = make_request(user_id=1)
    serializer = DebtSerializer(context={'request': request})
    obj = make_debt(is_paid=True)

    result = serializer.get_can_mark_paid(obj)

    assert result is False


# ── TC_WB068_03: N5-True (D2: có pending payment) ──
def test_get_can_mark_paid_has_pending_payment_returns_false():
    request = make_request(user_id=1)
    serializer = DebtSerializer(context={'request': request})
    obj = make_debt(is_paid=False)

    with patch.object(DebtSerializer, 'get_pending_payment', return_value=SimpleNamespace(id=1)):
        result = serializer.get_can_mark_paid(obj)

    assert result is False


# ── TC_WB068_04: N9-True (D3-True virtual, D4-True: from_user là current_user) ──
def test_get_can_mark_paid_virtual_from_user_matches_returns_true():
    request = make_request(user_id=1)
    serializer = DebtSerializer(context={'request': request})
    obj = make_debt(is_paid=False, from_user_id=1, to_user_id=2)

    with patch.object(DebtSerializer, 'get_pending_payment', return_value=None), \
         patch.object(DebtSerializer, 'get_has_virtual_member', return_value=True):
        result = serializer.get_can_mark_paid(obj)

    assert result is True


# ── TC_WB068_05: N11-True (D3-True virtual, D4-False, D5-True: to_user là current_user) ──
def test_get_can_mark_paid_virtual_to_user_matches_returns_true():
    request = make_request(user_id=2)
    serializer = DebtSerializer(context={'request': request})
    obj = make_debt(is_paid=False, from_user_id=1, to_user_id=2)

    with patch.object(DebtSerializer, 'get_pending_payment', return_value=None), \
         patch.object(DebtSerializer, 'get_has_virtual_member', return_value=True):
        result = serializer.get_can_mark_paid(obj)

    assert result is True


# ── TC_WB068_06: N13 (D3-True virtual, D4-False, D5-False: không ai khớp) ──
def test_get_can_mark_paid_virtual_neither_matches_returns_false():
    request = make_request(user_id=99)
    serializer = DebtSerializer(context={'request': request})
    obj = make_debt(is_paid=False, from_user_id=1, to_user_id=2)

    with patch.object(DebtSerializer, 'get_pending_payment', return_value=None), \
         patch.object(DebtSerializer, 'get_has_virtual_member', return_value=True):
        result = serializer.get_can_mark_paid(obj)

    assert result is False


# ── TC_WB068_07: N14 (D3-False: không virtual, from_user == current) ──
def test_get_can_mark_paid_not_virtual_from_user_matches_returns_true():
    request = make_request(user_id=1)
    serializer = DebtSerializer(context={'request': request})
    obj = make_debt(is_paid=False, from_user_id=1, to_user_id=2)

    with patch.object(DebtSerializer, 'get_pending_payment', return_value=None), \
         patch.object(DebtSerializer, 'get_has_virtual_member', return_value=False):
        result = serializer.get_can_mark_paid(obj)

    assert result is True


# ── TC_WB068_08: N14 (D3-False: không virtual, from_user != current, bổ sung) ──
def test_get_can_mark_paid_not_virtual_from_user_not_match_returns_false():
    request = make_request(user_id=99)
    serializer = DebtSerializer(context={'request': request})
    obj = make_debt(is_paid=False, from_user_id=1, to_user_id=2)

    with patch.object(DebtSerializer, 'get_pending_payment', return_value=None), \
         patch.object(DebtSerializer, 'get_has_virtual_member', return_value=False):
        result = serializer.get_can_mark_paid(obj)

    assert result is False