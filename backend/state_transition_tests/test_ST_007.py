import pytest
from django.contrib.auth import get_user_model
from households.models import HouseholdMember

User = get_user_model()

@pytest.mark.django_db
class TestST007HouseholdMemberRole:
    
    @pytest.fixture
    def test_member_user(self, db):
        return User.objects.create_user(
            email="member_st007@example.com",
            username="member_st007",
            password="testpassword123",
            is_active=True,
            email_verified=True
        )

    def test_st_007_01_add_member_default_role(self, auth_client, test_household, test_member_user):
        """
        Null -> E1 (Mặc định) -> MEMBER
        """
        # Delete any existing memberships for this user
        HouseholdMember.objects.filter(user=test_member_user).delete()
        
        url = f'/api/households/{test_household.id}/members/add/'
        data = {
            "email": test_member_user.email
            # No role specified
        }
        
        response = auth_client.post(url, data, format='json')
        assert response.status_code == 201
        
        member = HouseholdMember.objects.get(household=test_household, user=test_member_user)
        assert member.role == HouseholdMember.Role.MEMBER

    def test_st_007_02_add_member_owner_role(self, auth_client, test_household, test_member_user):
        """
        Null -> E2 (Chỉ định) -> OWNER
        """
        HouseholdMember.objects.filter(user=test_member_user).delete()
        
        url = f'/api/households/{test_household.id}/members/add/'
        data = {
            "email": test_member_user.email,
            "role": HouseholdMember.Role.OWNER
        }
        
        response = auth_client.post(url, data, format='json')
        assert response.status_code == 201
        
        member = HouseholdMember.objects.get(household=test_household, user=test_member_user)
        assert member.role == HouseholdMember.Role.OWNER
