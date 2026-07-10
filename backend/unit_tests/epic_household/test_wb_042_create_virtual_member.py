from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status

from households.views import CreateVirtualHouseholdMemberView


pytestmark = pytest.mark.django_db


def make_request():
    return SimpleNamespace(
        user=SimpleNamespace(id=1, email="owner@gmail.com", full_name="Owner"),
        data={"display_name": "Bạn ảo", "note": ""}
    )


def setup_serializer(mock_serializer):
    mock_serializer.return_value.is_valid.return_value = True
    mock_serializer.return_value.validated_data = {
        "display_name": "Bạn ảo",
        "note": ""
    }


def test_wb042_01_household_not_found_returns_404():
    view = CreateVirtualHouseholdMemberView()

    with patch("households.views.CreateVirtualMemberSerializer") as mock_serializer, \
         patch("households.views.Household.objects.select_for_update") as mock_household:

        setup_serializer(mock_serializer)
        mock_household.return_value.filter.return_value.first.return_value = None

        response = view.post(make_request(), household_id=1)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_wb042_02_not_owner_returns_403():
    view = CreateVirtualHouseholdMemberView()
    household = SimpleNamespace(id=1)

    with patch("households.views.CreateVirtualMemberSerializer") as mock_serializer, \
         patch("households.views.Household.objects.select_for_update") as mock_household, \
         patch("households.views.HouseholdMember.objects.filter") as mock_member_filter:

        setup_serializer(mock_serializer)
        mock_household.return_value.filter.return_value.first.return_value = household
        mock_member_filter.return_value.first.return_value = None

        response = view.post(make_request(), household_id=1)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_wb042_03_duplicate_virtual_name_returns_400():
    view = CreateVirtualHouseholdMemberView()
    household = SimpleNamespace(id=1)

    owner_query = MagicMock()
    owner_query.first.return_value = SimpleNamespace(id=1)

    exists_name_query = MagicMock()
    exists_name_query.exists.return_value = True

    with patch("households.views.CreateVirtualMemberSerializer") as mock_serializer, \
         patch("households.views.Household.objects.select_for_update") as mock_household, \
         patch("households.views.HouseholdMember.objects.filter", side_effect=[owner_query, exists_name_query]):

        setup_serializer(mock_serializer)
        mock_household.return_value.filter.return_value.first.return_value = household

        response = view.post(make_request(), household_id=1)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_wb042_04_create_virtual_success_returns_201():
    view = CreateVirtualHouseholdMemberView()
    household_id = SimpleNamespace(hex="abcdef123456")
    household = SimpleNamespace(
        id=household_id,
        save=lambda update_fields=None: None,
        refresh_from_db=lambda: None
    )

    owner_query = MagicMock()
    owner_query.first.return_value = SimpleNamespace(id=1)

    exists_name_query = MagicMock()
    exists_name_query.exists.return_value = False

    email_query = MagicMock()
    email_query.exists.return_value = False

    username_query = MagicMock()
    username_query.exists.return_value = False

    virtual_user = SimpleNamespace(
        id=2,
        email="virtual@virtual.chungvi.local",
        full_name="Bạn ảo",
        set_unusable_password=lambda: None,
        save=lambda: None
    )

    with patch("households.views.CreateVirtualMemberSerializer") as mock_serializer, \
         patch("households.views.Household.objects.select_for_update") as mock_household, \
         patch("households.views.HouseholdMember.objects.filter", side_effect=[owner_query, exists_name_query]), \
         patch("households.views.User.objects.filter", side_effect=[email_query, username_query]), \
         patch("households.views.User.objects.create", return_value=virtual_user), \
         patch("households.views.HouseholdMember.objects.create"), \
         patch("households.views.Activity.objects.create"), \
         patch("households.views.HouseholdSerializer") as mock_response_serializer:

        setup_serializer(mock_serializer)
        mock_household.return_value.filter.return_value.first.return_value = household
        mock_response_serializer.return_value.data = {"id": 1}

        response = view.post(make_request(), household_id=1)

    assert response.status_code == status.HTTP_201_CREATED