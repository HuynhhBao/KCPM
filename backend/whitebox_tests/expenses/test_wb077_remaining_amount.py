"""
WB_077 — Debt.remaining_amount (property)
expenses-service

Chỉ đọc self.amount/self.paid_amount -> dùng Debt() KHÔNG save (không cần DB/FK
household/expense/from_user/to_user thật vì property này không đụng tới chúng).
"""
from decimal import Decimal

from expenses.models import Debt


# ── TC_WB077_01: D1-True, D2-False ──
def test_remaining_amount_returns_difference_when_positive():
    debt = Debt(amount=Decimal(100000), paid_amount=Decimal(30000))

    assert debt.remaining_amount == Decimal(70000)


# ── TC_WB077_02: D1-True, D2-True (remaining âm) ──
def test_remaining_amount_returns_zero_when_overpaid():
    debt = Debt(amount=Decimal(100000), paid_amount=Decimal(120000))

    assert debt.remaining_amount == Decimal('0')


# ── TC_WB077_03: D1-True, D2-True (remaining == 0, boundary) ──
def test_remaining_amount_returns_zero_at_exact_boundary():
    debt = Debt(amount=Decimal(100000), paid_amount=Decimal(100000))

    assert debt.remaining_amount == Decimal('0')


# ── TC_WB077_04: D1-False, D2-False ──
def test_remaining_amount_treats_none_paid_amount_as_zero():
    debt = Debt(amount=Decimal(50000), paid_amount=None)

    assert debt.remaining_amount == Decimal(50000)


# ── TC_WB077_05: D1-False, D2-True (bổ sung) ──
def test_remaining_amount_returns_zero_when_amount_zero_and_no_paid():
    debt = Debt(amount=Decimal(0), paid_amount=None)

    assert debt.remaining_amount == Decimal('0')