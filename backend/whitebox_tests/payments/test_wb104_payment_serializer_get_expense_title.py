import pytest
from types import SimpleNamespace
from payments.serializers import PaymentSerializer

def test_wb104_tc01_get_expense_title_exists():
    serializer = PaymentSerializer()
    expense = SimpleNamespace(title="Groceries")
    debt = SimpleNamespace(expense=expense)
    payment = SimpleNamespace(debt=debt)
    assert serializer.get_expense_title(payment) == "Groceries"

def test_wb104_tc02_get_expense_title_none():
    serializer = PaymentSerializer()
    payment = SimpleNamespace(debt=None)
    assert serializer.get_expense_title(payment) == ''
