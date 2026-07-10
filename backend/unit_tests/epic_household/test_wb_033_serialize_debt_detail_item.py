from types import SimpleNamespace
from datetime import date, datetime

from households.views import serialize_debt_detail_item


class FakeManager:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self.items


def make_user(user_id, email, full_name="User"):
    return SimpleNamespace(
        id=user_id,
        email=email,
        full_name=full_name
    )


def test_wb033_01_payable_amount_less_than_zero_reset_to_zero():
    from_user = make_user(1, "from@gmail.com", "From User")
    to_user = make_user(2, "to@gmail.com", "To User")
    payer = make_user(3, "payer@gmail.com", "Payer User")

    expense = SimpleNamespace(
        title="Ăn tối",
        expense_date=date(2026, 6, 1),
        payer=payer
    )

    debt = SimpleNamespace(
        id=1,
        expense_id=10,
        expense=expense,
        amount=100000,
        paid_amount=20000,
        is_paid=False,
        from_user_id=1,
        from_user=from_user,
        to_user_id=2,
        to_user=to_user,
        payments=FakeManager([
            SimpleNamespace(status="pending", amount=90000)
        ]),
        created_at=datetime(2026, 6, 1, 10, 0),
        updated_at=datetime(2026, 6, 1, 11, 0),
    )

    result = serialize_debt_detail_item(
        debt=debt,
        direction="i_owe",
        request=None
    )

    assert result["payable_amount"] == 0
    assert result["remaining_after_pending"] == 0


def test_wb033_02_date_fields_none_return_empty_string():
    from_user = make_user(1, "from@gmail.com", "From User")
    to_user = make_user(2, "to@gmail.com", "To User")

    expense = SimpleNamespace(
        title="Ăn tối",
        expense_date=None,
        payer=None
    )

    debt = SimpleNamespace(
        id=1,
        expense_id=10,
        expense=expense,
        amount=100000,
        paid_amount=0,
        is_paid=False,
        from_user_id=1,
        from_user=from_user,
        to_user_id=2,
        to_user=to_user,
        payments=FakeManager([]),
        created_at=None,
        updated_at=None,
    )

    result = serialize_debt_detail_item(
        debt=debt,
        direction="i_owe",
        request=None
    )

    assert result["expense_date"] == ""
    assert result["created_at"] == ""
    assert result["updated_at"] == ""
    assert result["paid_at"] == ""