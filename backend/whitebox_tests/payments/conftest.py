import pytest
from django.contrib.auth import get_user_model
from households.models import Household, HouseholdMember
from expenses.models import Expense, ExpenseParticipant, Debt
from payments.models import Payment, PaymentAllocation
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, force_authenticate

User = get_user_model()

@pytest.fixture
def owner(db):
    return User.objects.create_user(
        username="owner",
        email="owner@test.com",
        password="123456"
    )

@pytest.fixture
def member(db):
    return User.objects.create_user(
        username="member",
        email="member@test.com",
        password="123456"
    )

@pytest.fixture
def debtor(db):
    return User.objects.create_user(
        username="debtor",
        email="debtor@test.com",
        password="123456"
    )

@pytest.fixture
def virtual_user(db):
    user = User.objects.create_user(
        username="virtual",
        email="virtual@virtual.chungvi.local",
        password="123456"
    )
    user.is_virtual = True
    user.save()
    return user

@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="other",
        email="other@test.com",
        password="123456"
    )

@pytest.fixture
def household(db, owner, member, debtor, virtual_user):
    hh = Household.objects.create(
        name="Test Household",
        owner=owner
    )
    HouseholdMember.objects.create(household=hh, user=owner, role=HouseholdMember.Role.OWNER)
    HouseholdMember.objects.create(household=hh, user=member, role=HouseholdMember.Role.MEMBER)
    HouseholdMember.objects.create(household=hh, user=debtor, role=HouseholdMember.Role.MEMBER)
    HouseholdMember.objects.create(household=hh, user=virtual_user, role=HouseholdMember.Role.MEMBER)
    return hh

@pytest.fixture
def expense_instance(db, owner, household, debtor):
    expense = Expense.objects.create(
        household=household,
        title="Test Expense",
        amount=100000,
        payer=owner,
        split_type=Expense.SplitType.EQUAL,
    )
    ExpenseParticipant.objects.create(expense=expense, user=owner, share_amount=50000)
    ExpenseParticipant.objects.create(expense=expense, user=debtor, share_amount=50000)
    return expense

@pytest.fixture
def debt_instance(db, expense_instance, owner, debtor):
    # debtor owes owner 50000
    return Debt.objects.create(
        household=expense_instance.household,
        expense=expense_instance,
        from_user=debtor,
        to_user=owner,
        amount=50000,
        paid_amount=0,
        is_paid=False
    )

@pytest.fixture
def virtual_debt_instance(db, household, owner, virtual_user, expense_instance):
    # virtual_user owes owner 100000. Pointing to expense_instance to avoid IntegrityError (expense_id cannot be null)
    return Debt.objects.create(
        household=household,
        expense=expense_instance,
        from_user=virtual_user,
        to_user=owner,
        amount=100000,
        paid_amount=0,
        is_paid=False
    )
