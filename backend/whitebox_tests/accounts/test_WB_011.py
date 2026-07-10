# pyrefly: ignore [missing-import]
import pytest
from unittest.mock import patch
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestWB011ForgotPasswordRequestView:
    def setup_method(self):
        from django.test import RequestFactory
        self.factory = RequestFactory()
        from accounts.views import ForgotPasswordRequestView
        self.view = ForgotPasswordRequestView.as_view()

    @patch('accounts.views.cache.get')
    def test_wb_011_branch_cooldown(self, mock_get):
        mock_get.return_value = True
        request = self.factory.post('/forgot/', {'email': 'test@example.com'})
        response = self.view(request)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @patch('accounts.views.cache.get')
    @patch('accounts.views.send_mail')
    def test_wb_011_branch_success(self, mock_mail, mock_get):
        mock_get.return_value = False
        User.objects.create_user(username='test', email='test@example.com', password='pwd')
        request = self.factory.post('/forgot/', {'email': 'test@example.com'})
        response = self.view(request)
        assert response.status_code == status.HTTP_200_OK
        mock_mail.assert_called_once()
