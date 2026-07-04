#WB 064
"""
WB_064 — ExpenseListSerializer.get_can_manage
expenses-service

Không cần @pytest.mark.django_db: get_can_manage chỉ đọc obj.payer_id và
request.user.id, không đụng DB/model thật -> dùng SimpleNamespace để giả
lập obj và request thay vì tạo Expense/User thật trong DB test.
"""
from types import SimpleNamespace

from expenses.serializers import ExpenseListSerializer


# ── TC_WB064_01: N2-True (context không có request) ──
def test_get_can_manage_no_request_returns_false():
    obj = SimpleNamespace(payer_id=5)
    serializer = ExpenseListSerializer(context={})

    result = serializer.get_can_manage(obj)

    assert result is False


# ── TC_WB064_02: N2-False, payer_id == request.user.id ──
def test_get_can_manage_payer_matches_request_user_returns_true():
    request = SimpleNamespace(user=SimpleNamespace(id=5))
    obj = SimpleNamespace(payer_id=5)
    serializer = ExpenseListSerializer(context={'request': request})

    result = serializer.get_can_manage(obj)

    assert result is True


# ── TC_WB064_03: N2-False, payer_id != request.user.id ──
def test_get_can_manage_payer_not_match_request_user_returns_false():
    request = SimpleNamespace(user=SimpleNamespace(id=5))
    obj = SimpleNamespace(payer_id=9)
    serializer = ExpenseListSerializer(context={'request': request})

    result = serializer.get_can_manage(obj)

    assert result is False
