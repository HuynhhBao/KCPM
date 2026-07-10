# pyrefly: ignore [missing-import]
import pytest
from unittest.mock import patch
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestWB006ResendRegisterOTPView:
    def setup_method(self):
        from django.test import RequestFactory
        self.factory = RequestFactory()
        from accounts.views import ResendRegisterOTPView
        self.view = ResendRegisterOTPView.as_view()

    @patch('accounts.views.cache.get')
    def test_wb_006_branch_cooldown(self, mock_cache_get):
        mock_cache_get.return_value = True
        request = self.factory.post('/resend/', {'email': 'test@example.com'})
        response = self.view(request)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @patch('accounts.views.cache.get')
    @patch('accounts.views.send_register_otp')
    def test_wb_006_branch_success(self, mock_send_otp, mock_cache_get):
        mock_cache_get.return_value = False
        User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Password123!',
            email_verified=False
        )
        request = self.factory.post('/resend/', {'email': 'test@example.com'})
        response = self.view(request)
        assert response.status_code == status.HTTP_200_OK
        mock_send_otp.assert_called_once()
