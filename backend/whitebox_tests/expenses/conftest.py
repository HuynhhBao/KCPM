import pytest
from django.contrib.auth import get_user_model

from households.models import Household, HouseholdMember
from expenses.models import Expense, ExpenseParticipant, Debt

from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, force_authenticate

User = get_user_model()


# =========================================================
# USERS
# =========================================================

@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="user1",
        email="user1@test.com",
        password="123456"
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="user2",
        email="user2@test.com",
        password="123456"
    )


@pytest.fixture
def member2(db):
    return User.objects.create_user(
        username="member2",
        email="member2@test.com",
        password="123456"
    )


@pytest.fixture
def member3(db):
    return User.objects.create_user(
        username="member3",
        email="member3@test.com",
        password="123456"
    )


@pytest.fixture
def outsider_user(db):
    return User.objects.create_user(
        username="outsider",
        email="outsider@test.com",
        password="123456"
    )


# =========================================================
# VIRTUAL USER (FIX: phải save DB field)
# =========================================================

@pytest.fixture
def virtual_user(db):
    user = User.objects.create_user(
        username="virtual",
        email="virtual@test.com",
        password="123456"
    )
    user.is_virtual = True
    user.save()   # ✅ FIX QUAN TRỌNG
    return user


# =========================================================
# HOUSEHOLD
# =========================================================

@pytest.fixture
def household(db, user, member2):
    household = Household.objects.create(
        name="Test Household",
        owner=user
    )

    HouseholdMember.objects.create(household=household, user=user)
    HouseholdMember.objects.create(household=household, user=member2)

    return household


# =========================================================
# EXPENSE
# =========================================================

@pytest.fixture
def expense_instance(db, user, household, member2):
    expense = Expense.objects.create(
        household=household,
        title="Test Expense",
        amount=100000,
        payer=user,
        split_type=Expense.SplitType.EQUAL,
    )

    ExpenseParticipant.objects.create(expense=expense, user=user, share_amount=50000)
    ExpenseParticipant.objects.create(expense=expense, user=member2, share_amount=50000)

    return expense


@pytest.fixture
def expense_instance_with_participants(expense_instance):
    return expense_instance


# =========================================================
# VIRTUAL PAYER EXPENSE
# =========================================================

@pytest.fixture
def expense_instance_virtual_payer(db, household, virtual_user, member2):
    expense = Expense.objects.create(
        household=household,
        title="Virtual Expense",
        amount=100000,
        payer=virtual_user,
        split_type=Expense.SplitType.EQUAL,
    )

    ExpenseParticipant.objects.create(
        expense=expense,
        user=virtual_user,
        share_amount=50000
    )

    ExpenseParticipant.objects.create(
        expense=expense,
        user=member2,
        share_amount=50000
    )

    return expense


# =========================================================
# DEBT
# =========================================================

@pytest.fixture
def debt_instance(db, expense_instance, user, member2):
    return Debt.objects.create(
        household=expense_instance.household,
        expense=expense_instance,
        from_user=user,
        to_user=member2,
        amount=100000,
    )


@pytest.fixture
def paid_debt(db, expense_instance, user, member2):
    return Debt.objects.create(
        household=expense_instance.household,
        expense=expense_instance,
        from_user=user,
        to_user=member2,
        amount=100000,
        paid_amount=100000,
        is_paid=True
    )


@pytest.fixture
def pending_payment_debt(db, expense_instance, user, member2):
    return Debt.objects.create(
        household=expense_instance.household,
        expense=expense_instance,
        from_user=user,
        to_user=member2,
        amount=100000,
        paid_amount=50000,
        is_paid=False
    )


# =========================================================
# DRF REQUEST (FIX ANONYMOUS BUG)
# =========================================================

def make_drf_request(user=None, method="get"):
    factory = APIRequestFactory()
    django_request = getattr(factory, method)("/")
    request = Request(django_request)

    if user is not None:
        # force_authenticate gán user vào đúng chỗ DRF đọc,
        # tránh việc request.user tự chạy lại authentication
        # và trả về AnonymousUser.
        force_authenticate(request, user=user)
        request.user = user
    else:
        request.user = User()

    return request