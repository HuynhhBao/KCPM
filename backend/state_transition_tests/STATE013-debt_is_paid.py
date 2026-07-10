from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model

from expenses.models import Debt, Expense
from expenses.serializers import ExpenseCreateUpdateSerializer
from households.models import Household, HouseholdMember


pytestmark = pytest.mark.django_db


def create_user(email, full_name="Test User"):
    User = get_user_model()
    username = email.split("@")[0]

    return User.objects.create_user(
        username=username,
        email=email,
        password="StrongPass123",
        full_name=full_name,
    )


def create_household_with_members(owner, *members):
    household = Household.objects.create(
        name="Shared Home",
        owner=owner,
    )

    HouseholdMember.objects.create(
        household=household,
        user=owner,
        role=HouseholdMember.Role.OWNER,
    )

    for member in members:
        HouseholdMember.objects.create(
            household=household,
            user=member,
            role=HouseholdMember.Role.MEMBER,
        )

    return household


def create_expense(household, payer, amount=Decimal("100")):
    return Expense.objects.create(
        household=household,
        title="Dinner",
        amount=amount,
        payer=payer,
        split_type=Expense.SplitType.EQUAL,
    )


def create_debt(household, expense, from_user, to_user, amount=Decimal("100")):
    return Debt.objects.create(
        household=household,
        expense=expense,
        from_user=from_user,
        to_user=to_user,
        amount=amount,
    )


class TestDebtStateTransition:
    def test_apply_payment_marks_debt_paid_when_paid_amount_reaches_amount(self):
        payer = create_user("payer@example.com", "Payer")
        debtor = create_user("debtor@example.com", "Debtor")
        household = create_household_with_members(payer, debtor)
        expense = create_expense(household, payer)
        debt = create_debt(
            household=household,
            expense=expense,
            from_user=debtor,
            to_user=payer,
            amount=Decimal("100"),
        )

        assert debt.is_paid is False

        debt.apply_payment(Decimal("100"))

        assert debt.paid_amount == Decimal("100")
        assert debt.is_paid is True
        assert debt.remaining_amount == Decimal("0")

    def test_apply_payment_keeps_debt_unpaid_when_payment_is_partial(self):
        payer = create_user("payer-partial@example.com", "Payer")
        debtor = create_user("debtor-partial@example.com", "Debtor")
        household = create_household_with_members(payer, debtor)
        expense = create_expense(household, payer)
        debt = create_debt(
            household=household,
            expense=expense,
            from_user=debtor,
            to_user=payer,
            amount=Decimal("100"),
        )

        debt.apply_payment(Decimal("40"))

        assert debt.paid_amount == Decimal("40")
        assert debt.is_paid is False
        assert debt.remaining_amount == Decimal("60")

    def test_mark_fully_paid_sets_paid_amount_to_amount_and_marks_paid(self):
        payer = create_user("payer-full@example.com", "Payer")
        debtor = create_user("debtor-full@example.com", "Debtor")
        household = create_household_with_members(payer, debtor)
        expense = create_expense(household, payer)
        debt = create_debt(
            household=household,
            expense=expense,
            from_user=debtor,
            to_user=payer,
            amount=Decimal("150"),
        )

        debt.mark_fully_paid()

        assert debt.paid_amount == debt.amount == Decimal("150")
        assert debt.is_paid is True
        assert debt.remaining_amount == Decimal("0")


class TestExpenseCreateUpdateSerializerDebtSync:
    def test_update_replaces_old_debts_with_fresh_unpaid_debts(self):
        payer = create_user("payer-sync@example.com", "Payer")
        debtor = create_user("debtor-sync@example.com", "Debtor")
        new_debtor = create_user("new-debtor-sync@example.com", "New Debtor")
        household = create_household_with_members(payer, debtor, new_debtor)
        expense = create_expense(household, payer, amount=Decimal("100"))
        old_debt = create_debt(
            household=household,
            expense=expense,
            from_user=debtor,
            to_user=payer,
            amount=Decimal("50"),
        )
        old_debt.apply_payment(Decimal("25"))
        old_debt.save(update_fields=["paid_amount", "is_paid"])

        serializer = ExpenseCreateUpdateSerializer(
            instance=expense,
            data={
                "title": "Updated dinner",
                "amount": "120",
                "split_type": Expense.SplitType.EQUAL,
                "participants": [
                    {"user_id": payer.id},
                    {"user_id": debtor.id},
                    {"user_id": new_debtor.id},
                ],
            },
            context={"request": SimpleNamespace(user=payer)},
        )

        assert serializer.is_valid(), serializer.errors
        serializer.save()

        assert not Debt.objects.filter(id=old_debt.id).exists()

        new_debts = Debt.objects.filter(expense=expense).order_by("from_user__email")
        assert new_debts.count() == 2

        for debt in new_debts:
            assert debt.to_user == payer
            assert debt.amount == Decimal("40")
            assert debt.paid_amount == Decimal("0")
            assert debt.is_paid is False