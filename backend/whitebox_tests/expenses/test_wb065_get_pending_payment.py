#WB 065
"""
WB_065 — DebtSerializer.get_pending_payment
expenses-service

⚠ Field name của Payment (household, payer, receiver, status, debt/related_name='payments')
là suy đoán từ cách dùng trong serializers.py — chỉnh lại nếu model thật khác.
"""
import pytest

from expenses.serializers import DebtSerializer
from payments.models import Payment


# ── TC_WB065_01: N2-True (payment tìm thấy trực tiếp từ debt.payments) ──
@pytest.mark.django_db
def test_get_pending_payment_found_directly_on_debt(debt_instance):
    payment = Payment.objects.create(
        household=debt_instance.household,
        debt=debt_instance,
        payer=debt_instance.from_user,
        receiver=debt_instance.to_user,
        status='pending',
        amount=100000,
    )
    serializer = DebtSerializer()

    result = serializer.get_pending_payment(debt_instance)

    assert result == payment


# ── TC_WB065_02: N2-False, tìm thấy ở household level ──
@pytest.mark.django_db
def test_get_pending_payment_falls_back_to_household_level(debt_instance):
    # KHÔNG truyền debt=debt_instance -> không nằm trong debt.payments trực tiếp
    payment = Payment.objects.create(
        household=debt_instance.household,
        payer=debt_instance.from_user,
        receiver=debt_instance.to_user,
        status='pending',
        amount=100000,
    )
    serializer = DebtSerializer()

    result = serializer.get_pending_payment(debt_instance)

    assert result == payment


# ── TC_WB065_03: N2-False, không tìm thấy gì (bổ sung) ──
@pytest.mark.django_db
def test_get_pending_payment_returns_none_when_not_found(debt_instance):
    serializer = DebtSerializer()

    result = serializer.get_pending_payment(debt_instance)

    assert result is None