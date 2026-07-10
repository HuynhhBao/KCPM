from decimal import Decimal
from unittest.mock import patch
import pytest
from payments.views import get_debt_payable_amount
from expenses.models import Debt

def test_wb088_tc01_payable_amount_greater_than_zero():
    debt = Debt(amount=Decimal('50000'), paid_amount=Decimal('10000'))
    with patch('payments.views.get_pending_amount_for_debt', return_value=Decimal('15000')):
        assert get_debt_payable_amount(debt) == Decimal('25000')

def test_wb088_tc02_payable_amount_is_zero():
    debt = Debt(amount=Decimal('50000'), paid_amount=Decimal('10000'))
    with patch('payments.views.get_pending_amount_for_debt', return_value=Decimal('45000')):
        assert get_debt_payable_amount(debt) == Decimal('0')
