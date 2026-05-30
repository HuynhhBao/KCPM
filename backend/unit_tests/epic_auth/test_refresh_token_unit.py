import unittest

from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer


class TestRefreshTokenUnit(unittest.TestCase):
    """Pure unit tests for TokenRefreshSerializer (SimpleJWT)."""

    def test_refresh_token_missing_field(self):
        serializer = TokenRefreshSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertIn("refresh", serializer.errors)

    def test_refresh_token_none_value(self):
        serializer = TokenRefreshSerializer(data={"refresh": None})

        self.assertFalse(serializer.is_valid())
        self.assertIn("refresh", serializer.errors)

    def test_refresh_token_empty_string(self):
        serializer = TokenRefreshSerializer(data={"refresh": ""})

        # empty string → thường fail validate hoặc TokenError tùy version
        self.assertFalse(serializer.is_valid())

    def test_refresh_token_invalid_string(self):
        """Invalid plain string (not JWT)"""
        serializer = TokenRefreshSerializer(data={"refresh": "invalid"})

        with self.assertRaises(TokenError):
            serializer.is_valid(raise_exception=True)

    def test_refresh_token_jwt_like_invalid_format(self):
        """JWT format nhưng sai cấu trúc / signature"""
        serializer = TokenRefreshSerializer(data={"refresh": "abc.def.ghi"})

        with self.assertRaises(TokenError):
            serializer.is_valid(raise_exception=True)

    def test_refresh_token_non_string_int(self):
        """Non-string input (int)"""
        serializer = TokenRefreshSerializer(data={"refresh": 123})

        with self.assertRaises(TokenError):
            serializer.is_valid(raise_exception=True)

    def test_refresh_token_non_string_list(self):
        serializer = TokenRefreshSerializer(data={"refresh": ["abc"]})

        self.assertFalse(serializer.is_valid())

    def test_refresh_token_non_string_dict(self):
        serializer = TokenRefreshSerializer(data={"refresh": {"token": "abc"}})

        self.assertFalse(serializer.is_valid())


if __name__ == "__main__":
    unittest.main()