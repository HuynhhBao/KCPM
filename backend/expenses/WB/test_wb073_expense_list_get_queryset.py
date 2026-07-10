"""
WB_073 — ExpenseListView.get_queryset
expenses-service
"""

import pytest

from expenses.models import Expense
from expenses.views import ExpenseListView
from households.models import Household

# ❌ KHÔNG IMPORT conftest


# ── TC_WB073_01: outsider → empty queryset ──
@pytest.mark.django_db
def test_get_queryset_not_member_returns_empty(household, outsider_user, rf):
    view = ExpenseListView()
    view.kwargs = {'household_id': household.id}

    request = rf.get('/')
    request.user = outsider_user
    view.request = request

    queryset = view.get_queryset()

    assert queryset.count() == 0


# ── TC_WB073_02: member → filtered queryset ──
@pytest.mark.django_db
def test_get_queryset_member_returns_filtered_queryset(
    user,
    household,
    expense_instance,
    rf
):
    other_household = Household.objects.create(name='Nhà khác', owner=user)

    Expense.objects.create(
        household=other_household,
        payer=user,
        title='Tiền nước (nhà khác)',
        amount=50000,
    )

    second_expense = Expense.objects.create(
        household=household,
        payer=user,
        title='Tiền internet',
        amount=200000,
    )

    view = ExpenseListView()
    view.kwargs = {'household_id': household.id}

    request = rf.get('/')
    request.user = user
    view.request = request

    queryset = view.get_queryset()

    result_ids = set(queryset.values_list('id', flat=True))

    assert result_ids == {expense_instance.id, second_expense.id}