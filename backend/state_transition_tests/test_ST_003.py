import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestST003Password:
    
    def test_st_003_01_change_password_success(self, auth_client, active_user):
        """
        S1 (Mật khẩu cũ) -> E1 (Đổi mật khẩu với old_password đúng) -> S2 (Mật khẩu mới)
        """
        url = '/api/auth/change-password/'
        data = {
            "old_password": "testpassword123",
            "new_password": "Newpassword456",
            "confirm_password": "Newpassword456"
        }
        
        response = auth_client.post(url, data, format='json')
        assert response.status_code == 200
        
        active_user.refresh_from_db()
        assert active_user.check_password("Newpassword456") is True
        assert active_user.check_password("testpassword123") is False

    @patch('accounts.views.cache.get')
    @patch('accounts.views.cache.delete')
    def test_st_003_02_reset_password_success(self, mock_cache_delete, mock_cache_get, api_client, active_user):
        """
        S1 (Mật khẩu cũ) -> E2 (Đặt lại mật khẩu với OTP hợp lệ) -> S2 (Mật khẩu mới)
        """
        def mock_cache_get_side_effect(key, default=None):
            if key == f"forgot_password_otp:{active_user.email}":
                return "654321"
            if key == f"forgot_password_otp_attempts:{active_user.email}":
                return 1
            return default
        mock_cache_get.side_effect = mock_cache_get_side_effect
        
        url = '/api/auth/reset-password/'
        data = {
            "email": active_user.email,
            "otp": "654321",
            "new_password": "Resetpassword789",
            "confirm_password": "Resetpassword789"
        }
        
        response = api_client.post(url, data, format='json')
        assert response.status_code == 200
        
        active_user.refresh_from_db()
        assert active_user.check_password("Resetpassword789") is True

    def test_st_003_03_change_password_fail_wrong_old(self, auth_client, active_user):
        """
        S1 (Mật khẩu cũ) -> E3 (Đổi mật khẩu sai old_password) -> S1 (Mật khẩu cũ)
        """
        url = '/api/auth/change-password/'
        data = {
            "old_password": "wrongpassword",
            "new_password": "Newpassword456",
            "confirm_password": "Newpassword456"
        }
        
        response = auth_client.post(url, data, format='json')
        assert response.status_code == 400
        
        active_user.refresh_from_db()
        assert active_user.check_password("testpassword123") is True
