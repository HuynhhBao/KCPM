import os
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import django
from django.test import TestCase

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.contrib.auth import get_user_model
from expenses.models import Debt, Expense
from expenses.serializers import ExpenseCreateUpdateSerializer
from households.models import Household, HouseholdMember


class ExpenseCreateUpdateSerializerTestCase(TestCase):
    def create_user(self, email, full_name="Test User"):
        User = get_user_model()
        username = email.replace("@", "_").replace(".", "_")

        return User.objects.create_user(
            username=username,
            email=email,
            password="StrongPass123",
            full_name=full_name,
        )

    def create_household_with_members(self, owner, *members):
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

    def create_expense(self, household, payer, amount=Decimal("101")):
        return Expense.objects.create(
            household=household,
            title="Dinner",
            amount=amount,
            payer=payer,
            split_type=Expense.SplitType.EQUAL,
        )

    def create_debt(self, household, expense, from_user, to_user, amount):
        return Debt.objects.create(
            household=household,
            expense=expense,
            from_user=from_user,
            to_user=to_user,
            amount=amount,
        )

    def make_serializer_context(self, user):
        return {"request": SimpleNamespace(user=user)}

    def test_build_split_items_equal_divides_evenly_and_assigns_remainder_to_first_user(self):
        payer = self.create_user("payer-equal@example.com", "Payer")
        member_a = self.create_user("member-a-equal@example.com", "Member A")
        member_b = self.create_user("member-b-equal@example.com", "Member B")
        serializer = ExpenseCreateUpdateSerializer()
        participants = [
            {"user_id": payer.id},
            {"user_id": member_a.id},
            {"user_id": member_b.id},
        ]
        users_by_id = {
            payer.id: payer,
            member_a.id: member_a,
            member_b.id: member_b,
        }

        split_items = serializer._build_split_items(
            amount=Decimal("101"),
            split_type=Expense.SplitType.EQUAL,
            participants=participants,
            users_by_id=users_by_id,
        )

        assert split_items == [
            (payer, Decimal("35")),
            (member_a, Decimal("33")),
            (member_b, Decimal("33")),
        ]

    def test_build_split_items_manual_uses_input_share_amounts(self):
        payer = self.create_user("payer-manual@example.com", "Payer")
        member = self.create_user("member-manual@example.com", "Member")
        serializer = ExpenseCreateUpdateSerializer()
        participants = [
            {"user_id": payer.id, "share_amount": Decimal("70")},
            {"user_id": member.id, "share_amount": Decimal("30")},
        ]
        users_by_id = {
            payer.id: payer,
            member.id: member,
        }

        split_items = serializer._build_split_items(
            amount=Decimal("100"),
            split_type=Expense.SplitType.MANUAL,
            participants=participants,
            users_by_id=users_by_id,
        )

        assert split_items == [
            (payer, Decimal("70")),
            (member, Decimal("30")),
        ]

    def test_validate_rejects_manual_split_when_share_total_differs_from_amount(self):
        payer = self.create_user("payer-invalid-manual@example.com", "Payer")
        member = self.create_user("member-invalid-manual@example.com", "Member")
        household = self.create_household_with_members(payer, member)
        serializer = ExpenseCreateUpdateSerializer(
            data={
                "household": household.id,
                "title": "Manual split",
                "amount": "100",
                "split_type": Expense.SplitType.MANUAL,
                "participants": [
                    {"user_id": payer.id, "share_amount": "70"},
                    {"user_id": member.id, "share_amount": "20"},
                ],
            },
            context=self.make_serializer_context(payer),
        )

        assert serializer.is_valid() is False
        assert "Tổng số tiền chia phải bằng tổng khoản chi." in str(serializer.errors)

    def test_validate_accepts_manual_split_when_share_total_equals_amount(self):
        payer = self.create_user("payer-valid-manual@example.com", "Payer")
        member = self.create_user("member-valid-manual@example.com", "Member")
        household = self.create_household_with_members(payer, member)
        serializer = ExpenseCreateUpdateSerializer(
            data={
                "household": household.id,
                "title": "Manual split",
                "amount": "100",
                "split_type": Expense.SplitType.MANUAL,
                "participants": [
                    {"user_id": payer.id, "share_amount": "70"},
                    {"user_id": member.id, "share_amount": "30"},
                ],
            },
            context=self.make_serializer_context(payer),
        )

        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["_split_items"] == [
            (payer, Decimal("70")),
            (member, Decimal("30")),
        ]

    def test_update_changing_split_type_deletes_old_debts_and_recreates_from_new_split_logic(self):
        payer = self.create_user("payer-sync-split@example.com", "Payer")
        member_a = self.create_user("member-a-sync-split@example.com", "Member A")
        member_b = self.create_user("member-b-sync-split@example.com", "Member B")
        household = self.create_household_with_members(payer, member_a, member_b)
        expense = self.create_expense(household, payer, amount=Decimal("101"))
        old_debt = self.create_debt(
            household=household,
            expense=expense,
            from_user=member_a,
            to_user=payer,
            amount=Decimal("33"),
        )

        serializer = ExpenseCreateUpdateSerializer(
            instance=expense,
            data={
                "title": "Manual dinner",
                "amount": "90",
                "split_type": Expense.SplitType.MANUAL,
                "participants": [
                    {"user_id": payer.id, "share_amount": "30"},
                    {"user_id": member_a.id, "share_amount": "20"},
                    {"user_id": member_b.id, "share_amount": "40"},
                ],
            },
            context=self.make_serializer_context(payer),
        )

        assert serializer.is_valid(), serializer.errors
        updated_expense = serializer.save()

        assert updated_expense.split_type == Expense.SplitType.MANUAL
        assert not Debt.objects.filter(id=old_debt.id).exists()

        new_debts = Debt.objects.filter(expense=updated_expense).order_by("amount")
        assert list(new_debts.values_list("from_user", "amount", "is_paid")) == [
            (member_a.id, Decimal("20"), False),
            (member_b.id, Decimal("40"), False),
        ]