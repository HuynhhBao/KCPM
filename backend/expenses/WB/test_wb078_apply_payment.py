"""
WB_078 — Debt.apply_payment
expenses-service

Chỉ đọc/gán self.amount/self.paid_amount/self.is_paid -> dùng Debt() KHÔNG save,
không cần DB thật.
"""
from decimal import Decimal

from expenses.models import Debt


# ── TC_WB078_01: N2-True (D1: amount == 0, boundary) ──
def test_apply_payment_zero_amount_does_nothing():
    debt = Debt(amount=Decimal(100000), paid_amount=Decimal(20000), is_paid=False)

    debt.apply_payment(0)

    assert debt.paid_amount == Decimal(20000)
    assert debt.is_paid is False


# ── TC_WB078_02: N2-True (D1: amount âm) ──
def test_apply_payment_negative_amount_does_nothing():
    debt = Debt(amount=Decimal(100000), paid_amount=Decimal(20000), is_paid=False)

    debt.apply_payment(-5000)

    assert debt.paid_amount == Decimal(20000)
    assert debt.is_paid is False


# ── TC_WB078_03: N4-True (D2 True), trả một phần, chưa đủ ──
def test_apply_payment_partial_payment_updates_paid_amount():
    debt = Debt(amount=Decimal(100000), paid_amount=Decimal(20000), is_paid=False)

    debt.apply_payment(30000)

    assert debt.paid_amount == Decimal(50000)
    assert debt.is_paid is False


# ── TC_WB078_04: N4-True (D2 True), trả dư, bị min() cap ──
def test_apply_payment_overpayment_is_capped_at_debt_amount():
    debt = Debt(amount=Decimal(100000), paid_amount=Decimal(90000), is_paid=False)

    debt.apply_payment(50000)  # 90000 + 50000 = 140000 > 100000

    assert debt.paid_amount == Decimal(100000)  # bị cap, KHÔNG phải 140000
    assert debt.is_paid is True


# ── TC_WB078_05: N4-False (D2 False), lần trả đầu, trả đủ (boundary ==) ──
def test_apply_payment_first_payment_full_amount_marks_paid():
    debt = Debt(amount=Decimal(100000), paid_amount=None, is_paid=False)

    debt.apply_payment(100000)

    assert debt.paid_amount == Decimal(100000)
    assert debt.is_paid is True


# ── TC_WB078_06: N4-False (D2 False), lần trả đầu, trả thiếu (bổ sung) ──
def test_apply_payment_first_partial_payment_not_marked_paid():
    debt = Debt(amount=Decimal(100000), paid_amount=None, is_paid=False)

    debt.apply_payment(40000)

    assert debt.paid_amount == Decimal(40000)
    assert debt.is_paid is False