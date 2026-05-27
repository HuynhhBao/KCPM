import unittest
from types import SimpleNamespace
from unittest.mock import patch

from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.views import CustomTokenObtainPairSerializer


class TestLoginUnit(unittest.TestCase):
    """Unit tests for login validation via CustomTokenObtainPairSerializer."""
    def test_login_rejects_unverified_email(self):
        """Reject login when user email is not verified."""
        def fake_validate(self, attrs):
            self.user = SimpleNamespace(email_verified=False)
            return {"access": "a", "refresh": "r"}

        serializer = CustomTokenObtainPairSerializer(
            data={"email": "user@example.com", "password": "pass"}
        )

        with patch.object(TokenObtainPairSerializer, "validate", fake_validate):
            with self.assertRaises(ValidationError) as ctx:
                serializer.validate(serializer.initial_data)

        self.assertIn("Email chưa được xác thực", str(ctx.exception.detail))

    def test_login_allows_verified_email(self):
        """Allow login when user email is verified."""
        expected = {"access": "a", "refresh": "r"}

        def fake_validate(self, attrs):
            self.user = SimpleNamespace(email_verified=True)
            return expected

        serializer = CustomTokenObtainPairSerializer(
            data={"email": "user@example.com", "password": "pass"}
        )

        with patch.object(TokenObtainPairSerializer, "validate", fake_validate):
            data = serializer.validate(serializer.initial_data)

        self.assertEqual(data, expected)

    def test_login_propagates_invalid_credentials(self):
        """Propagate underlying invalid-credentials error from SimpleJWT."""
        def fake_validate(self, attrs):
            raise ValidationError({"detail": "No active account found"})

        serializer = CustomTokenObtainPairSerializer(
            data={"email": "user@example.com", "password": "wrong"}
        )

        with patch.object(TokenObtainPairSerializer, "validate", fake_validate):
            with self.assertRaises(ValidationError) as ctx:
                serializer.validate(serializer.initial_data)

        self.assertIn("No active account found", str(ctx.exception.detail))


if __name__ == "__main__":
    unittest.main()