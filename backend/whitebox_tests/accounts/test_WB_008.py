# pyrefly: ignore [missing-import]
import pytest
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestWB008UserAvatarView:
    def setup_method(self):
        from django.test import RequestFactory
        self.factory = RequestFactory()
        from accounts.views import UserAvatarView
        self.view = UserAvatarView.as_view()

    def test_wb_008_branch_not_found(self):
        request = self.factory.get('/avatar/')
        response = self.view(request, user_id=999)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_wb_008_branch_fallback_content_type(self):
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Password123!',
            avatar_data=b'data',
            avatar_content_type='' # Should be empty string, not None
        )
        request = self.factory.get('/avatar/')
        response = self.view(request, user_id=user.id)
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'application/octet-stream'

    def test_wb_008_branch_v_param(self):
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Password123!',
            avatar_data=b'data',
            avatar_content_type='image/png'
        )
        request = self.factory.get('/avatar/?v=1')
        response = self.view(request, user_id=user.id)
        assert response.status_code == status.HTTP_200_OK
        assert response['Cache-Control'] == 'public, max-age=31536000, immutable'
