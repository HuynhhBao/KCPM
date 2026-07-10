# pyrefly: ignore [missing-import]
import pytest
from unittest.mock import patch
from rest_framework import status
from django.contrib.auth import get_user_model
from accounts.views import GoogleProviderUnavailableError

User = get_user_model()

@pytest.mark.django_db
class TestWB013GoogleLoginView:
    def setup_method(self):
        from rest_framework.test import APIRequestFactory
        self.factory = APIRequestFactory()
        from accounts.views import GoogleLoginView
        self.view = GoogleLoginView.as_view()

    def test_wb_013_branch_missing_token(self):
        request = self.factory.post('/google/', {}, format='json')
        response = self.view(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch('accounts.views.get_google_identity')
    def test_wb_013_branch_success_new_user(self, mock_identity):
        mock_identity.return_value = {'email': 'new@example.com', 'full_name': 'New'}
        request = self.factory.post('/google/', {'token': 'valid'}, format='json')
        response = self.view(request)
        assert response.status_code == status.HTTP_200_OK
        assert User.objects.count() == 1

    @patch('accounts.views.get_google_identity')
    def test_wb_013_branch_success_existing_user(self, mock_identity):
        User.objects.create_user(username='test', email='existing@example.com', password='pwd')
        mock_identity.return_value = {'email': 'existing@example.com', 'full_name': 'Updated'}
        request = self.factory.post('/google/', {'token': 'valid'}, format='json')
        response = self.view(request)
        assert response.status_code == status.HTTP_200_OK
        assert User.objects.count() == 1
