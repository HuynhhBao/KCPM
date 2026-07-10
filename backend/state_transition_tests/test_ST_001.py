import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestST001EmailVerified:
    
    @patch('accounts.views.cache.get')
    @patch('accounts.views.cache.delete')
    def test_st_001_01_verify_otp_success(self, mock_cache_delete, mock_cache_get, api_client, test_user):
        """
        S1 (False) -> E1 (Xác thực OTP hợp lệ) -> S2 (True)
        """
        assert test_user.email_verified is False
        
        # Mock Redis cache to return "123456" for OTP and 1 for attempts
        def mock_cache_get_side_effect(key, default=None):
            if key == f"register_otp:{test_user.email}":
                return "123456"
            if key == f"register_otp_attempts:{test_user.email}":
                return 1
            return default
        mock_cache_get.side_effect = mock_cache_get_side_effect
        
        url = '/api/auth/verify-register-otp/'
        data = {
            "email": test_user.email,
            "otp": "123456"
        }
        
        response = api_client.post(url, data, format='json')
        assert response.status_code == 200
        
        test_user.refresh_from_db()
        assert test_user.email_verified is True
        assert test_user.is_active is True

    @patch('accounts.views.get_google_identity')
    def test_st_001_02_google_login_from_unverified(self, mock_get_identity, api_client, test_user):
        """
        S1 (False) -> E2 (Đăng nhập Google) -> S2 (True)
        """
        assert test_user.email_verified is False
        test_user.is_active = True
        test_user.save()
        
        mock_get_identity.return_value = {
            "email": test_user.email,
            "full_name": "Google User"
        }
        
        url = '/api/auth/google-login/'
        data = {"token": "fake_google_token"}
        
        response = api_client.post(url, data, format='json')
        assert response.status_code == 200
        
        test_user.refresh_from_db()
        assert test_user.email_verified is True

    @patch('accounts.views.get_google_identity')
    def test_st_001_03_google_login_from_verified(self, mock_get_identity, api_client, active_user):
        """
        S2 (True) -> E2 (Đăng nhập Google) -> S2 (True)
        """
        assert active_user.email_verified is True
        
        mock_get_identity.return_value = {
            "email": active_user.email,
            "full_name": "Active Google User"
        }
        
        url = '/api/auth/google-login/'
        data = {"token": "fake_google_token"}
        
        response = api_client.post(url, data, format='json')
        assert response.status_code == 200
        
        active_user.refresh_from_db()
        assert active_user.email_verified is True
