import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from accounts.serializers import VerifyRegisterOTPSerializer
from accounts.views import VerifyRegisterOTPView


class TestVerifyRegistrationOtpUnit(unittest.TestCase):
    """Unit tests for VerifyRegisterOTPView OTP flow."""

    def test_verify_otp_serializer_rejects_short_otp(self):
        """Reject OTP values that are not length 6."""
        serializer = VerifyRegisterOTPSerializer(
            data={"email": "user@example.com", "otp": "12345"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("otp", serializer.errors)

    def test_verify_otp_user_not_found(self):
        """Return 404 when user does not exist."""
        request = SimpleNamespace(
            data={"email": "user@example.com", "otp": "123456"}
        )

        with patch("accounts.views.User") as user_model:
            user_model.objects.filter.return_value.first.return_value = None
            response = VerifyRegisterOTPView().post(request)

        self.assertEqual(response.status_code, 404)

    def test_verify_otp_expired(self):
        """Return 400 when OTP is expired or missing in cache."""
        request = SimpleNamespace(
            data={"email": "user@example.com", "otp": "123456"}
        )

        user = SimpleNamespace(
            email="user@example.com",
            email_verified=False,
            is_active=False,
            save=MagicMock(),
        )

        with patch("accounts.views.User") as user_model, patch("accounts.views.cache") as cache:
            user_model.objects.filter.return_value.first.return_value = user
            cache.get.return_value = None
            response = VerifyRegisterOTPView().post(request)

        self.assertEqual(response.status_code, 400)

    def test_verify_otp_wrong_code(self):
        """Return 400 when OTP does not match cached value."""
        request = SimpleNamespace(
            data={"email": "user@example.com", "otp": "123456"}
        )

        user = SimpleNamespace(
            email="user@example.com",
            email_verified=False,
            is_active=False,
            save=MagicMock(),
        )

        with patch("accounts.views.User") as user_model, patch("accounts.views.cache") as cache:
            user_model.objects.filter.return_value.first.return_value = user
            cache.get.return_value = "111111"
            response = VerifyRegisterOTPView().post(request)

        self.assertEqual(response.status_code, 400)

    def test_verify_otp_success_sets_flags_and_clears_cache(self):
        """Activate user and clear cached OTP on success."""
        request = SimpleNamespace(
            data={"email": "user@example.com", "otp": "123456"}
        )

        user = SimpleNamespace(
            email="user@example.com",
            email_verified=False,
            is_active=False,
            save=MagicMock(),
        )

        with patch("accounts.views.User") as user_model, patch("accounts.views.cache") as cache:
            user_model.objects.filter.return_value.first.return_value = user
            cache.get.return_value = "123456"
            response = VerifyRegisterOTPView().post(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(user.email_verified)
        self.assertTrue(user.is_active)
        cache.delete.assert_called_once_with("register_otp:user@example.com")

    def test_verify_otp_lowercases_email_for_cache_key(self):
        """Use lowercase email when checking cached OTP."""
        request = SimpleNamespace(
            data={"email": "USER@EXAMPLE.COM", "otp": "123456"}
        )

        user = SimpleNamespace(
            email="user@example.com",
            email_verified=False,
            is_active=False,
            save=MagicMock(),
        )

        with patch("accounts.views.User") as user_model, patch("accounts.views.cache") as cache:
            user_model.objects.filter.return_value.first.return_value = user
            cache.get.return_value = "123456"
            response = VerifyRegisterOTPView().post(request)

        self.assertEqual(response.status_code, 200)
        cache.get.assert_called_once_with("register_otp:user@example.com")


class TestVerifyRegistrationOtpSerializerUnit(unittest.TestCase):
    """Unit tests for VerifyRegisterOTPSerializer input validation."""

    def test_verify_otp_serializer_accepts_valid_input(self):
        """Accept valid email and OTP length 6."""
        serializer = VerifyRegisterOTPSerializer(
            data={"email": "user@example.com", "otp": "123456"}
        )

        self.assertTrue(serializer.is_valid())

    def test_verify_otp_serializer_missing_email(self):
        """Reject when email is missing."""
        serializer = VerifyRegisterOTPSerializer(
            data={"otp": "123456"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_verify_otp_serializer_missing_otp(self):
        """Reject when OTP is missing."""
        serializer = VerifyRegisterOTPSerializer(
            data={"email": "user@example.com"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("otp", serializer.errors)

    def test_verify_otp_serializer_missing_both_fields(self):
        """Reject when email and OTP are missing."""
        serializer = VerifyRegisterOTPSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)
        self.assertIn("otp", serializer.errors)

    def test_verify_otp_serializer_invalid_email_format(self):
        """Reject invalid email format."""
        serializer = VerifyRegisterOTPSerializer(
            data={"email": "not-an-email", "otp": "123456"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_verify_otp_serializer_email_empty_string(self):
        """Reject empty email string."""
        serializer = VerifyRegisterOTPSerializer(
            data={"email": "", "otp": "123456"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_verify_otp_serializer_email_whitespace(self):
        """Reject email that is only whitespace."""
        serializer = VerifyRegisterOTPSerializer(
            data={"email": "   ", "otp": "123456"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_verify_otp_serializer_email_none(self):
        """Reject email None value."""
        serializer = VerifyRegisterOTPSerializer(
            data={"email": None, "otp": "123456"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_verify_otp_serializer_email_wrong_type_int(self):
        """Reject email with wrong type int."""
        serializer = VerifyRegisterOTPSerializer(
            data={"email": 123, "otp": "123456"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_verify_otp_serializer_email_wrong_type_list(self):
        """Reject email with wrong type list."""
        serializer = VerifyRegisterOTPSerializer(
            data={"email": ["user@example.com"], "otp": "123456"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_verify_otp_serializer_email_wrong_type_dict(self):
        """Reject email with wrong type dict."""
        serializer = VerifyRegisterOTPSerializer(
            data={"email": {"value": "user@example.com"}, "otp": "123456"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_verify_otp_serializer_otp_too_long(self):
        """Reject OTP length greater than 6."""
        serializer = VerifyRegisterOTPSerializer(
            data={"email": "user@example.com", "otp": "1234567"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("otp", serializer.errors)

    def test_verify_otp_serializer_otp_empty_string(self):
        """Reject empty OTP string."""
        serializer = VerifyRegisterOTPSerializer(
            data={"email": "user@example.com", "otp": ""}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("otp", serializer.errors)

    def test_verify_otp_serializer_otp_whitespace(self):
        """Reject OTP that is only whitespace."""
        serializer = VerifyRegisterOTPSerializer(
            data={"email": "user@example.com", "otp": "   "}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("otp", serializer.errors)

    def test_verify_otp_serializer_otp_none(self):
        """Reject OTP None value."""
        serializer = VerifyRegisterOTPSerializer(
            data={"email": "user@example.com", "otp": None}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("otp", serializer.errors)

    def test_verify_otp_serializer_otp_wrong_type_int(self):
        """Accept OTP int coerced to string by DRF."""
        serializer = VerifyRegisterOTPSerializer(
            data={"email": "user@example.com", "otp": 123456}
        )

        self.assertTrue(serializer.is_valid())

    def test_verify_otp_serializer_otp_wrong_type_list(self):
        """Reject OTP with wrong type list."""
        serializer = VerifyRegisterOTPSerializer(
            data={"email": "user@example.com", "otp": ["123456"]}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("otp", serializer.errors)

    def test_verify_otp_serializer_otp_wrong_type_dict(self):
        """Reject OTP with wrong type dict."""
        serializer = VerifyRegisterOTPSerializer(
            data={"email": "user@example.com", "otp": {"value": "123456"}}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("otp", serializer.errors)


if __name__ == "__main__":
    unittest.main()
