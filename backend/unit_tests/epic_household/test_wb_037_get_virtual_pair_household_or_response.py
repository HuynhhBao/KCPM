from types import SimpleNamespace
from unittest.mock import patch

from households.views import get_virtual_pair_household_or_response
from rest_framework import status


def test_wb037_01_household_not_found_returns_404():
    request = SimpleNamespace(user=SimpleNamespace(id=1))

    with patch("households.views.Household.objects.filter") as mock_filter:
        mock_filter.return_value.distinct.return_value.first.return_value = None

        household, response = get_virtual_pair_household_or_response(
            request,
            household_id=1,
            other_user_id=2
        )

    assert household is None
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_wb037_02_not_owner_and_not_involved_returns_403():
    request = SimpleNamespace(user=SimpleNamespace(id=1))
    fake_household = SimpleNamespace(id=1)

    with patch("households.views.Household.objects.filter") as mock_household_filter, \
         patch("households.views.HouseholdMember.objects.filter") as mock_member_filter:

        mock_household_filter.return_value.distinct.return_value.first.return_value = fake_household
        mock_member_filter.return_value.exists.return_value = False

        household, response = get_virtual_pair_household_or_response(
            request,
            household_id=1,
            other_user_id=2
        )

    assert household is None
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_wb037_03_owner_can_view_returns_household():
    request = SimpleNamespace(user=SimpleNamespace(id=1))
    fake_household = SimpleNamespace(id=1)

    with patch("households.views.Household.objects.filter") as mock_household_filter, \
         patch("households.views.HouseholdMember.objects.filter") as mock_member_filter:

        mock_household_filter.return_value.distinct.return_value.first.return_value = fake_household
        mock_member_filter.return_value.exists.return_value = True

        household, response = get_virtual_pair_household_or_response(
            request,
            household_id=1,
            other_user_id=2
        )

    assert household == fake_household
    assert response is None


def test_wb037_04_involved_user_can_view_returns_household():
    request = SimpleNamespace(user=SimpleNamespace(id=2))
    fake_household = SimpleNamespace(id=1)

    with patch("households.views.Household.objects.filter") as mock_household_filter, \
         patch("households.views.HouseholdMember.objects.filter") as mock_member_filter:

        mock_household_filter.return_value.distinct.return_value.first.return_value = fake_household
        mock_member_filter.return_value.exists.return_value = False

        household, response = get_virtual_pair_household_or_response(
            request,
            household_id=1,
            other_user_id=2
        )

    assert household == fake_household
    assert response is None