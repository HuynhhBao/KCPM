import os
import sys
import uuid
from decimal import Decimal
from pathlib import Path

import django
import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate

from expenses.models import Debt, Expense
from households.models import Household, HouseholdMember
from payments.models import Payment
from payments.views import (
    ConfirmPaymentView,
    MarkDebtPaidView,
    RecordVirtualReceiptView,
    RejectPaymentView,
)


pytestmark = pytest.mark.django_db


def unique_email(prefix):
    return f"{prefix}-{uuid.uuid4().hex}@example.com"


def create_user(prefix, full_name="Test User"):
    User = get_user_model()
    email = unique_email(prefix)

    return User.objects.create_user(
        username=email.split("@")[0],
        email=email,
        password="StrongPass123",
        full_name=full_name,
    )


def create_virtual_user(prefix="virtual", full_name="Virtual Member"):
    User = get_user_model()
    email = f"{prefix}-{uuid.uuid4().hex}@virtual.chungvi.local"

    return User.objects.create_user(
        username=email.split("@")[0],
        email=email,
        password="StrongPass123",
        full_name=full_name,
    )


def create_household_with_members(owner, *members):
    household = Household.objects.create(
        name=f"Payment State Household {uuid.uuid4().hex}",
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
        title="Payment status expense",
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


def post_view(view_class, user, url, data=None, **kwargs):
    factory = APIRequestFactory()
    request = factory.post(url, data or {}, format="json")
    force_authenticate(request, user=user)
    return view_class.as_view()(request, **kwargs)


class TestConfirmPaymentView:
    def test_post_changes_pending_payment_to_confirmed(self):
        payer = create_user("confirm-payer", "Payer")
        receiver = create_user("confirm-receiver", "Receiver")
        household = create_household_with_members(receiver, payer)
        expense = create_expense(household, receiver)
        debt = create_debt(household, expense, payer, receiver, Decimal("100"))
        payment = Payment.objects.create(
            debt=debt,
            household=household,
            payer=payer,
            receiver=receiver,
            amount=Decimal("100"),
        )

        response = post_view(
            ConfirmPaymentView,
            receiver,
            f"/payments/{payment.id}/confirm/",
            {"note": "confirmed"},
            pk=payment.id,
        )

        assert response.status_code == 200
        payment.refresh_from_db()
        debt.refresh_from_db()
        assert payment.status == Payment.Status.CONFIRMED
        assert payment.confirmed_at is not None
        assert payment.receiver_note == "confirmed"
        assert debt.is_paid is True
        assert debt.paid_amount == Decimal("100")


class TestRejectPaymentView:
    def test_post_changes_pending_payment_to_rejected(self):
        payer = create_user("reject-payer", "Payer")
        receiver = create_user("reject-receiver", "Receiver")
        household = create_household_with_members(receiver, payer)
        expense = create_expense(household, receiver)
        debt = create_debt(household, expense, payer, receiver, Decimal("100"))
        payment = Payment.objects.create(
            debt=debt,
            household=household,
            payer=payer,
            receiver=receiver,
            amount=Decimal("100"),
        )

        response = post_view(
            RejectPaymentView,
            receiver,
            f"/payments/{payment.id}/reject/",
            {"note": "rejected"},
            pk=payment.id,
        )

        assert response.status_code == 200
        payment.refresh_from_db()
        debt.refresh_from_db()
        assert payment.status == Payment.Status.REJECTED
        assert payment.rejected_at is not None
        assert payment.receiver_note == "rejected"
        assert debt.is_paid is False
        assert debt.paid_amount == Decimal("0")


class TestRecordVirtualReceiptView:
    def test_post_creates_confirmed_payment_for_virtual_receipt(self):
        receiver = create_user("virtual-receiver", "Receiver")
        virtual_payer = create_virtual_user("virtual-payer", "Virtual Payer")
        household = create_household_with_members(receiver, virtual_payer)
        expense = create_expense(household, receiver)
        debt = create_debt(
            household,
            expense,
            virtual_payer,
            receiver,
            Decimal("100"),
        )

        response = post_view(
            RecordVirtualReceiptView,
            receiver,
            f"/payments/households/{household.id}/virtual-receipts/",
            {
                "virtual_user_id": virtual_payer.id,
                "payment_mode": Payment.Mode.CUSTOM_AMOUNT,
                "amount": "100",
                "note": "received outside app",
            },
            household_id=household.id,
        )

        assert response.status_code == 201
        payment = Payment.objects.get(
            household=household,
            payer=virtual_payer,
            receiver=receiver,
        )
        debt.refresh_from_db()
        assert payment.status == Payment.Status.CONFIRMED
        assert payment.confirmed_at is not None
        assert payment.is_pair_payment is True
        assert payment.receiver_note == "received outside app"
        assert debt.is_paid is True
        assert debt.paid_amount == Decimal("100")


class TestMarkDebtPaidView:
    def test_post_creates_new_payment_with_pending_default_status(self):
        payer = create_user("mark-paid-payer", "Payer")
        receiver = create_user("mark-paid-receiver", "Receiver")
        household = create_household_with_members(receiver, payer)
        expense = create_expense(household, receiver)
        debt = create_debt(household, expense, payer, receiver, Decimal("100"))

        response = post_view(
            MarkDebtPaidView,
            payer,
            f"/payments/debts/{debt.id}/mark-paid/",
            {"note": "paid"},
            debt_id=debt.id,
        )

        assert response.status_code == 201
        payment = Payment.objects.get(debt=debt)
        debt.refresh_from_db()
        assert payment.status == Payment.Status.PENDING
        assert payment.payer == payer
        assert payment.receiver == receiver
        assert payment.amount == Decimal("100")
        assert payment.payer_note == "paid"
        assert debt.is_paid is False
        assert debt.paid_amount == Decimal("0")