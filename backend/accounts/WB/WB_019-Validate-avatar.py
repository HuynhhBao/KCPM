import pytest
from unittest.mock import MagicMock
from rest_framework.exceptions import ValidationError
from accounts.serializers import UserProfileSerializer


class TestUserProfileSerializerValidateAvatar:
    """
    White-box tests for UserProfileSerializer.validate_avatar() — lines 281–316

    Covers:
      - Branch 1 (lines 282–283): value is falsy (None / empty)     → return value immediately
      - Branch 2 (lines 287–290): value.size > 2MB                  → ValidationError('Ảnh đại diện tối đa 2MB')
      - Branch 3 (lines 311–314): content_type not in allowed_types → ValidationError('Chỉ hỗ trợ ảnh JPG, PNG hoặc WEBP')
      - Branch 4 (line 316)     : all checks pass                   → return value
    """

    MAX_SIZE = 2 * 1024 * 1024  # 2 MB in bytes

    @staticmethod
    def _serializer():
        """Create a UserProfileSerializer instance without calling __init__."""
        return UserProfileSerializer.__new__(UserProfileSerializer)

    @staticmethod
    def _make_file(size, content_type='image/jpeg', name='photo.jpg'):
        """Helper: build a mock file object with .size, .content_type, .name."""
        mock_file = MagicMock()
        mock_file.size = size
        mock_file.content_type = content_type
        mock_file.name = name
        return mock_file

    # ------------------------------------------------------------------
    # Branch 1 — lines 282–283  (not value → return value immediately)
    # ------------------------------------------------------------------

    def test_TC1_branch1_hit_none(self):
        """
        Tests lines 282–283 (Branch 1 — HIT).
        Condition: value = None → `not value` is True
        Expected : returns None immediately, no further checks performed
        """
        serializer = self._serializer()
        result = serializer.validate_avatar(None)
        assert result is None

    def test_TC2_branch1_hit_empty_string(self):
        """
        Tests lines 282–283 (Branch 1 — HIT).
        Condition: value = "" → `not value` is True
        Expected : returns "" immediately, no further checks performed
        """
        serializer = self._serializer()
        result = serializer.validate_avatar("")
        assert result == ""

    def test_TC3_branch1_miss_file_present(self):
        """
        Tests lines 282–283 (Branch 1 — MISS).
        Condition: value is a valid mock file → `not value` is False
        Expected : Branch 1 is NOT taken; execution continues to size check
        """
        serializer = self._serializer()
        mock_file = self._make_file(size=1024, content_type='image/jpeg', name='photo.jpg')
        # Should not return early — will proceed through all checks and return the file
        result = serializer.validate_avatar(mock_file)
        assert result is mock_file

    # ------------------------------------------------------------------
    # Branch 2 — lines 287–290  (value.size > 2MB → ValidationError)
    # ------------------------------------------------------------------

    def test_TC4_branch2_hit_size_exceeds_2mb(self):
        """
        Tests lines 287–290 (Branch 2 — HIT).
        Condition: value.size = 2MB + 1 byte → size > max_size → True
        Expected : ValidationError('Ảnh đại diện tối đa 2MB')
        """
        serializer = self._serializer()
        mock_file = self._make_file(size=self.MAX_SIZE + 1, content_type='image/jpeg', name='big.jpg')
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_avatar(mock_file)
        assert str(exc_info.value.detail[0]) == "Ảnh đại diện tối đa 2MB"

    def test_TC5_branch2_hit_size_far_exceeds_2mb(self):
        """
        Tests lines 287–290 (Branch 2 — HIT).
        Condition: value.size = 10MB → clearly > 2MB
        Expected : ValidationError('Ảnh đại diện tối đa 2MB')
        """
        serializer = self._serializer()
        mock_file = self._make_file(size=10 * 1024 * 1024, content_type='image/png', name='huge.png')
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_avatar(mock_file)
        assert str(exc_info.value.detail[0]) == "Ảnh đại diện tối đa 2MB"

    def test_TC6_branch2_miss_size_exactly_2mb(self):
        """
        Tests lines 287–290 (Branch 2 — MISS).
        Condition: value.size = 2MB exactly → NOT > max_size → False
        Expected : Branch 2 is NOT raised; execution continues to format check
        """
        serializer = self._serializer()
        mock_file = self._make_file(size=self.MAX_SIZE, content_type='image/jpeg', name='exact.jpg')
        # Should not raise size error
        result = serializer.validate_avatar(mock_file)
        assert result is mock_file

    def test_TC7_branch2_miss_size_under_2mb(self):
        """
        Tests lines 287–290 (Branch 2 — MISS).
        Condition: value.size = 1MB → < 2MB → False
        Expected : Branch 2 is NOT raised; execution continues to format check
        """
        serializer = self._serializer()
        mock_file = self._make_file(size=1 * 1024 * 1024, content_type='image/jpeg', name='small.jpg')
        result = serializer.validate_avatar(mock_file)
        assert result is mock_file

    # ------------------------------------------------------------------
    # Branch 3 — lines 311–314  (content_type not in allowed_types)
    # ------------------------------------------------------------------

    def test_TC8_branch3_hit_invalid_content_type(self):
        """
        Tests lines 311–314 (Branch 3 — HIT).
        Condition: content_type = 'image/gif' → not in ['image/jpeg','image/png','image/webp']
        Expected : ValidationError('Chỉ hỗ trợ ảnh JPG, PNG hoặc WEBP')
        """
        serializer = self._serializer()
        mock_file = self._make_file(size=1024, content_type='image/gif', name='anim.gif')
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_avatar(mock_file)
        assert str(exc_info.value.detail[0]) == "Chỉ hỗ trợ ảnh JPG, PNG hoặc WEBP"

    def test_TC9_branch3_hit_pdf_content_type(self):
        """
        Tests lines 311–314 (Branch 3 — HIT).
        Condition: content_type = 'application/pdf' → not in allowed_types
        Expected : ValidationError('Chỉ hỗ trợ ảnh JPG, PNG hoặc WEBP')
        """
        serializer = self._serializer()
        mock_file = self._make_file(size=512, content_type='application/pdf', name='doc.pdf')
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_avatar(mock_file)
        assert str(exc_info.value.detail[0]) == "Chỉ hỗ trợ ảnh JPG, PNG hoặc WEBP"

    def test_TC10_branch3_hit_octet_stream_unguessable_name(self):
        """
        Tests lines 298–314 (Branch 3 — HIT via fallback guess).
        Condition: content_type = 'application/octet-stream', name = 'file.bmp'
                   → guessed_type = 'image/bmp' → not in allowed_types
        Expected : ValidationError('Chỉ hỗ trợ ảnh JPG, PNG hoặc WEBP')
        """
        serializer = self._serializer()
        mock_file = self._make_file(size=1024, content_type='application/octet-stream', name='file.bmp')
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_avatar(mock_file)
        assert str(exc_info.value.detail[0]) == "Chỉ hỗ trợ ảnh JPG, PNG hoặc WEBP"

    def test_TC11_branch3_miss_jpeg(self):
        """
        Tests lines 311–314 (Branch 3 — MISS).
        Condition: content_type = 'image/jpeg' → in allowed_types
        Expected : Branch 3 is NOT raised; function returns the file
        """
        serializer = self._serializer()
        mock_file = self._make_file(size=1024, content_type='image/jpeg', name='photo.jpg')
        result = serializer.validate_avatar(mock_file)
        assert result is mock_file

    def test_TC12_branch3_miss_png(self):
        """
        Tests lines 311–314 (Branch 3 — MISS).
        Condition: content_type = 'image/png' → in allowed_types
        Expected : Branch 3 is NOT raised; function returns the file
        """
        serializer = self._serializer()
        mock_file = self._make_file(size=2048, content_type='image/png', name='image.png')
        result = serializer.validate_avatar(mock_file)
        assert result is mock_file

    def test_TC13_branch3_miss_webp(self):
        """
        Tests lines 311–314 (Branch 3 — MISS).
        Condition: content_type = 'image/webp' → in allowed_types
        Expected : Branch 3 is NOT raised; function returns the file
        """
        serializer = self._serializer()
        mock_file = self._make_file(size=4096, content_type='image/webp', name='image.webp')
        result = serializer.validate_avatar(mock_file)
        assert result is mock_file

    # ------------------------------------------------------------------
    # Branch 4 — line 316  (all checks pass → return value)
    # ------------------------------------------------------------------

    def test_TC14_branch4_happy_path_jpeg(self):
        """
        Tests line 316 (Branch 4 — Happy path).
        Condition: JPEG file, size = 500KB → passes all branches
        Expected : returns the original file object unchanged
        """
        serializer = self._serializer()
        mock_file = self._make_file(size=500 * 1024, content_type='image/jpeg', name='avatar.jpg')
        result = serializer.validate_avatar(mock_file)
        assert result is mock_file

    def test_TC15_branch4_happy_path_png(self):
        """
        Tests line 316 (Branch 4 — Happy path).
        Condition: PNG file, size = 1MB → passes all branches
        Expected : returns the original file object unchanged
        """
        serializer = self._serializer()
        mock_file = self._make_file(size=1 * 1024 * 1024, content_type='image/png', name='avatar.png')
        result = serializer.validate_avatar(mock_file)
        assert result is mock_file

    def test_TC16_branch4_happy_path_webp(self):
        """
        Tests line 316 (Branch 4 — Happy path).
        Condition: WEBP file, size = 2MB exactly → passes all branches
        Expected : returns the original file object unchanged
        """
        serializer = self._serializer()
        mock_file = self._make_file(size=self.MAX_SIZE, content_type='image/webp', name='avatar.webp')
        result = serializer.validate_avatar(mock_file)
        assert result is mock_file

    def test_TC17_branch4_happy_path_octet_stream_jpg_name(self):
        """
        Tests lines 298–309 + line 316 (Branch 4 — Happy path via fallback guess).
        Condition: content_type = 'application/octet-stream', name = 'photo.jpg'
                   → guessed_type = 'image/jpeg' → in allowed_types → passes
        Expected : returns the original file object unchanged
        """
        serializer = self._serializer()
        mock_file = self._make_file(size=1024, content_type='application/octet-stream', name='photo.jpg')
        result = serializer.validate_avatar(mock_file)
        assert result is mock_file
