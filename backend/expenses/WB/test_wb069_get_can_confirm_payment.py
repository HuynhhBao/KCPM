#WB_069
"""
WB_069 — DebtSerializer.get_can_confirm_payment
expenses-service
"""
from types import SimpleNamespace
from unittest.mock import patch

from expenses.serializers import DebtSerializer


def make_request(user_id):
    return SimpleNamespace(user=SimpleNamespace(id=user_id))


def make_debt(is_paid=False, to_user_id=2):
    return SimpleNamespace(is_paid=is_paid, to_user_id=to_user_id)


# ── TC_WB069_01: N2-True (D1: not request) ──
def test_get_can_confirm_payment_no_request_returns_false():
    serializer = DebtSerializer(context={})
    obj = make_debt()

    result = serializer.get_can_confirm_payment(obj)

    assert result is False


# ── TC_WB069_02: N2-True (D1: obj.is_paid) ──
def test_get_can_confirm_payment_already_paid_returns_false():
    request = make_request(user_id=2)
    serializer = DebtSerializer(context={'request': request})
    obj = make_debt(is_paid=True)

    result = serializer.get_can_confirm_payment(obj)

    assert result is False


# ── TC_WB069_03: N4-True (D2: có virtual member) ──
def test_get_can_confirm_payment_virtual_member_returns_false():
    request = make_request(user_id=2)
    serializer = DebtSerializer(context={'request': request})
    obj = make_debt(is_paid=False, to_user_id=2)

    with patch.object(DebtSerializer, 'get_has_virtual_member', return_value=True):
        result = serializer.get_can_confirm_payment(obj)

    assert result is False


# ── TC_WB069_04: N6-True (D3: to_user không phải current_user) ──
def test_get_can_confirm_payment_not_to_user_returns_false():
    request = make_request(user_id=1)
    serializer = DebtSerializer(context={'request': request})
    obj = make_debt(is_paid=False, to_user_id=2)

    with patch.object(DebtSerializer, 'get_has_virtual_member', return_value=False):
        result = serializer.get_can_confirm_payment(obj)

    assert result is False


# ── TC_WB069_05: N8 (happy path, có pending payment) ──
def test_get_can_confirm_payment_happy_path_returns_true():
    request = make_request(user_id=2)
    serializer = DebtSerializer(context={'request': request})
    obj = make_debt(is_paid=False, to_user_id=2)

    with patch.object(DebtSerializer, 'get_has_virtual_member', return_value=False), \
         patch.object(DebtSerializer, 'get_pending_payment', return_value=SimpleNamespace(id=1)):
        result = serializer.get_can_confirm_payment(obj)

    assert result is True


# ── TC_WB069_06: N8 (happy path nhưng không có pending payment, bổ sung) ──
def test_get_can_confirm_payment_no_pending_payment_returns_false():
    request = make_request(user_id=2)
    serializer = DebtSerializer(context={'request': request})
    obj = make_debt(is_paid=False, to_user_id=2)

    with patch.object(DebtSerializer, 'get_has_virtual_member', return_value=False), \
         patch.object(DebtSerializer, 'get_pending_payment', return_value=None):
        result = serializer.get_can_confirm_payment(obj)

    assert result is False
