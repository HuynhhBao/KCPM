import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from rest_framework.exceptions import ValidationError

from accounts.serializers import ResetPasswordSerializer
from accounts.views import ForgotPasswordRequestView, ResetPasswordView


class TestForgotResetPasswordUnit(unittest.TestCase):
    """Unit tests for forgot/reset password views."""

    def test_forgot_password_user_not_found_returns_ok(self):
        """Return 200 even if email does not exist."""
        request = SimpleNamespace(data={"email": "user@example.com"})

        with patch("accounts.views.User") as user_model, patch("accounts.views.send_mail") as send_mail:
            user_model.objects.filter.return_value.first.return_value = None
            response = ForgotPasswordRequestView().post(request)

        self.assertEqual(response.status_code, 200)
        send_mail.assert_not_called()

    def test_forgot_password_user_found_sets_cache_and_sends(self):
        """Set cache and send OTP email for existing user."""
        request = SimpleNamespace(data={"email": "user@example.com"})
        user = SimpleNamespace(email="user@example.com")

        with patch("accounts.views.User") as user_model, patch("accounts.views.cache") as cache:
            user_model.objects.filter.return_value.first.return_value = user
            with patch("accounts.views.random.randint", return_value=123456):
                with patch("accounts.views.send_mail") as send_mail:
                    response = ForgotPasswordRequestView().post(request)

        self.assertEqual(response.status_code, 200)
        cache.set.assert_called_once()
        send_mail.assert_called_once()

    def test_forgot_password_email_uppercase_is_lowered_in_cache_key(self):
        """Lower-case email before using it in cache key."""
        request = SimpleNamespace(data={"email": "User@Gmail.COM"})
        user = SimpleNamespace(email="user@gmail.com")

        with patch("accounts.views.User") as user_model, patch("accounts.views.cache") as cache:
            user_model.objects.filter.return_value.first.return_value = user
            with patch("accounts.views.random.randint", return_value=123456):
                with patch("accounts.views.send_mail") as send_mail:
                    response = ForgotPasswordRequestView().post(request)

        self.assertEqual(response.status_code, 200)
        cache.set.assert_called_once()
        send_mail.assert_called_once()
        cache_key = cache.set.call_args[0][0]
        self.assertEqual(cache_key, "forgot_password_otp:user@gmail.com")

    def test_forgot_password_missing_email_raises_validation_error(self):
        """Reject request when email is missing."""
        request = SimpleNamespace(data={})

        with self.assertRaises(ValidationError):
            ForgotPasswordRequestView().post(request)

    def test_reset_password_expired_otp(self):
        """Return 400 when OTP is missing or expired."""
        request = SimpleNamespace(
            data={
                "email": "user@example.com",
                "otp": "123456",
                "new_password": "NewPass123",
                "confirm_password": "NewPass123",
            }
        )

        with patch("accounts.views.cache") as cache:
            cache.get.return_value = None
            response = ResetPasswordView().post(request)

        self.assertEqual(response.status_code, 400)

    def test_reset_password_wrong_otp(self):
        """Return 400 when OTP does not match cached value."""
        request = SimpleNamespace(
            data={
                "email": "user@example.com",
                "otp": "123456",
                "new_password": "NewPass123",
                "confirm_password": "NewPass123",
            }
        )

        with patch("accounts.views.cache") as cache:
            cache.get.return_value = "111111"
            response = ResetPasswordView().post(request)

        self.assertEqual(response.status_code, 400)

    def test_reset_password_wrong_otp_does_not_clear_cache(self):
        """Do not clear cache when OTP is wrong."""
        request = SimpleNamespace(
            data={
                "email": "user@example.com",
                "otp": "123456",
                "new_password": "NewPass123",
                "confirm_password": "NewPass123",
            }
        )

        with patch("accounts.views.cache") as cache:
            cache.get.return_value = "111111"
            response = ResetPasswordView().post(request)

        self.assertEqual(response.status_code, 400)
        cache.delete.assert_not_called()

    def test_reset_password_user_not_found(self):
        """Return 404 when user does not exist for valid OTP."""
        request = SimpleNamespace(
            data={
                "email": "user@example.com",
                "otp": "123456",
                "new_password": "NewPass123",
                "confirm_password": "NewPass123",
            }
        )

        with patch("accounts.views.cache") as cache, patch("accounts.views.User") as user_model:
            cache.get.return_value = "123456"
            user_model.objects.filter.return_value.first.return_value = None
            response = ResetPasswordView().post(request)

        self.assertEqual(response.status_code, 404)

    def test_reset_password_success_updates_password(self):
        """Update password and clear OTP cache on success."""
        request = SimpleNamespace(
            data={
                "email": "user@example.com",
                "otp": "123456",
                "new_password": "NewPass123",
                "confirm_password": "NewPass123",
            }
        )

        user = SimpleNamespace(
            set_password=MagicMock(),
            save=MagicMock(),
        )

        with patch("accounts.views.cache") as cache, patch("accounts.views.User") as user_model:
            cache.get.return_value = "123456"
            user_model.objects.filter.return_value.first.return_value = user
            response = ResetPasswordView().post(request)

        self.assertEqual(response.status_code, 200)
        user.set_password.assert_called_once_with("NewPass123")
        user.save.assert_called_once()
        cache.delete.assert_called_once_with("forgot_password_otp:user@example.com")

    def test_reset_password_serializer_confirm_mismatch(self):
        """Reject reset when confirm password does not match."""
        serializer = ResetPasswordSerializer(
            data={
                "email": "user@example.com",
                "otp": "123456",
                "new_password": "NewPass123",
                "confirm_password": "Mismatch",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("confirm_password", serializer.errors)

    def test_reset_password_serializer_weak_password(self):
        """Reject reset when new password is too weak."""
        serializer = ResetPasswordSerializer(
            data={
                "email": "user@example.com",
                "otp": "123456",
                "new_password": "weakpass",
                "confirm_password": "weakpass",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("new_password", serializer.errors)


if __name__ == "__main__":
    unittest.main()
