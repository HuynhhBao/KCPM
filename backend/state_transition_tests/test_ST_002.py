import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestST002IsActive:
    
    @patch('accounts.views.send_register_otp')
    def test_st_002_01_register_email(self, mock_send_otp, api_client):
        """
        Null -> E1 (Đăng ký tài khoản qua email) -> S1 (False)
        """
        url = '/api/auth/register/'
        data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "full_name": "New User",
            "password": "Newpassword456"
        }
        
        response = api_client.post(url, data, format='json')
        assert response.status_code == 201
        
        user = User.objects.get(email="newuser@example.com")
        assert user.is_active is False

    @patch('accounts.views.get_google_identity')
    def test_st_002_02_google_login_new_user(self, mock_get_identity, api_client):
        """
        Null -> E2 (Đăng nhập Google lần đầu) -> S2 (True)
        """
        email = "googleuser@example.com"
        
        mock_get_identity.return_value = {
            "email": email,
            "full_name": "Google User"
        }
        
        url = '/api/auth/google-login/'
        data = {"token": "fake_google_token"}
        
        response = api_client.post(url, data, format='json')
        assert response.status_code == 200
        
        user = User.objects.get(email=email)
        assert user.is_active is True

    @patch('accounts.views.cache.get')
    @patch('accounts.views.cache.delete')
    def test_st_002_03_verify_otp(self, mock_cache_delete, mock_cache_get, api_client, test_user):
        """
        S1 (False) -> E3 (Xác thực OTP thành công) -> S2 (True)
        """
        assert test_user.is_active is False
        
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
        assert test_user.is_active is True
