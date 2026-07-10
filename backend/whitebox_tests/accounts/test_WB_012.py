# pyrefly: ignore [missing-import]
import pytest
from unittest.mock import patch
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestWB012ResetPasswordView:
    def setup_method(self):
        from rest_framework.test import APIRequestFactory
        self.factory = APIRequestFactory()
        from accounts.views import ResetPasswordView
        self.view = ResetPasswordView.as_view()

    @patch('accounts.views.consume_cached_otp')
    def test_wb_012_branch_expired(self, mock_consume):
        mock_consume.return_value = False
        request = self.factory.post('/reset/', {'email': 'test@example.com', 'otp': '123456', 'new_password': 'NewPassword1!', 'confirm_password': 'NewPassword1!'}, format='json')
        response = self.view(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch('accounts.views.consume_cached_otp')
    def test_wb_012_branch_incorrect(self, mock_consume):
        mock_consume.return_value = False
        request = self.factory.post('/reset/', {'email': 'test@example.com', 'otp': '123456', 'new_password': 'NewPassword1!', 'confirm_password': 'NewPassword1!'}, format='json')
        response = self.view(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch('accounts.views.consume_cached_otp')
    def test_wb_012_branch_success(self, mock_consume):
        mock_consume.return_value = True
        User.objects.create_user(username='test', email='test@example.com', password='pwd')
        request = self.factory.post('/reset/', {'email': 'test@example.com', 'otp': '123456', 'new_password': 'NewPassword1!', 'confirm_password': 'NewPassword1!'}, format='json')
        response = self.view(request)
        assert response.status_code == status.HTTP_200_OK
