# pyrefly: ignore [missing-import]
import pytest
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from unittest.mock import patch

User = get_user_model()

@pytest.mark.django_db
class TestWB007CustomTokenObtainPairSerializer:
    def setup_method(self):
        from accounts.views import CustomTokenObtainPairSerializer
        self.serializer_class = CustomTokenObtainPairSerializer

    @patch('accounts.views.TokenObtainPairSerializer.validate')
    def test_wb_007_branch_email_not_verified(self, mock_super_validate):
        mock_super_validate.return_value = {'access': 'token'}
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Password123!',
            email_verified=False
        )
        serializer = self.serializer_class()
        serializer.user = user
        with pytest.raises(ValidationError):
            serializer.validate({})

    @patch('accounts.views.TokenObtainPairSerializer.validate')
    def test_wb_007_branch_success(self, mock_super_validate):
        mock_super_validate.return_value = {'access': 'token'}
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Password123!',
            email_verified=True
        )
        serializer = self.serializer_class()
        serializer.user = user
        assert serializer.validate({}) == {'access': 'token'}
