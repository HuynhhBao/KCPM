# pyrefly: ignore [missing-import]
import pytest
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestWB010ChangePasswordView:
    def setup_method(self):
        from rest_framework.test import APIRequestFactory, force_authenticate
        self.factory = APIRequestFactory()
        self.force_authenticate = force_authenticate
        from accounts.views import ChangePasswordView
        self.view = ChangePasswordView.as_view()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='OldPassword123!'
        )

    def test_wb_010_branch_wrong_password(self):
        request = self.factory.post('/change/', {'old_password': 'wrong', 'new_password': 'NewPassword1!', 'confirm_password': 'NewPassword1!'}, format='json')
        self.force_authenticate(request, user=self.user)
        response = self.view(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_wb_010_branch_same_password(self):
        request = self.factory.post('/change/', {'old_password': 'OldPassword123!', 'new_password': 'OldPassword123!', 'confirm_password': 'OldPassword123!'}, format='json')
        self.force_authenticate(request, user=self.user)
        response = self.view(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_wb_010_branch_success(self):
        request = self.factory.post('/change/', {'old_password': 'OldPassword123!', 'new_password': 'NewPassword123!', 'confirm_password': 'NewPassword123!'}, format='json')
        self.force_authenticate(request, user=self.user)
        response = self.view(request)
        assert response.status_code == status.HTTP_200_OK
