# pyrefly: ignore [missing-import]
import pytest   
from unittest.mock import patch
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestWB005VerifyRegisterOTPView:
    def setup_method(self):
        from django.test import RequestFactory
        self.factory = RequestFactory()
        from accounts.views import VerifyRegisterOTPView
        self.view = VerifyRegisterOTPView.as_view()

    @patch('accounts.views.consume_cached_otp')
    def test_wb_005_branch_invalid_user_or_otp(self, mock_consume):
        mock_consume.return_value = False
        request = self.factory.post('/verify/', {'email': 'test@example.com', 'otp': '123456'})
        response = self.view(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch('accounts.views.consume_cached_otp')
    def test_wb_005_branch_success(self, mock_consume):
        mock_consume.return_value = True
        User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Password123!',
            email_verified=False,
            is_active=False
        )
        request = self.factory.post('/verify/', {'email': 'test@example.com', 'otp': '123456'})
        response = self.view(request)
        assert response.status_code == status.HTTP_200_OK
