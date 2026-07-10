from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status

from households.models import HouseholdMember
from households.views import LeaveHouseholdView


pytestmark = pytest.mark.django_db


def make_request():
    return SimpleNamespace(
        user=SimpleNamespace(id=1, email="user@gmail.com")
    )


def test_wb044_01_household_not_found_returns_404():
    view = LeaveHouseholdView()

    with patch("households.views.Household.objects.select_for_update") as mock_household:
        mock_household.return_value.filter.return_value.first.return_value = None

        response = view.post(make_request(), household_id=1)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_wb044_02_membership_not_found_returns_404():
    view = LeaveHouseholdView()
    household = SimpleNamespace(id=1)

    with patch("households.views.Household.objects.select_for_update") as mock_household, \
         patch("households.views.HouseholdMember.objects.select_for_update") as mock_member:

        mock_household.return_value.filter.return_value.first.return_value = household
        mock_member.return_value.filter.return_value.first.return_value = None

        response = view.post(make_request(), household_id=1)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_wb044_03_owner_leave_when_group_has_other_members_returns_400():
    view = LeaveHouseholdView()
    household = SimpleNamespace(id=1)
    membership = SimpleNamespace(role=HouseholdMember.Role.OWNER)

    with patch("households.views.Household.objects.select_for_update") as mock_household, \
         patch("households.views.HouseholdMember.objects.select_for_update") as mock_member, \
         patch("households.views.HouseholdMember.objects.filter") as mock_count_filter:

        mock_household.return_value.filter.return_value.first.return_value = household
        mock_member.return_value.filter.return_value.first.return_value = membership
        mock_count_filter.return_value.count.return_value = 2

        response = view.post(make_request(), household_id=1)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_wb044_04_has_unpaid_debt_returns_400():
    view = LeaveHouseholdView()
    household = SimpleNamespace(id=1)
    membership = SimpleNamespace(role=HouseholdMember.Role.MEMBER)

    debt_query = MagicMock()
    debt_query.filter.return_value.exists.return_value = True

    with patch("households.views.Household.objects.select_for_update") as mock_household, \
         patch("households.views.HouseholdMember.objects.select_for_update") as mock_member, \
         patch("households.views.HouseholdMember.objects.filter") as mock_count_filter, \
         patch("households.views.Debt.objects.filter", return_value=debt_query):

        mock_household.return_value.filter.return_value.first.return_value = household
        mock_member.return_value.filter.return_value.first.return_value = membership
        mock_count_filter.return_value.count.return_value = 2

        response = view.post(make_request(), household_id=1)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_wb044_05_last_member_leave_sets_household_inactive_returns_200():
    view = LeaveHouseholdView()
    household = SimpleNamespace(
        id=1,
        is_active=True,
        save=lambda update_fields=None: None
    )
    membership = SimpleNamespace(
        role=HouseholdMember.Role.MEMBER,
        delete=lambda: None
    )

    debt_query = MagicMock()
    debt_query.filter.return_value.exists.return_value = False

    with patch("households.views.Household.objects.select_for_update") as mock_household, \
         patch("households.views.HouseholdMember.objects.select_for_update") as mock_member, \
         patch("households.views.HouseholdMember.objects.filter") as mock_count_filter, \
         patch("households.views.Debt.objects.filter", return_value=debt_query), \
         patch("households.views.Activity.objects.create"):

        mock_household.return_value.filter.return_value.first.return_value = household
        mock_member.return_value.filter.return_value.first.return_value = membership
        mock_count_filter.return_value.count.return_value = 1

        response = view.post(make_request(), household_id=1)

    assert response.status_code == status.HTTP_200_OK
    assert household.is_active is False