from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.db import IntegrityError
from rest_framework import status

from households.views import AddHouseholdMemberView


pytestmark = pytest.mark.django_db


def make_request():
    return SimpleNamespace(
        user=SimpleNamespace(id=1, email="owner@gmail.com"),
        data={"email": "member@gmail.com", "role": "member"}
    )


def setup_serializer(mock_serializer):
    mock_serializer.return_value.is_valid.return_value = True
    mock_serializer.return_value.validated_data = {
        "email": "member@gmail.com",
        "role": "member"
    }


def test_wb041_01_household_not_found_returns_403():
    view = AddHouseholdMemberView()

    with patch("households.views.AddHouseholdMemberSerializer") as mock_serializer, \
         patch("households.views.Household.objects.select_for_update") as mock_household:

        setup_serializer(mock_serializer)
        mock_household.return_value.filter.return_value.first.return_value = None

        response = view.post(make_request(), household_id=1)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_wb041_02_not_owner_returns_403():
    view = AddHouseholdMemberView()
    household = SimpleNamespace(id=1)

    with patch("households.views.AddHouseholdMemberSerializer") as mock_serializer, \
         patch("households.views.Household.objects.select_for_update") as mock_household, \
         patch("households.views.HouseholdMember.objects.filter") as mock_member_filter:

        setup_serializer(mock_serializer)
        mock_household.return_value.filter.return_value.first.return_value = household
        mock_member_filter.return_value.first.return_value = None

        response = view.post(make_request(), household_id=1)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_wb041_03_user_email_not_found_returns_404():
    view = AddHouseholdMemberView()
    household = SimpleNamespace(id=1)
    owner_membership = SimpleNamespace(id=1)

    with patch("households.views.AddHouseholdMemberSerializer") as mock_serializer, \
         patch("households.views.Household.objects.select_for_update") as mock_household, \
         patch("households.views.HouseholdMember.objects.filter") as mock_member_filter, \
         patch("households.views.User.objects.filter") as mock_user_filter:

        setup_serializer(mock_serializer)
        mock_household.return_value.filter.return_value.first.return_value = household
        mock_member_filter.return_value.first.return_value = owner_membership
        mock_user_filter.return_value.first.return_value = None

        response = view.post(make_request(), household_id=1)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_wb041_04_user_already_member_returns_400():
    view = AddHouseholdMemberView()
    household = SimpleNamespace(id=1)
    owner_membership = SimpleNamespace(id=1)
    added_user = SimpleNamespace(id=2, email="member@gmail.com")

    owner_query = MagicMock()
    owner_query.first.return_value = owner_membership

    exists_query = MagicMock()
    exists_query.exists.return_value = True

    with patch("households.views.AddHouseholdMemberSerializer") as mock_serializer, \
         patch("households.views.Household.objects.select_for_update") as mock_household, \
         patch("households.views.HouseholdMember.objects.filter", side_effect=[owner_query, exists_query]), \
         patch("households.views.User.objects.filter") as mock_user_filter:

        setup_serializer(mock_serializer)
        mock_household.return_value.filter.return_value.first.return_value = household
        mock_user_filter.return_value.first.return_value = added_user

        response = view.post(make_request(), household_id=1)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_wb041_05_integrity_error_returns_400():
    view = AddHouseholdMemberView()
    household = SimpleNamespace(id=1)
    owner_membership = SimpleNamespace(id=1)
    added_user = SimpleNamespace(id=2, email="member@gmail.com")

    owner_query = MagicMock()
    owner_query.first.return_value = owner_membership

    exists_query = MagicMock()
    exists_query.exists.return_value = False

    with patch("households.views.AddHouseholdMemberSerializer") as mock_serializer, \
         patch("households.views.Household.objects.select_for_update") as mock_household, \
         patch("households.views.HouseholdMember.objects.filter", side_effect=[owner_query, exists_query]), \
         patch("households.views.User.objects.filter") as mock_user_filter, \
         patch("households.views.HouseholdMember.objects.create", side_effect=IntegrityError):

        setup_serializer(mock_serializer)
        mock_household.return_value.filter.return_value.first.return_value = household
        mock_user_filter.return_value.first.return_value = added_user

        response = view.post(make_request(), household_id=1)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_wb041_06_add_member_success_returns_201():
    view = AddHouseholdMemberView()
    household = SimpleNamespace(
        id=1,
        save=lambda update_fields=None: None,
        refresh_from_db=lambda: None
    )
    owner_membership = SimpleNamespace(id=1)
    added_user = SimpleNamespace(id=2, email="member@gmail.com")

    owner_query = MagicMock()
    owner_query.first.return_value = owner_membership

    exists_query = MagicMock()
    exists_query.exists.return_value = False

    with patch("households.views.AddHouseholdMemberSerializer") as mock_serializer, \
         patch("households.views.Household.objects.select_for_update") as mock_household, \
         patch("households.views.HouseholdMember.objects.filter", side_effect=[owner_query, exists_query]), \
         patch("households.views.User.objects.filter") as mock_user_filter, \
         patch("households.views.HouseholdMember.objects.create"), \
         patch("households.views.Activity.objects.create"), \
         patch("households.views.HouseholdSerializer") as mock_response_serializer:

        setup_serializer(mock_serializer)
        mock_household.return_value.filter.return_value.first.return_value = household
        mock_user_filter.return_value.first.return_value = added_user
        mock_response_serializer.return_value.data = {"id": 1}

        response = view.post(make_request(), household_id=1)

    assert response.status_code == status.HTTP_201_CREATED