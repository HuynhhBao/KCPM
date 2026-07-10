import pytest
from unittest.mock import patch
from decimal import Decimal
from rest_framework import serializers

from expenses.serializers import ExpenseCreateUpdateSerializer


# =========================
# Helper serializer
# =========================
def make_serializer(user=None, instance=None):
    from unittest.mock import MagicMock

    request = MagicMock()
    request.user = user

    return ExpenseCreateUpdateSerializer(
        instance=instance,
        context={'request': request}
    )


# =========================
# 1. NO REQUEST
# =========================
def test_no_request_raises():
    serializer = ExpenseCreateUpdateSerializer(context={})

    with pytest.raises(serializers.ValidationError):
        serializer.validate({'household': None})


# =========================
# 2. NOT MANAGER (UPDATE)
# =========================
@pytest.mark.django_db
@patch('expenses.serializers.is_user_expense_manager', return_value=False)
def test_not_manager_raises(mock_mgr, user, expense_instance):
    serializer = make_serializer(user, expense_instance)

    with pytest.raises(serializers.ValidationError):
        serializer.validate({})


# =========================
# 3. EMPTY PARTICIPANTS
# =========================
@pytest.mark.django_db
def test_empty_participants_raises(user):
    serializer = make_serializer(user)

    with pytest.raises(serializers.ValidationError):
        serializer.validate({
            'participants': []
        })


# =========================
# 4. DUPLICATE PARTICIPANTS
# =========================
@pytest.mark.django_db
def test_duplicate_participants_raises(user):
    serializer = make_serializer(user)

    with pytest.raises(serializers.ValidationError):
        serializer.validate({
            'participants': [
                {'user_id': user.id},
                {'user_id': user.id}
            ]
        })


# =========================
# 5. HAPPY PATH CREATE
# =========================
@pytest.mark.django_db
def test_happy_path_create(user, household, member2):
    serializer = make_serializer(user)

    result = serializer.validate({
        'household': household,
        'amount': Decimal('100000'),
        'participants': [
            {'user_id': user.id},
            {'user_id': member2.id}
        ]
    })

    assert '_split_items' in result
    assert result['payer'] == user


# =========================
# 6. HAPPY PATH UPDATE (FIXED)
# =========================
@pytest.mark.django_db
def test_happy_path_update(user, expense_instance, member2):
    serializer = make_serializer(user, expense_instance)

    result = serializer.validate({
        'participants': [
            {'user_id': user.id},
            {'user_id': member2.id}   # FIX: đảm bảo KHÔNG trùng
        ]
    })

    assert '_split_items' in result


# =========================
# 7. PARTICIPANT NOT IN HOUSEHOLD
# =========================
@pytest.mark.django_db
def test_participant_not_in_household_raises(user, household):
    serializer = make_serializer(user)

    with pytest.raises(serializers.ValidationError):
        serializer.validate({
            'household': household,
            'amount': Decimal('100000'),
            'participants': [
                {'user_id': 999999}
            ]
        })


# =========================
# 8. VIRTUAL PAYER (FIXED)
# =========================
@pytest.mark.django_db
@patch('expenses.serializers.is_virtual_user', return_value=True)
def test_virtual_payer_raises(mock_virtual, user, household):
    serializer = make_serializer(user)

    with pytest.raises(serializers.ValidationError):
        serializer.validate({
            'household': household,   # FIX: dùng fixture thật, không mock
            'amount': Decimal('100000'),
            'participants': [
                {'user_id': user.id}
            ]
        })