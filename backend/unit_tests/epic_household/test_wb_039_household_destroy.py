from types import SimpleNamespace
from unittest.mock import patch

from households.views import HouseholdDetailView
from households.models import HouseholdMember
from rest_framework import status
import pytest
from households.views import HouseholdDetailView
from households.models import HouseholdMember
from rest_framework import status

pytestmark = pytest.mark.django_db


class FakeQuerySet:
    def __init__(self, result=None, exists_result=False):
        self.result = result
        self.exists_result = exists_result

    def filter(self, *args, **kwargs):
        return self

    def select_for_update(self):
        return self

    def first(self):
        return self.result

    def exists(self):
        return self.exists_result


def make_request(user):
    return SimpleNamespace(user=user)


def test_wb039_01_household_not_found_returns_404():
    view = HouseholdDetailView()
    request = make_request(SimpleNamespace(id=1, email="owner@gmail.com"))

    with patch("households.views.Household.objects.select_for_update") as mock_household_qs:
        mock_household_qs.return_value.filter.return_value.first.return_value = None

        response = view.destroy(request, pk=1)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_wb039_02_user_not_member_returns_403():
    view = HouseholdDetailView()
    user = SimpleNamespace(id=1, email="user@gmail.com")
    household = SimpleNamespace(id=1, is_active=True)

    with patch("households.views.Household.objects.select_for_update") as mock_household_qs, \
         patch("households.views.HouseholdMember.objects.filter") as mock_member_filter:

        mock_household_qs.return_value.filter.return_value.first.return_value = household
        mock_member_filter.return_value.first.return_value = None

        response = view.destroy(make_request(user), pk=1)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_wb039_03_user_not_owner_returns_403():
    view = HouseholdDetailView()
    user = SimpleNamespace(id=1, email="member@gmail.com")
    household = SimpleNamespace(id=1, is_active=True)
    membership = SimpleNamespace(role=HouseholdMember.Role.MEMBER)

    with patch("households.views.Household.objects.select_for_update") as mock_household_qs, \
         patch("households.views.HouseholdMember.objects.filter") as mock_member_filter:

        mock_household_qs.return_value.filter.return_value.first.return_value = household
        mock_member_filter.return_value.first.return_value = membership

        response = view.destroy(make_request(user), pk=1)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_wb039_04_has_unpaid_debt_returns_400():
    view = HouseholdDetailView()
    user = SimpleNamespace(id=1, email="owner@gmail.com")
    household = SimpleNamespace(id=1, is_active=True)
    membership = SimpleNamespace(role=HouseholdMember.Role.OWNER)

    with patch("households.views.Household.objects.select_for_update") as mock_household_qs, \
         patch("households.views.HouseholdMember.objects.filter") as mock_member_filter, \
         patch("households.views.Debt.objects.filter") as mock_debt_filter:

        mock_household_qs.return_value.filter.return_value.first.return_value = household
        mock_member_filter.return_value.first.return_value = membership
        mock_debt_filter.return_value.exists.return_value = True

        response = view.destroy(make_request(user), pk=1)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_wb039_05_owner_can_soft_delete_household_returns_200():
    view = HouseholdDetailView()
    user = SimpleNamespace(id=1, email="owner@gmail.com")
    household = SimpleNamespace(
        id=1,
        name="Nhóm test",
        is_active=True,
        save=lambda update_fields=None: None
    )
    membership = SimpleNamespace(role=HouseholdMember.Role.OWNER)

    with patch("households.views.Household.objects.select_for_update") as mock_household_qs, \
         patch("households.views.HouseholdMember.objects.filter") as mock_member_filter, \
         patch("households.views.Debt.objects.filter") as mock_debt_filter, \
         patch("households.views.Activity.objects.create"):

        mock_household_qs.return_value.filter.return_value.first.return_value = household
        mock_member_filter.return_value.first.return_value = membership
        mock_debt_filter.return_value.exists.return_value = False

        response = view.destroy(make_request(user), pk=1)

    assert response.status_code == status.HTTP_200_OK
    assert household.is_active is False