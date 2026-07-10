from types import SimpleNamespace
from unittest.mock import patch

from households.views import get_virtual_user_or_response
from rest_framework import status


def test_wb038_01_membership_not_found_returns_404():
    household = SimpleNamespace(id=1)

    with patch("households.views.HouseholdMember.objects.filter") as mock_filter:
        mock_filter.return_value.select_related.return_value.first.return_value = None

        user, response = get_virtual_user_or_response(
            household,
            virtual_user_id=1
        )

    assert user is None
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_wb038_02_user_is_not_virtual_returns_400():
    household = SimpleNamespace(id=1)
    normal_user = SimpleNamespace(
        id=1,
        email="normal@gmail.com",
        full_name="Normal User"
    )
    membership = SimpleNamespace(user=normal_user)

    with patch("households.views.HouseholdMember.objects.filter") as mock_filter:
        mock_filter.return_value.select_related.return_value.first.return_value = membership

        user, response = get_virtual_user_or_response(
            household,
            virtual_user_id=1
        )

    assert user is None
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_wb038_03_user_is_virtual_returns_user():
    household = SimpleNamespace(id=1)
    virtual_user = SimpleNamespace(
        id=1,
        email="virtual001@virtual.chungvi.local",
        full_name="Virtual User"
    )
    membership = SimpleNamespace(user=virtual_user)

    with patch("households.views.HouseholdMember.objects.filter") as mock_filter:
        mock_filter.return_value.select_related.return_value.first.return_value = membership

        user, response = get_virtual_user_or_response(
            household,
            virtual_user_id=1
        )

    assert user == virtual_user
    assert response is None