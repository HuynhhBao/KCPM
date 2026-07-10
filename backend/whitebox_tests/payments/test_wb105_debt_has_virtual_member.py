import pytest
from payments.views import debt_has_virtual_member
from expenses.models import Debt
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_wb105_tc01_from_user_is_virtual(virtual_user, owner):
    debt = Debt(from_user=virtual_user, to_user=owner)
    assert debt_has_virtual_member(debt) is True

@pytest.mark.django_db
def test_wb105_tc02_to_user_is_virtual(virtual_user, owner):
    debt = Debt(from_user=owner, to_user=virtual_user)
    assert debt_has_virtual_member(debt) is True

@pytest.mark.django_db
def test_wb105_tc03_neither_is_virtual(owner, member):
    debt = Debt(from_user=owner, to_user=member)
    assert debt_has_virtual_member(debt) is False
