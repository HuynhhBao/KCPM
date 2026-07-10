# pyrefly: ignore [missing-import]
import pytest
from unittest.mock import patch
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestWB004RegisterView:
    def setup_method(self):
        from rest_framework.test import APIRequestFactory
        self.factory = APIRequestFactory()
        from accounts.views import RegisterView
        self.view = RegisterView.as_view()

    @patch('accounts.views.cache.set')
    @patch('accounts.views.send_register_otp')
    def test_wb_004_branch_existing_user(self, mock_send_otp, mock_cache_set):
        User.objects.create_user(
            username='existinguser',
            email='test@example.com',
            password='Password123!',
            email_verified=False
        )
        request = self.factory.post('/register/', {
            'email': 'test@example.com',
            'username': 'existinguser', # Must match existing user
            'password': 'Password123!'
        }, format='json')
        response = self.view(request)
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.count() == 1

    @patch('accounts.views.cache.set')
    @patch('accounts.views.send_register_otp')
    def test_wb_004_branch_new_user(self, mock_send_otp, mock_cache_set):
        assert User.objects.count() == 0
        request = self.factory.post('/register/', {
            'email': 'new@example.com',
            'username': 'newuser',
            'password': 'Password123!',
            'full_name': 'New User'
        }, format='json')
        response = self.view(request)
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.count() == 1
