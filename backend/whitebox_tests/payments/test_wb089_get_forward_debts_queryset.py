import pytest
from payments.views import get_forward_debts_queryset

@pytest.mark.django_db
def test_wb089_tc01_get_forward_debts_queryset_with_lock(household, owner, debtor, debt_instance):
    qs = get_forward_debts_queryset(household=household, payer=debtor, receiver=owner, lock=True)
    assert qs.query.select_for_update

@pytest.mark.django_db
def test_wb089_tc02_get_forward_debts_queryset_without_lock(household, owner, debtor, debt_instance):
    qs = get_forward_debts_queryset(household=household, payer=debtor, receiver=owner, lock=False)
    assert debt_instance in list(qs)
    assert not qs.query.select_for_update
