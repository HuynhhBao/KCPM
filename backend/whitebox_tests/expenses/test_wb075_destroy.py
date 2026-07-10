"""
WB_075 — ExpenseDetailView.destroy
"""

from unittest.mock import patch

import pytest
from rest_framework.exceptions import PermissionDenied

from expenses.models import Debt, Expense
from expenses.views import ExpenseDetailView
from households.models import Activity


# ── helper: dùng rf fixture thay vì conftest import ──
# (pytest-django auto inject rf)


# ── TC_WB075_01: không phải payer ──
@pytest.mark.django_db
def test_destroy_not_payer_raises_permission_denied(
    user,
    other_user,
    household,
    expense_instance,
    rf
):
    view = ExpenseDetailView()
    view.request = rf.delete('/')
    view.request.user = other_user

    with patch.object(
        ExpenseDetailView,
        'get_object',
        return_value=expense_instance
    ):
        with pytest.raises(PermissionDenied):
            view.destroy(view.request)

    assert Expense.objects.filter(id=expense_instance.id).exists()


# ── TC_WB075_02: có debt đã paid → 400 ──
@pytest.mark.django_db
def test_destroy_has_paid_debt_returns_400(
    user,
    other_user,
    household,
    expense_instance,
    rf
):
    Debt.objects.create(
        household=household,
        expense=expense_instance,
        from_user=user,
        to_user=other_user,
        amount=100000,
        is_paid=True,
    )

    view = ExpenseDetailView()
    view.request = rf.delete('/')
    view.request.user = user

    with patch.object(
        ExpenseDetailView,
        'get_object',
        return_value=expense_instance
    ):
        response = view.destroy(view.request)

    assert response.status_code == 400
    assert Expense.objects.filter(id=expense_instance.id).exists()


# ── TC_WB075_03: happy path ──
@pytest.mark.django_db
def test_destroy_happy_path_deletes_expense_and_logs_activity(
    user,
    other_user,
    household,
    expense_instance,
    rf
):
    expense_id = expense_instance.id

    view = ExpenseDetailView()
    view.request = rf.delete('/')
    view.request.user = user

    with patch.object(
        ExpenseDetailView,
        'get_object',
        return_value=expense_instance
    ):
        response = view.destroy(view.request)

    assert response.status_code == 200

    assert not Expense.objects.filter(id=expense_id).exists()

    assert Activity.objects.filter(
        household=household,
        activity_type=Activity.ActivityType.EXPENSE_DELETED,
    ).exists()