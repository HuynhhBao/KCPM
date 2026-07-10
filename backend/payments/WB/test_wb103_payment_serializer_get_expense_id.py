import pytest
from types import SimpleNamespace
from payments.serializers import PaymentSerializer

def test_wb103_tc01_get_expense_id_exists():
    serializer = PaymentSerializer()
    debt = SimpleNamespace(expense_id="12345678-1234-1234-1234-123456789012")
    payment = SimpleNamespace(debt=debt)
    assert serializer.get_expense_id(payment) == "12345678-1234-1234-1234-123456789012"

def test_wb103_tc02_get_expense_id_none():
    serializer = PaymentSerializer()
    payment = SimpleNamespace(debt=None)
    assert serializer.get_expense_id(payment) is None
