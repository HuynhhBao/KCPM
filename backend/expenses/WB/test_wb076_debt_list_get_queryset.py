import pytest

from expenses.models import Debt
from expenses.views import DebtListView

from expenses.WB.conftest import make_drf_request


# ─────────────────────────────────────────────
# TC_WB076_01
# ─────────────────────────────────────────────
@pytest.mark.django_db
def test_get_queryset_not_member_returns_empty(household, outsider_user):
    view = DebtListView()
    view.kwargs = {'household_id': household.id}
    view.request = make_drf_request(user=outsider_user)

    queryset = view.get_queryset()

    assert queryset.count() == 0


# ─────────────────────────────────────────────
# TC_WB076_02
# ─────────────────────────────────────────────
@pytest.mark.django_db
def test_get_queryset_member_as_from_user_returns_debt(
    user, member2, household, expense_instance
):
    debt = Debt.objects.create(
        household=household,
        expense=expense_instance,
        from_user=user,
        to_user=member2,
        amount=100000,
        is_paid=False,
    )

    view = DebtListView()
    view.kwargs = {'household_id': household.id}
    view.request = make_drf_request(user=user)

    queryset = view.get_queryset()

    assert list(queryset.values_list('id', flat=True)) == [debt.id]


# ─────────────────────────────────────────────
# TC_WB076_03
# ─────────────────────────────────────────────
@pytest.mark.django_db
def test_get_queryset_member_as_to_user_returns_debt(
    user, member2, household, expense_instance
):
    debt = Debt.objects.create(
        household=household,
        expense=expense_instance,
        from_user=member2,
        to_user=user,
        amount=100000,
        is_paid=False,
    )

    Debt.objects.create(
        household=household,
        expense=expense_instance,
        from_user=member2,
        to_user=user,
        amount=50000,
        is_paid=True,
    )

    view = DebtListView()
    view.kwargs = {'household_id': household.id}
    view.request = make_drf_request(user=user)

    queryset = view.get_queryset()

    assert list(queryset.values_list('id', flat=True)) == [debt.id]