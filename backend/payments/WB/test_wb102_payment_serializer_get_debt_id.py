import pytest
from payments.serializers import PaymentSerializer
from payments.models import Payment

def test_wb102_tc01_get_debt_id_exists():
    serializer = PaymentSerializer()
    payment = Payment(debt_id="12345678-1234-1234-1234-123456789012")
    assert serializer.get_debt_id(payment) == "12345678-1234-1234-1234-123456789012"

def test_wb102_tc02_get_debt_id_none():
    serializer = PaymentSerializer()
    payment = Payment(debt_id=None)
    assert serializer.get_debt_id(payment) is None
