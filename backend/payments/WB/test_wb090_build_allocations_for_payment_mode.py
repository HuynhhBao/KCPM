from decimal import Decimal
import pytest
from payments.models import Payment
from payments.views import build_allocations_for_payment_mode

@pytest.mark.django_db
def test_wb090_tc01_build_allocations_full_mode(household, debtor, owner, debt_instance):
    total, allocations = build_allocations_for_payment_mode(
        household=household, payer=debtor, receiver=owner, payment_mode=Payment.Mode.FULL
    )
    assert total == Decimal('50000')
    assert len(allocations) == 1
    assert allocations[0]['debt'] == debt_instance

@pytest.mark.django_db
def test_wb090_tc02_build_allocations_custom_amount_valid(household, debtor, owner, debt_instance):
    total, allocations = build_allocations_for_payment_mode(
        household=household, payer=debtor, receiver=owner,
        payment_mode=Payment.Mode.CUSTOM_AMOUNT, amount=20000
    )
    assert total == Decimal('20000')
    assert len(allocations) == 1
    assert allocations[0]['allocated_amount'] == Decimal('20000')

@pytest.mark.django_db
def test_wb090_tc03_build_allocations_custom_amount_zero(household, debtor, owner, debt_instance):
    with pytest.raises(ValueError, match="Số tiền thanh toán phải lớn hơn 0."):
        build_allocations_for_payment_mode(
            household=household, payer=debtor, receiver=owner,
            payment_mode=Payment.Mode.CUSTOM_AMOUNT, amount=0
        )

@pytest.mark.django_db
def test_wb090_tc04_build_allocations_custom_amount_negative(household, debtor, owner, debt_instance):
    with pytest.raises(ValueError, match="Số tiền thanh toán phải lớn hơn 0."):
        build_allocations_for_payment_mode(
            household=household, payer=debtor, receiver=owner,
            payment_mode=Payment.Mode.CUSTOM_AMOUNT, amount=-100
        )

@pytest.mark.django_db
def test_wb090_tc05_build_allocations_selected_items_empty(household, debtor, owner, debt_instance):
    with pytest.raises(ValueError, match="Vui lòng chọn ít nhất một khoản cần thanh toán."):
        build_allocations_for_payment_mode(
            household=household, payer=debtor, receiver=owner,
            payment_mode=Payment.Mode.SELECTED_ITEMS, debt_ids=[]
        )
