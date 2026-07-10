from types import SimpleNamespace
from unittest.mock import patch

import pytest
from rest_framework import status

from households.views import MyDebtSummaryView


pytestmark = pytest.mark.django_db


def make_request():
    return SimpleNamespace(
        user=SimpleNamespace(id=1, email="me@gmail.com", full_name="Me")
    )


def test_wb045_01_household_not_found_returns_404():
    view = MyDebtSummaryView()

    with patch("households.views.Household.objects.filter") as mock_household:
        mock_household.return_value.first.return_value = None

        response = view.get(make_request(), household_id=1)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_wb045_02_summary_rows_classify_i_owe_and_owed_to_me():
    view = MyDebtSummaryView()
    household = SimpleNamespace(id=1)

    other_user_2 = SimpleNamespace(
        id=2,
        email="a@gmail.com",
        full_name="A"
    )
    other_user_3 = SimpleNamespace(
        id=3,
        email="b@gmail.com",
        full_name="B"
    )

    rows = [
        {
            "other_user_id": 2,
            "subject_owes_amount": 100000,
            "owed_to_subject_amount": 30000,
            "expense_count": 2,
        },
        {
            "other_user_id": 3,
            "subject_owes_amount": 10000,
            "owed_to_subject_amount": 50000,
            "expense_count": 1,
        },
        {
            "other_user_id": 4,
            "subject_owes_amount": 10000,
            "owed_to_subject_amount": 10000,
            "expense_count": 1,
        },
    ]

    users_by_id = {
        2: other_user_2,
        3: other_user_3,
    }

    with patch("households.views.Household.objects.filter") as mock_household, \
         patch("households.views.get_debt_summary_rows", return_value=(rows, users_by_id)):

        mock_household.return_value.first.return_value = household

        response = view.get(make_request(), household_id=1)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["total_i_owe"] == 70000
    assert response.data["total_owed_to_me"] == 40000
    assert len(response.data["i_owe"]) == 1
    assert len(response.data["owed_to_me"]) == 1