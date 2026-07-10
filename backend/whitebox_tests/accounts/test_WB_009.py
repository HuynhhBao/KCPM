# pyrefly: ignore [missing-import]
import pytest
from rest_framework import status
from django.contrib.auth import get_user_model
from notifications.models import FCMDevice

User = get_user_model()

@pytest.mark.django_db
class TestWB009SaveFCMTokenView:
    def setup_method(self):
        from rest_framework.test import APIRequestFactory, force_authenticate
        self.factory = APIRequestFactory()
        self.force_authenticate = force_authenticate
        from accounts.views import SaveFCMTokenView
        self.view = SaveFCMTokenView.as_view()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Password123!'
        )

    def test_wb_009_branch_invalid_token(self):
        request = self.factory.post('/fcm/', {'token': 123}, format='json')
        self.force_authenticate(request, user=self.user)
        response = self.view(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_wb_009_branch_invalid_device(self):
        request = self.factory.post('/fcm/', {'token': 'valid', 'device_type': 'win'}, format='json')
        self.force_authenticate(request, user=self.user)
        response = self.view(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_wb_009_branch_success(self):
        request = self.factory.post('/fcm/', {'token': 'valid', 'device_type': 'android'}, format='json')
        self.force_authenticate(request, user=self.user)
        response = self.view(request)
        assert response.status_code == status.HTTP_200_OK
        assert FCMDevice.objects.filter(token='valid').exists()
