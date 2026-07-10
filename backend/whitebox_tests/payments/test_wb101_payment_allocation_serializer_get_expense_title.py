import pytest
from types import SimpleNamespace
from payments.serializers import PaymentAllocationSerializer

def test_wb101_tc01_get_expense_title_exists():
    serializer = PaymentAllocationSerializer()
    expense = SimpleNamespace(title="Groceries")
    debt = SimpleNamespace(expense=expense)
    allocation = SimpleNamespace(debt=debt)
    assert serializer.get_expense_title(allocation) == "Groceries"

def test_wb101_tc02_get_expense_title_none():
    serializer = PaymentAllocationSerializer()
    debt = SimpleNamespace(expense=None)
    allocation = SimpleNamespace(debt=debt)
    assert serializer.get_expense_title(allocation) == ''
