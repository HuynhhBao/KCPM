import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from accounts.serializers import ChangePasswordSerializer
from accounts.views import ChangePasswordView


class TestChangePasswordUnit(unittest.TestCase):
    """Unit tests for change password validation and view logic."""

    def test_change_password_confirm_mismatch(self):
        """Reject when new password and confirm do not match."""
        serializer = ChangePasswordSerializer(
            data={
                "old_password": "OldPass123",
                "new_password": "NewPass123",
                "confirm_password": "Mismatch",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("confirm_password", serializer.errors)

    def test_change_password_wrong_old_password(self):
        """Return 400 when old password does not match."""
        request = SimpleNamespace(
            data={
                "old_password": "WrongOld",
                "new_password": "NewPass123",
                "confirm_password": "NewPass123",
            },
            user=SimpleNamespace(password="hashed"),
        )

        with patch("accounts.views.check_password", return_value=False):
            response = ChangePasswordView().post(request)

        self.assertEqual(response.status_code, 400)

    def test_change_password_success(self):
        """Update password when old password is valid."""
        user = SimpleNamespace(
            password="hashed",
            set_password=MagicMock(),
            save=MagicMock(),
        )

        request = SimpleNamespace(
            data={
                "old_password": "OldPass123",
                "new_password": "NewPass123",
                "confirm_password": "NewPass123",
            },
            user=user,
        )

        with patch("accounts.views.check_password", return_value=True):
            response = ChangePasswordView().post(request)

        self.assertEqual(response.status_code, 200)
        user.set_password.assert_called_once_with("NewPass123")
        user.save.assert_called_once()

    def test_change_password_same_as_old(self):
        """Return 400 when new password is the same as old password."""
        user = SimpleNamespace(
            password="hashed",
            set_password=MagicMock(),
            save=MagicMock(),
        )

        request = SimpleNamespace(
            data={
                "old_password": "OldPass123",
                "new_password": "OldPass123",
                "confirm_password": "OldPass123",
            },
            user=user,
        )

        with patch("accounts.views.check_password", return_value=True):
            response = ChangePasswordView().post(request)

        self.assertEqual(response.status_code, 400)
        user.set_password.assert_not_called()
        user.save.assert_not_called()

    def test_change_password_weak_new_password(self):
        """Reject when new password is too weak (too short or all digits)."""
        serializer = ChangePasswordSerializer(
            data={
                "old_password": "OldPass123",
                "new_password": "123",
                "confirm_password": "123",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("new_password", serializer.errors)

    def test_change_password_missing_required_fields(self):
        """Reject when required fields are missing from request."""
        serializer = ChangePasswordSerializer(
            data={
                "new_password": "NewPass123",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("old_password", serializer.errors)

if __name__ == "__main__":
    unittest.main()
