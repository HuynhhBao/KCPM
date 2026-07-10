from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.db import IntegrityError
from rest_framework import status

from households.views import JoinHouseholdView


pytestmark = pytest.mark.django_db


def make_request():
    return SimpleNamespace(
        user=SimpleNamespace(id=1, email="user@gmail.com"),
        data={"invite_code": "ABC123"}
    )


def setup_serializer(mock_serializer):
    mock_serializer.return_value.is_valid.return_value = True
    mock_serializer.return_value.validated_data = {
        "invite_code": "ABC123"
    }


def test_wb040_01_invite_code_invalid_returns_404():
    view = JoinHouseholdView()

    with patch("households.views.JoinHouseholdSerializer") as mock_serializer, \
         patch("households.views.Household.objects.select_for_update") as mock_household:

        setup_serializer(mock_serializer)
        mock_household.return_value.filter.return_value.first.return_value = None

        response = view.post(make_request())

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_wb040_02_user_already_member_returns_400():
    view = JoinHouseholdView()
    household = SimpleNamespace(id=1)

    with patch("households.views.JoinHouseholdSerializer") as mock_serializer, \
         patch("households.views.Household.objects.select_for_update") as mock_household, \
         patch("households.views.HouseholdMember.objects.filter") as mock_member_filter:

        setup_serializer(mock_serializer)
        mock_household.return_value.filter.return_value.first.return_value = household
        mock_member_filter.return_value.exists.return_value = True

        response = view.post(make_request())

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_wb040_03_integrity_error_returns_400():
    view = JoinHouseholdView()
    household = SimpleNamespace(id=1)

    with patch("households.views.JoinHouseholdSerializer") as mock_serializer, \
         patch("households.views.Household.objects.select_for_update") as mock_household, \
         patch("households.views.HouseholdMember.objects.filter") as mock_member_filter, \
         patch("households.views.HouseholdMember.objects.create", side_effect=IntegrityError):

        setup_serializer(mock_serializer)
        mock_household.return_value.filter.return_value.first.return_value = household
        mock_member_filter.return_value.exists.return_value = False

        response = view.post(make_request())

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_wb040_04_join_success_returns_200():
    view = JoinHouseholdView()
    household = SimpleNamespace(
        id=1,
        refresh_from_db=lambda: None
    )

    with patch("households.views.JoinHouseholdSerializer") as mock_serializer, \
         patch("households.views.Household.objects.select_for_update") as mock_household, \
         patch("households.views.HouseholdMember.objects.filter") as mock_member_filter, \
         patch("households.views.HouseholdMember.objects.create"), \
         patch("households.views.Activity.objects.create"), \
         patch("households.views.HouseholdSerializer") as mock_response_serializer:

        setup_serializer(mock_serializer)
        mock_household.return_value.filter.return_value.first.return_value = household
        mock_member_filter.return_value.exists.return_value = False
        mock_response_serializer.return_value.data = {"id": 1}

        response = view.post(make_request())

    assert response.status_code == status.HTTP_200_OK