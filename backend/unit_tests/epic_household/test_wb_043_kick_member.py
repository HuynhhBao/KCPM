from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status

from households.models import HouseholdMember
from households.views import KickHouseholdMemberView


pytestmark = pytest.mark.django_db


def make_request(user_id=1):
    return SimpleNamespace(
        user=SimpleNamespace(id=user_id, email="owner@gmail.com", full_name="Owner")
    )


def test_wb043_01_household_not_found_returns_404():
    view = KickHouseholdMemberView()

    with patch("households.views.Household.objects.select_for_update") as mock_household:
        mock_household.return_value.filter.return_value.first.return_value = None

        response = view.delete(make_request(), household_id=1, member_id=2)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_wb043_02_not_owner_returns_403():
    view = KickHouseholdMemberView()
    household = SimpleNamespace(id=1)

    with patch("households.views.Household.objects.select_for_update") as mock_household, \
         patch("households.views.HouseholdMember.objects.filter") as mock_member_filter:

        mock_household.return_value.filter.return_value.first.return_value = household
        mock_member_filter.return_value.first.return_value = None

        response = view.delete(make_request(), household_id=1, member_id=2)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_wb043_03_target_member_not_found_returns_404():
    view = KickHouseholdMemberView()
    household = SimpleNamespace(id=1)

    owner_query = MagicMock()
    owner_query.first.return_value = SimpleNamespace(id=1)

    target_query = MagicMock()
    target_query.select_related.return_value.filter.return_value.first.return_value = None

    with patch("households.views.Household.objects.select_for_update") as mock_household, \
         patch("households.views.HouseholdMember.objects.filter", return_value=owner_query), \
         patch("households.views.HouseholdMember.objects.select_for_update", return_value=target_query):

        mock_household.return_value.filter.return_value.first.return_value = household

        response = view.delete(make_request(), household_id=1, member_id=2)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_wb043_04_target_is_self_returns_400():
    view = KickHouseholdMemberView()
    household = SimpleNamespace(id=1)
    target = SimpleNamespace(user_id=1, role=HouseholdMember.Role.MEMBER)

    owner_query = MagicMock()
    owner_query.first.return_value = SimpleNamespace(id=1)

    target_query = MagicMock()
    target_query.select_related.return_value.filter.return_value.first.return_value = target

    with patch("households.views.Household.objects.select_for_update") as mock_household, \
         patch("households.views.HouseholdMember.objects.filter", return_value=owner_query), \
         patch("households.views.HouseholdMember.objects.select_for_update", return_value=target_query):

        mock_household.return_value.filter.return_value.first.return_value = household

        response = view.delete(make_request(user_id=1), household_id=1, member_id=2)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_wb043_05_target_is_owner_returns_400():
    view = KickHouseholdMemberView()
    household = SimpleNamespace(id=1)
    target = SimpleNamespace(user_id=2, role=HouseholdMember.Role.OWNER)

    owner_query = MagicMock()
    owner_query.first.return_value = SimpleNamespace(id=1)

    target_query = MagicMock()
    target_query.select_related.return_value.filter.return_value.first.return_value = target

    with patch("households.views.Household.objects.select_for_update") as mock_household, \
         patch("households.views.HouseholdMember.objects.filter", return_value=owner_query), \
         patch("households.views.HouseholdMember.objects.select_for_update", return_value=target_query):

        mock_household.return_value.filter.return_value.first.return_value = household

        response = view.delete(make_request(user_id=1), household_id=1, member_id=2)

    assert response.status_code == status.HTTP_400_BAD_REQUEST