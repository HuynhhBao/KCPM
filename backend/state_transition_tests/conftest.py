import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def test_user(db):
    user = User.objects.create_user(
        email="testuser@example.com",
        username="testuser",
        password="testpassword123",
        full_name="Test User",
        email_verified=False,
        is_active=False
    )
    return user

@pytest.fixture
def active_user(db):
    user = User.objects.create_user(
        email="activeuser@example.com",
        username="activeuser",
        password="testpassword123",
        full_name="Active User",
        email_verified=True,
        is_active=True
    )
    return user

@pytest.fixture
def auth_client(api_client, active_user):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(active_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client

@pytest.fixture
def test_household(db, active_user):
    from households.models import Household, HouseholdMember
    household = Household.objects.create(
        name="Test Household",
        owner=active_user
    )
    HouseholdMember.objects.create(
        household=household,
        user=active_user,
        role=HouseholdMember.Role.OWNER
    )
    return household
