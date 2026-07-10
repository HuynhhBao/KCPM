from decimal import Decimal
import pytest
from payments.models import Payment, PaymentAllocation
from payments.views import get_pending_amount_for_debt

@pytest.mark.django_db
def test_wb087_tc01_pending_amount_greater_than_zero(debt_instance, owner, debtor, household):
    payment_pending = Payment.objects.create(
        household=household, payer=debtor, receiver=owner, amount=20000, status=Payment.Status.PENDING
    )
    PaymentAllocation.objects.create(payment=payment_pending, debt=debt_instance, allocated_amount=Decimal('20000'))
    assert get_pending_amount_for_debt(debt_instance) == Decimal('20000')

@pytest.mark.django_db
def test_wb087_tc02_pending_amount_is_zero_other_user(debt_instance):
    assert get_pending_amount_for_debt(debt_instance) == Decimal('0')
