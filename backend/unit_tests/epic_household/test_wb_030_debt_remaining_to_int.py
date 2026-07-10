from types import SimpleNamespace

from households.views import debt_remaining_to_int


def test_wb030_01_remaining_equal_zero_returns_zero():
    debt = SimpleNamespace(
        amount=100000,
        paid_amount=100000
    )

    result = debt_remaining_to_int(debt)

    assert result == 0


def test_wb030_02_remaining_less_than_zero_returns_zero():
    debt = SimpleNamespace(
        amount=100000,
        paid_amount=150000
    )

    result = debt_remaining_to_int(debt)

    assert result == 0


def test_wb030_03_remaining_greater_than_zero_returns_int():
    debt = SimpleNamespace(
        amount=100000,
        paid_amount=30000
    )

    result = debt_remaining_to_int(debt)

    assert result == 70000