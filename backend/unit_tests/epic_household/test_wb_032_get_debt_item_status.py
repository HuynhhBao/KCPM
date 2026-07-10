from types import SimpleNamespace

from households.views import get_debt_item_status


def test_wb032_01_is_paid_returns_paid():
    debt = SimpleNamespace(
        is_paid=True,
        amount=100000,
        paid_amount=0
    )

    result = get_debt_item_status(debt, pending_amount=0)

    assert result == "paid"


def test_wb032_02_remaining_less_than_or_equal_zero_returns_paid():
    debt = SimpleNamespace(
        is_paid=False,
        amount=100000,
        paid_amount=100000
    )

    result = get_debt_item_status(debt, pending_amount=0)

    assert result == "paid"


def test_wb032_03_pending_and_paid_returns_partial_paid_pending():
    debt = SimpleNamespace(
        is_paid=False,
        amount=100000,
        paid_amount=20000
    )

    result = get_debt_item_status(debt, pending_amount=30000)

    assert result == "partial_paid_pending"


def test_wb032_04_only_pending_returns_pending():
    debt = SimpleNamespace(
        is_paid=False,
        amount=100000,
        paid_amount=0
    )

    result = get_debt_item_status(debt, pending_amount=30000)

    assert result == "pending"


def test_wb032_05_only_paid_returns_partial_paid():
    debt = SimpleNamespace(
        is_paid=False,
        amount=100000,
        paid_amount=20000
    )

    result = get_debt_item_status(debt, pending_amount=0)

    assert result == "partial_paid"


def test_wb032_06_no_pending_no_paid_returns_unpaid():
    debt = SimpleNamespace(
        is_paid=False,
        amount=100000,
        paid_amount=0
    )

    result = get_debt_item_status(debt, pending_amount=0)

    assert result == "unpaid"