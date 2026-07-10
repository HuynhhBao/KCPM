import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestST005HouseholdIsActive:
    
    def test_st_005_01_owner_destroy_no_debt(self, auth_client, test_household):
        """
        S1 (Active) -> E1 (Owner xóa nhóm khi không còn nợ) -> S2 (Inactive)
        """
        assert test_household.is_active is True
        
        url = f'/api/households/{test_household.id}/'
        response = auth_client.delete(url)
        assert response.status_code == 200
        
        test_household.refresh_from_db()
        assert test_household.is_active is False

    def test_st_005_02_last_member_leave(self, auth_client, test_household, active_user):
        """
        S1 (Active) -> E2 (Thành viên cuối tự rời nhóm) -> S2 (Inactive)
        """
        assert test_household.is_active is True
        
        url = f'/api/households/{test_household.id}/leave/'
        response = auth_client.post(url)
        assert response.status_code == 200
        
        test_household.refresh_from_db()
        assert test_household.is_active is False
