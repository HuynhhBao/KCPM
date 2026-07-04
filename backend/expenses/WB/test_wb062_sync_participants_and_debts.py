import pytest
from unittest.mock import patch
from decimal import Decimal

from expenses.serializers import ExpenseCreateUpdateSerializer
from expenses.models import ExpenseParticipant, Debt


@pytest.fixture
def serializer():
    return ExpenseCreateUpdateSerializer()


# ── TC_WB062_01 ──
@pytest.mark.django_db
def test_sync_empty_split_items(serializer, expense_instance):
    expense_instance.participants.all().delete()
    expense_instance.debts.all().delete()

    serializer._sync_participants_and_debts(
        expense=expense_instance,
        split_items=[],
    )

    assert ExpenseParticipant.objects.filter(expense=expense_instance).count() == 0
    assert Debt.objects.filter(expense=expense_instance).count() == 0


# ── TC_WB062_02 ──
@pytest.mark.django_db
def test_sync_payer_skips_debt_creation(serializer, expense_instance, user):
    split_items = [(user, Decimal("100000"))]

    serializer._sync_participants_and_debts(
        expense=expense_instance,
        split_items=split_items,
    )

    assert ExpenseParticipant.objects.filter(expense=expense_instance).count() == 1
    assert Debt.objects.filter(expense=expense_instance).count() == 0


# ── TC_WB062_03 ──
@pytest.mark.django_db
@patch("expenses.serializers.create_notification")
def test_sync_no_notification_when_disabled(mock_notify, serializer, expense_instance, member2):
    split_items = [(member2, Decimal("50000"))]

    serializer._sync_participants_and_debts(
        expense=expense_instance,
        split_items=split_items,
        send_notifications=False,
    )

    assert Debt.objects.count() == 1
    mock_notify.assert_not_called()


# ── TC_WB062_04 ──
@pytest.mark.django_db
@patch("expenses.serializers.create_notification")
@patch("expenses.serializers.is_virtual_user", side_effect=lambda u: getattr(u, "is_virtual", False))
def test_sync_no_notification_when_user_is_virtual(mock_virtual, mock_notify,
                                                   serializer, expense_instance, virtual_user):
    split_items = [(virtual_user, Decimal("50000"))]

    serializer._sync_participants_and_debts(
        expense=expense_instance,
        split_items=split_items,
        send_notifications=True,
    )

    mock_notify.assert_not_called()


# ── TC_WB062_05 ──
@pytest.mark.django_db
@patch("expenses.serializers.create_notification")
@patch("expenses.serializers.is_virtual_user", side_effect=lambda u: getattr(u, "is_virtual", False))
def test_sync_no_notification_when_payer_is_virtual(mock_virtual, mock_notify,
                                                    serializer, expense_instance_virtual_payer,
                                                    member2):
    split_items = [(member2, Decimal("50000"))]

    serializer._sync_participants_and_debts(
        expense=expense_instance_virtual_payer,
        split_items=split_items,
        send_notifications=True,
    )

    mock_notify.assert_not_called()


# ── TC_WB062_06 ──
@pytest.mark.django_db
@patch("expenses.serializers.create_notification")
@patch("expenses.serializers.is_virtual_user", return_value=False)
def test_sync_sends_notification_when_all_conditions_met(mock_virtual, mock_notify,
                                                         serializer, expense_instance, member2):
    split_items = [(member2, Decimal("50000"))]

    serializer._sync_participants_and_debts(
        expense=expense_instance,
        split_items=split_items,
        send_notifications=True,
    )

    assert Debt.objects.count() == 1
    mock_notify.assert_called_once()


# ── TC_WB062_07 ──
@pytest.mark.django_db
@patch("expenses.serializers.create_notification")
@patch("expenses.serializers.is_virtual_user", return_value=False)
def test_sync_multiple_split_items_mix(mock_virtual, mock_notify,
                                      serializer, expense_instance, user, member2, member3):

    split_items = [
        (user, Decimal("40000")),
        (member2, Decimal("30000")),
        (member3, Decimal("30000")),
    ]

    serializer._sync_participants_and_debts(
        expense=expense_instance,
        split_items=split_items,
        send_notifications=True,
    )

    assert ExpenseParticipant.objects.filter(expense=expense_instance).count() == 3
    assert Debt.objects.filter(expense=expense_instance).count() == 2
    assert mock_notify.call_count == 2