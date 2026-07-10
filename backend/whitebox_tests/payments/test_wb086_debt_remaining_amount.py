from decimal import Decimal
import pytest
from expenses.models import Debt
from payments.views import debt_remaining_amount

def test_wb086_tc01_remaining_amount_greater_than_zero():
    debt = Debt(amount=Decimal('50000'), paid_amount=Decimal('20000'))
    assert debt_remaining_amount(debt) == Decimal('30000')

def test_wb086_tc02_remaining_amount_equals_zero_fully_paid():
    debt = Debt(amount=Decimal('50000'), paid_amount=Decimal('50000'))
    assert debt_remaining_amount(debt) == Decimal('0')
