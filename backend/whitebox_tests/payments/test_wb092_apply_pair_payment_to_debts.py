from decimal import Decimal
import pytest
from payments.views import apply_pair_payment_to_debts, get_pair_debt_state
from expenses.models import Debt, Expense

@pytest.mark.django_db
def test_wb092_tc01_apply_pair_payment_normal_flow(household, owner, debtor, debt_instance):
    expense_rev = Expense.objects.create(
        household=household, title="Reverse Exp", amount=20000, payer=debtor, split_type=Expense.SplitType.EQUAL
    )
    debt_rev = Debt.objects.create(
        household=household, expense=expense_rev, from_user=owner, to_user=debtor, amount=10000, paid_amount=0, is_paid=False
    )
    state = get_pair_debt_state(household=household, payer=debtor, receiver=owner)
    apply_pair_payment_to_debts(state=state, amount=Decimal('20000'))
    debt_rev.refresh_from_db()
    debt_instance.refresh_from_db()
    assert debt_rev.is_paid is True
    assert debt_instance.paid_amount == Decimal('30000')

@pytest.mark.django_db
def test_wb092_tc02_apply_pair_payment_virtual_receipt(household, owner, virtual_user, virtual_debt_instance):
    state = get_pair_debt_state(household=household, payer=virtual_user, receiver=owner)
    apply_pair_payment_to_debts(state=state, amount=Decimal('100000'))
    virtual_debt_instance.refresh_from_db()
    assert virtual_debt_instance.is_paid is True
    assert virtual_debt_instance.paid_amount == Decimal('100000')
