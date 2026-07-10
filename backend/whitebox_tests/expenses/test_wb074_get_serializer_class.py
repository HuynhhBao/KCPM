"""
WB_074 — ExpenseDetailView.get_serializer_class
expenses-service

Hàm chỉ đọc self.request.method -> không cần DB, chỉ cần gán view.request giả lập.
"""
from types import SimpleNamespace

from expenses.serializers import ExpenseCreateUpdateSerializer, ExpenseDetailSerializer
from expenses.views import ExpenseDetailView


# ── TC_WB074_01: N1-True (method=PUT) ──
def test_get_serializer_class_put_returns_create_update_serializer():
    view = ExpenseDetailView()
    view.request = SimpleNamespace(method='PUT')

    result = view.get_serializer_class()

    assert result is ExpenseCreateUpdateSerializer


# ── TC_WB074_02: N1-True (method=PATCH, bổ sung) ──
def test_get_serializer_class_patch_returns_create_update_serializer():
    view = ExpenseDetailView()
    view.request = SimpleNamespace(method='PATCH')

    result = view.get_serializer_class()

    assert result is ExpenseCreateUpdateSerializer


# ── TC_WB074_03: N1-False (method=GET) ──
def test_get_serializer_class_get_returns_detail_serializer():
    view = ExpenseDetailView()
    view.request = SimpleNamespace(method='GET')

    result = view.get_serializer_class()

    assert result is ExpenseDetailSerializer