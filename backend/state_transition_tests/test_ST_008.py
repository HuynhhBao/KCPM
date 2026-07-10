import pytest
from django.contrib.auth import get_user_model
from households.models import HouseholdMember

User = get_user_model()

@pytest.mark.django_db
class TestST008HouseholdMemberExistence:
    
    @pytest.fixture
    def test_member_user(self, db):
        return User.objects.create_user(
            email="member_st008@example.com",
            username="member_st008",
            password="testpassword123",
            is_active=True,
            email_verified=True
        )

    @pytest.fixture
    def household_member(self, test_household, test_member_user):
        return HouseholdMember.objects.create(
            household=test_household,
            user=test_member_user,
            role=HouseholdMember.Role.MEMBER
        )

    def test_st_008_01_owner_kick_member(self, auth_client, test_household, household_member, test_member_user):
        """
        S1 (Tồn tại / Active) -> E1 (Owner kick thành viên không nợ) -> S2 (Deleted)
        """
        assert HouseholdMember.objects.filter(household=test_household, user=test_member_user).exists() is True
        
        url = f'/api/households/{test_household.id}/members/{household_member.id}/kick/'
        response = auth_client.delete(url)
        assert response.status_code == 200
        
        assert HouseholdMember.objects.filter(household=test_household, user=test_member_user).exists() is False

    def test_st_008_02_member_leaves(self, api_client, test_household, household_member, test_member_user):
        """
        S1 (Tồn tại / Active) -> E2 (Thành viên không nợ tự rời nhóm) -> S2 (Deleted)
        """
        # Authenticate as the normal member
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(test_member_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        assert HouseholdMember.objects.filter(household=test_household, user=test_member_user).exists() is True
        
        url = f'/api/households/{test_household.id}/leave/'
        response = api_client.post(url)
        assert response.status_code == 200
        
        assert HouseholdMember.objects.filter(household=test_household, user=test_member_user).exists() is False
