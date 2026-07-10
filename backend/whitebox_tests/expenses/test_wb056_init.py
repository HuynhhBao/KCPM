import pytest
from expenses.serializers import ExpenseCreateUpdateSerializer


@pytest.mark.django_db
def test_init_create_mode_requires_participants_and_household():
    serializer = ExpenseCreateUpdateSerializer()

    assert serializer.fields['participants'].required is True
    assert serializer.fields['household'].required is True
    assert serializer.fields['household'].read_only is False


@pytest.mark.django_db
def test_init_update_mode_makes_household_read_only(expense_instance):
    serializer = ExpenseCreateUpdateSerializer(instance=expense_instance)

    assert serializer.fields['household'].read_only is True