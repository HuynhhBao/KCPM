import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestST004AuthProvider:
    
    @patch('accounts.views.get_google_identity')
    def test_st_004_01_auth_provider_email_to_google(self, mock_get_identity, api_client, active_user):
        """
        S1 ('email') -> E1 (Đăng nhập Google) -> S2 ('google')
        """
        assert active_user.auth_provider == 'email'
        
        mock_get_identity.return_value = {
            "email": active_user.email,
            "full_name": "Active Google User"
        }
        
        url = '/api/auth/google-login/'
        data = {"token": "fake_google_token"}
        
        response = api_client.post(url, data, format='json')
        assert response.status_code == 200
        
        active_user.refresh_from_db()
        assert active_user.auth_provider == 'google'
