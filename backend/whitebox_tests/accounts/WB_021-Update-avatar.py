import pytest
from unittest.mock import patch, MagicMock, call
from rest_framework.exceptions import ValidationError
from accounts.serializers import UserProfileSerializer


class TestUserProfileSerializerUpdate:
    """
    White-box tests for UserProfileSerializer.update() — lines 318–382

    Covers:
      - Branch 1 (lines 335–369): avatar_file is truthy
                                   → call upload_user_avatar, update avatar_url/storage_path/updated_at,
                                     clear avatar_data fields, try/except delete local avatar
      - Branch 2 (line 335)     : avatar_file is None/falsy → skip upload block entirely
      - Branch 3 (lines 373–380): after save(), avatar_file AND old_storage_path != new path
                                   → call delete_cloudinary_avatar_safely(old_storage_path)
    """

    @staticmethod
    def _serializer():
        """Create a UserProfileSerializer instance without calling __init__."""
        return UserProfileSerializer.__new__(UserProfileSerializer)

    @staticmethod
    def _make_instance(avatar_storage_path='', has_avatar=False):
        """Helper: build a mock model instance."""
        instance = MagicMock()
        instance.avatar_storage_path = avatar_storage_path
        instance.pk = 42
        if has_avatar:
            instance.avatar = MagicMock()
        else:
            instance.avatar = None
        return instance

    @staticmethod
    def _make_upload_result(url='https://cdn.example.com/avatar.jpg',
                            storage_path='users/42/avatar',
                            updated_at='2024-01-01T00:00:00Z'):
        return {
            'avatar_url': url,
            'avatar_storage_path': storage_path,
            'avatar_updated_at': updated_at,
        }

    # ------------------------------------------------------------------
    # Branch 1 — lines 335–369  (avatar_file truthy → upload + update fields)
    # ------------------------------------------------------------------

    @patch('accounts.serializers.upload_user_avatar')
    @patch('accounts.serializers.delete_cloudinary_avatar_safely')
    def test_TC1_branch1_hit_avatar_file_present(self, mock_delete_cloud, mock_upload):
        """
        Tests lines 335–369 (Branch 1 — HIT).
        Condition: validated_data contains 'avatar' file → avatar_file is truthy
        Expected : upload_user_avatar called; instance fields updated;
                   avatar_data/content_type/file_name cleared; instance.avatar set to None
        """
        upload_result = self._make_upload_result(
            storage_path='users/42/new_avatar'
        )
        mock_upload.return_value = upload_result

        instance = self._make_instance(avatar_storage_path='', has_avatar=False)
        serializer = self._serializer()
        mock_file = MagicMock()
        validated_data = {'avatar': mock_file}

        serializer.update(instance, validated_data)

        mock_upload.assert_called_once_with(user=instance, uploaded_file=mock_file)
        assert instance.avatar_url == upload_result['avatar_url']
        assert instance.avatar_storage_path == upload_result['avatar_storage_path']
        assert instance.avatar_updated_at == upload_result['avatar_updated_at']
        assert instance.avatar_data is None
        assert instance.avatar_content_type == ''
        assert instance.avatar_file_name == ''
        assert instance.avatar is None

    @patch('accounts.serializers.upload_user_avatar')
    @patch('accounts.serializers.delete_cloudinary_avatar_safely')
    def test_TC2_branch1_hit_deletes_old_local_avatar(self, mock_delete_cloud, mock_upload):
        """
        Tests lines 357–369 (Branch 1 — HIT: try block — local avatar exists and is deleted).
        Condition: instance.avatar is truthy → instance.avatar.delete(save=False) is called
        Expected : instance.avatar.delete called with save=False; instance.avatar set to None
        """
        mock_upload.return_value = self._make_upload_result(storage_path='users/42/new_avatar')

        instance = self._make_instance(avatar_storage_path='', has_avatar=True)
        old_avatar_mock = instance.avatar
        serializer = self._serializer()
        mock_file = MagicMock()
        validated_data = {'avatar': mock_file}

        serializer.update(instance, validated_data)

        old_avatar_mock.delete.assert_called_once_with(save=False)
        assert instance.avatar is None

    @patch('accounts.serializers.upload_user_avatar')
    @patch('accounts.serializers.delete_cloudinary_avatar_safely')
    def test_TC3_branch1_hit_local_avatar_delete_exception_suppressed(self, mock_delete_cloud, mock_upload):
        """
        Tests lines 357–367 (Branch 1 — HIT: except block — delete raises Exception).
        Condition: instance.avatar.delete() raises an Exception
        Expected : Exception is caught and suppressed; execution continues normally
        """
        mock_upload.return_value = self._make_upload_result(storage_path='users/42/new_avatar')

        instance = self._make_instance(avatar_storage_path='', has_avatar=True)
        instance.avatar.delete.side_effect = Exception("disk error")
        serializer = self._serializer()
        mock_file = MagicMock()
        validated_data = {'avatar': mock_file}

        # Should NOT raise — exception must be swallowed
        result = serializer.update(instance, validated_data)
        assert result is instance

    @patch('accounts.serializers.upload_user_avatar')
    @patch('accounts.serializers.delete_cloudinary_avatar_safely')
    def test_TC4_branch1_hit_no_local_avatar_skip_delete(self, mock_delete_cloud, mock_upload):
        """
        Tests lines 357–369 (Branch 1 — HIT: try block — no local avatar, skip delete).
        Condition: instance.avatar is None/falsy → delete is NOT called
        Expected : instance.avatar.delete is never called; instance.avatar remains None
        """
        mock_upload.return_value = self._make_upload_result(storage_path='users/42/new_avatar')

        instance = self._make_instance(avatar_storage_path='', has_avatar=False)
        serializer = self._serializer()
        mock_file = MagicMock()
        validated_data = {'avatar': mock_file}

        serializer.update(instance, validated_data)

        assert instance.avatar is None

    # ------------------------------------------------------------------
    # Branch 2 — line 335  (avatar_file falsy → skip upload block)
    # ------------------------------------------------------------------

    @patch('accounts.serializers.upload_user_avatar')
    @patch('accounts.serializers.delete_cloudinary_avatar_safely')
    def test_TC5_branch2_hit_no_avatar_file(self, mock_delete_cloud, mock_upload):
        """
        Tests line 335 (Branch 2 — HIT: avatar_file is None).
        Condition: validated_data has no 'avatar' key → avatar_file = None
        Expected : upload_user_avatar NOT called; instance fields NOT modified by upload block
        """
        instance = self._make_instance(avatar_storage_path='users/42/existing')
        serializer = self._serializer()
        validated_data = {'full_name': 'Nguyễn Văn An'}

        serializer.update(instance, validated_data)

        mock_upload.assert_not_called()
        mock_delete_cloud.assert_not_called()

    @patch('accounts.serializers.upload_user_avatar')
    @patch('accounts.serializers.delete_cloudinary_avatar_safely')
    def test_TC6_branch2_hit_avatar_explicitly_none(self, mock_delete_cloud, mock_upload):
        """
        Tests line 335 (Branch 2 — HIT: avatar_file explicitly None in validated_data).
        Condition: validated_data = {'avatar': None} → avatar_file = None (falsy)
        Expected : upload_user_avatar NOT called
        """
        instance = self._make_instance(avatar_storage_path='users/42/existing')
        serializer = self._serializer()
        validated_data = {'avatar': None}

        serializer.update(instance, validated_data)

        mock_upload.assert_not_called()

    @patch('accounts.serializers.upload_user_avatar')
    @patch('accounts.serializers.delete_cloudinary_avatar_safely')
    def test_TC7_branch2_hit_other_fields_still_updated(self, mock_delete_cloud, mock_upload):
        """
        Tests lines 324–329 + line 335 (Branch 2 — HIT: non-avatar fields are still set).
        Condition: no avatar_file; validated_data has other fields
        Expected : setattr called for each non-avatar field; instance.save() called
        """
        instance = self._make_instance()
        serializer = self._serializer()
        validated_data = {'full_name': 'Trần Thị B', 'phone': '0901234567'}

        serializer.update(instance, validated_data)

        assert instance.full_name == 'Trần Thị B'
        assert instance.phone == '0901234567'
        instance.save.assert_called_once()

    # ------------------------------------------------------------------
    # Branch 3 — lines 373–380  (avatar_file AND old_path != new_path → delete Cloudinary)
    # ------------------------------------------------------------------

    @patch('accounts.serializers.upload_user_avatar')
    @patch('accounts.serializers.delete_cloudinary_avatar_safely')
    def test_TC8_branch3_hit_old_path_differs_from_new(self, mock_delete_cloud, mock_upload):
        """
        Tests lines 373–380 (Branch 3 — HIT).
        Condition: avatar_file truthy, old_storage_path = 'users/42/old',
                   upload returns new path 'users/42/new' → old != new
        Expected : delete_cloudinary_avatar_safely('users/42/old') called once
        """
        old_path = 'users/42/old_avatar'
        new_path = 'users/42/new_avatar'
        mock_upload.return_value = self._make_upload_result(storage_path=new_path)

        instance = self._make_instance(avatar_storage_path=old_path, has_avatar=False)
        serializer = self._serializer()
        mock_file = MagicMock()
        validated_data = {'avatar': mock_file}

        serializer.update(instance, validated_data)

        mock_delete_cloud.assert_called_once_with(old_path)

    @patch('accounts.serializers.upload_user_avatar')
    @patch('accounts.serializers.delete_cloudinary_avatar_safely')
    def test_TC9_branch3_miss_no_avatar_file(self, mock_delete_cloud, mock_upload):
        """
        Tests lines 373–380 (Branch 3 — MISS: avatar_file is None).
        Condition: no avatar_file → first condition of `and` is False
        Expected : delete_cloudinary_avatar_safely NOT called
        """
        instance = self._make_instance(avatar_storage_path='users/42/old_avatar')
        serializer = self._serializer()
        validated_data = {}

        serializer.update(instance, validated_data)

        mock_delete_cloud.assert_not_called()

    @patch('accounts.serializers.upload_user_avatar')
    @patch('accounts.serializers.delete_cloudinary_avatar_safely')
    def test_TC10_branch3_miss_no_old_storage_path(self, mock_delete_cloud, mock_upload):
        """
        Tests lines 373–380 (Branch 3 — MISS: old_storage_path is empty string).
        Condition: avatar_file truthy, but old_storage_path = '' → falsy → condition fails
        Expected : delete_cloudinary_avatar_safely NOT called
        """
        mock_upload.return_value = self._make_upload_result(storage_path='users/42/new_avatar')

        instance = self._make_instance(avatar_storage_path='', has_avatar=False)
        serializer = self._serializer()
        mock_file = MagicMock()
        validated_data = {'avatar': mock_file}

        serializer.update(instance, validated_data)

        mock_delete_cloud.assert_not_called()

    @patch('accounts.serializers.upload_user_avatar')
    @patch('accounts.serializers.delete_cloudinary_avatar_safely')
    def test_TC11_branch3_miss_same_storage_path(self, mock_delete_cloud, mock_upload):
        """
        Tests lines 373–380 (Branch 3 — MISS: old_path == new_path).
        Condition: avatar_file truthy, old_storage_path == new upload path → paths are equal
        Expected : delete_cloudinary_avatar_safely NOT called (no need to delete same resource)
        """
        same_path = 'users/42/same_avatar'
        mock_upload.return_value = self._make_upload_result(storage_path=same_path)

        instance = self._make_instance(avatar_storage_path=same_path, has_avatar=False)
        serializer = self._serializer()
        mock_file = MagicMock()
        validated_data = {'avatar': mock_file}

        serializer.update(instance, validated_data)

        mock_delete_cloud.assert_not_called()

    # ------------------------------------------------------------------
    # Return value — line 382  (always returns instance)
    # ------------------------------------------------------------------

    @patch('accounts.serializers.upload_user_avatar')
    @patch('accounts.serializers.delete_cloudinary_avatar_safely')
    def test_TC12_returns_instance_with_avatar(self, mock_delete_cloud, mock_upload):
        """
        Tests line 382 (return instance — with avatar upload).
        Condition: full happy path with avatar_file
        Expected : update() returns the same instance object
        """
        mock_upload.return_value = self._make_upload_result(storage_path='users/42/new')
        instance = self._make_instance(avatar_storage_path='users/42/old', has_avatar=False)
        serializer = self._serializer()
        validated_data = {'avatar': MagicMock()}

        result = serializer.update(instance, validated_data)

        assert result is instance

    @patch('accounts.serializers.upload_user_avatar')
    @patch('accounts.serializers.delete_cloudinary_avatar_safely')
    def test_TC13_returns_instance_without_avatar(self, mock_delete_cloud, mock_upload):
        """
        Tests line 382 (return instance — without avatar upload).
        Condition: no avatar_file; only other fields updated
        Expected : update() returns the same instance object
        """
        instance = self._make_instance()
        serializer = self._serializer()
        validated_data = {'full_name': 'Lê Văn C'}

        result = serializer.update(instance, validated_data)

        assert result is instance
