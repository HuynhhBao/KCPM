from decimal import Decimal
import pytest
from payments.views import get_pair_debt_state
from expenses.models import Debt, Expense

@pytest.mark.django_db
def test_wb091_tc01_get_pair_debt_state_positive(household, owner, debtor, debt_instance):
    expense_rev = Expense.objects.create(
        household=household, title="Reverse Exp", amount=20000, payer=debtor, split_type=Expense.SplitType.EQUAL
    )
    debt_rev = Debt.objects.create(
        household=household, expense=expense_rev, from_user=owner, to_user=debtor, amount=10000, paid_amount=0, is_paid=False
    )
    state = get_pair_debt_state(household=household, payer=debtor, receiver=owner)
    assert state['net_amount'] == Decimal('40000')

@pytest.mark.django_db
def test_wb091_tc02_get_pair_debt_state_zero_or_negative(household, owner, debtor, debt_instance):
    expense_rev = Expense.objects.create(
        household=household, title="Reverse Exp", amount=120000, payer=debtor, split_type=Expense.SplitType.EQUAL
    )
    Debt.objects.create(
        household=household, expense=expense_rev, from_user=owner, to_user=debtor, amount=60000, paid_amount=0, is_paid=False
    )
    state = get_pair_debt_state(household=household, payer=debtor, receiver=owner)
    assert state['net_amount'] == Decimal('0')
