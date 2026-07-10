import pytest
from types import SimpleNamespace
from payments.serializers import PaymentAllocationSerializer

def test_wb100_tc01_get_expense_id_exists():
    serializer = PaymentAllocationSerializer()
    debt = SimpleNamespace(expense_id="12345678-1234-1234-1234-123456789012")
    allocation = SimpleNamespace(debt=debt)
    assert serializer.get_expense_id(allocation) == "12345678-1234-1234-1234-123456789012"

def test_wb100_tc02_get_expense_id_none():
    serializer = PaymentAllocationSerializer()
    debt = SimpleNamespace(expense_id=None)
    allocation = SimpleNamespace(debt=debt)
    assert serializer.get_expense_id(allocation) is None
