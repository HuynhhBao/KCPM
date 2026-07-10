from types import SimpleNamespace

from households.views import debt_pending_amount_to_int
from payments.models import Payment


class FakeManager:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self.items


def test_wb031_01_no_pending_payment_returns_zero():
    payment = SimpleNamespace(
        status="APPROVED",
        amount=100000
    )

    debt = SimpleNamespace(
        payments=FakeManager([payment])
    )

    result = debt_pending_amount_to_int(debt)

    assert result == 0


def test_wb031_02_one_pending_payment_returns_amount():
    payment = SimpleNamespace(
        status=Payment.Status.PENDING,
        amount=100000
    )

    debt = SimpleNamespace(
        payments=FakeManager([payment])
    )

    result = debt_pending_amount_to_int(debt)

    assert result == 100000


def test_wb031_03_multiple_payments_only_pending_is_counted():
    pending_payment = SimpleNamespace(
        status=Payment.Status.PENDING,
        amount=50000
    )
    approved_payment = SimpleNamespace(
        status="APPROVED",
        amount=200000
    )

    debt = SimpleNamespace(
        payments=FakeManager([pending_payment, approved_payment])
    )

    result = debt_pending_amount_to_int(debt)

    assert result == 50000


def test_wb031_04_payment_allocations_pending_is_counted():
    normal_payment = SimpleNamespace(
        status="APPROVED",
        amount=100000
    )

    pending_payment = SimpleNamespace(
        status=Payment.Status.PENDING
    )

    allocation = SimpleNamespace(
        payment=pending_payment,
        allocated_amount=30000
    )

    debt = SimpleNamespace(
        payments=FakeManager([normal_payment]),
        payment_allocations=FakeManager([allocation])
    )

    result = debt_pending_amount_to_int(debt)

    assert result == 30000


def test_wb031_05_allocation_without_payment_is_skipped():
    allocation = SimpleNamespace(
        payment=None,
        allocated_amount=30000
    )

    debt = SimpleNamespace(
        payments=FakeManager([]),
        payment_allocations=FakeManager([allocation])
    )

    result = debt_pending_amount_to_int(debt)

    assert result == 0


def test_wb031_06_debt_without_payment_allocations_does_not_error():
    pending_payment = SimpleNamespace(
        status=Payment.Status.PENDING,
        amount=70000
    )

    debt = SimpleNamespace(
        payments=FakeManager([pending_payment])
    )

    result = debt_pending_amount_to_int(debt)

    assert result == 70000