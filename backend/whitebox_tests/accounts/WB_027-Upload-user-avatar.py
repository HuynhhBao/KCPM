import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from accounts.cloudinary_storage import upload_user_avatar


class TestUploadUserAvatar:
    """
    White-box tests for upload_user_avatar() — lines 106–161 (cloudinary_storage.py)

    Covers:
      - Branch 1 (lines 111–114): user is None/falsy       → raise ValueError('Thiếu user khi upload avatar')
      - Branch 2 (lines 116–119): uploaded_file is falsy   → raise ValueError('Thiếu file avatar')
      - Branch 3 (lines 152–155): secure_url or uploaded_public_id empty after upload
                                   → raise RuntimeError('Upload avatar lên Cloudinary thất bại')
      - Happy path (lines 157–161): all checks pass        → return dict with avatar_url, storage_path, updated_at
    """

    @staticmethod
    def _make_user(user_id=42):
        """Helper: build a mock user with an id."""
        user = MagicMock()
        user.id = user_id
        return user

    @staticmethod
    def _make_file():
        """Helper: build a minimal in-memory file object."""
        buf = BytesIO(b'fake-image-data')
        buf.name = 'avatar.jpg'
        return buf

    # ------------------------------------------------------------------
    # Branch 1 — lines 111–114  (user is falsy → ValueError)
    # ------------------------------------------------------------------

    def test_TC1_branch1_hit_user_none(self):
        """
        Tests lines 111–114 (Branch 1 — HIT).
        Condition: user = None → `not user` is True
        Expected : ValueError('Thiếu user khi upload avatar')
        """
        with pytest.raises(ValueError) as exc_info:
            upload_user_avatar(user=None, uploaded_file=self._make_file())
        assert str(exc_info.value) == 'Thiếu user khi upload avatar'

    def test_TC2_branch1_hit_user_false(self):
        """
        Tests lines 111–114 (Branch 1 — HIT).
        Condition: user = False → `not user` is True
        Expected : ValueError('Thiếu user khi upload avatar')
        """
        with pytest.raises(ValueError) as exc_info:
            upload_user_avatar(user=False, uploaded_file=self._make_file())
        assert str(exc_info.value) == 'Thiếu user khi upload avatar'

    def test_TC3_branch1_miss_user_present(self):
        """
        Tests lines 111–114 (Branch 1 — MISS).
        Condition: user is a valid mock object → `not user` is False
        Expected : Branch 1 not raised; execution continues to uploaded_file check
        """
        user = self._make_user()
        # uploaded_file = None to trigger branch 2 (not branch 1)
        with pytest.raises(ValueError) as exc_info:
            upload_user_avatar(user=user, uploaded_file=None)
        assert str(exc_info.value) == 'Thiếu file avatar'

    # ------------------------------------------------------------------
    # Branch 2 — lines 116–119  (uploaded_file is falsy → ValueError)
    # ------------------------------------------------------------------

    def test_TC4_branch2_hit_file_none(self):
        """
        Tests lines 116–119 (Branch 2 — HIT).
        Condition: user valid, uploaded_file = None → `not uploaded_file` is True
        Expected : ValueError('Thiếu file avatar')
        """
        with pytest.raises(ValueError) as exc_info:
            upload_user_avatar(user=self._make_user(), uploaded_file=None)
        assert str(exc_info.value) == 'Thiếu file avatar'

    def test_TC5_branch2_hit_file_false(self):
        """
        Tests lines 116–119 (Branch 2 — HIT).
        Condition: user valid, uploaded_file = False → `not uploaded_file` is True
        Expected : ValueError('Thiếu file avatar')
        """
        with pytest.raises(ValueError) as exc_info:
            upload_user_avatar(user=self._make_user(), uploaded_file=False)
        assert str(exc_info.value) == 'Thiếu file avatar'

    def test_TC6_branch2_hit_file_empty_string(self):
        """
        Tests lines 116–119 (Branch 2 — HIT).
        Condition: user valid, uploaded_file = '' → `not uploaded_file` is True
        Expected : ValueError('Thiếu file avatar')
        """
        with pytest.raises(ValueError) as exc_info:
            upload_user_avatar(user=self._make_user(), uploaded_file='')
        assert str(exc_info.value) == 'Thiếu file avatar'

    # ------------------------------------------------------------------
    # Branch 3 — lines 152–155  (secure_url or public_id empty → RuntimeError)
    # ------------------------------------------------------------------

    @patch('accounts.cloudinary_storage.configure_cloudinary')
    @patch('accounts.cloudinary_storage._normalize_avatar_image')
    @patch('accounts.cloudinary_storage.cloudinary.uploader.upload')
    def test_TC7_branch3_hit_secure_url_empty(self, mock_upload, mock_normalize, mock_configure):
        """
        Tests lines 152–155 (Branch 3 — HIT: secure_url is empty).
        Condition: cloudinary upload returns secure_url='' and public_id='some/path'
        Expected : RuntimeError('Upload avatar lên Cloudinary thất bại')
        """
        mock_normalize.return_value = self._make_file()
        mock_upload.return_value = {'secure_url': '', 'public_id': 'chung_vi/avatars/users/42/avatar_123'}
        with pytest.raises(RuntimeError) as exc_info:
            upload_user_avatar(user=self._make_user(), uploaded_file=self._make_file())
        assert str(exc_info.value) == 'Upload avatar lên Cloudinary thất bại'

    @patch('accounts.cloudinary_storage.configure_cloudinary')
    @patch('accounts.cloudinary_storage._normalize_avatar_image')
    @patch('accounts.cloudinary_storage.cloudinary.uploader.upload')
    def test_TC8_branch3_hit_public_id_empty(self, mock_upload, mock_normalize, mock_configure):
        """
        Tests lines 152–155 (Branch 3 — HIT: uploaded_public_id is empty).
        Condition: cloudinary upload returns secure_url='https://...' but public_id=''
        Expected : RuntimeError('Upload avatar lên Cloudinary thất bại')
        """
        mock_normalize.return_value = self._make_file()
        mock_upload.return_value = {'secure_url': 'https://cdn.example.com/avatar.webp', 'public_id': ''}
        with pytest.raises(RuntimeError) as exc_info:
            upload_user_avatar(user=self._make_user(), uploaded_file=self._make_file())
        assert str(exc_info.value) == 'Upload avatar lên Cloudinary thất bại'

    @patch('accounts.cloudinary_storage.configure_cloudinary')
    @patch('accounts.cloudinary_storage._normalize_avatar_image')
    @patch('accounts.cloudinary_storage.cloudinary.uploader.upload')
    def test_TC9_branch3_hit_both_empty(self, mock_upload, mock_normalize, mock_configure):
        """
        Tests lines 152–155 (Branch 3 — HIT: both secure_url and public_id empty).
        Condition: cloudinary upload returns empty dict
        Expected : RuntimeError('Upload avatar lên Cloudinary thất bại')
        """
        mock_normalize.return_value = self._make_file()
        mock_upload.return_value = {'secure_url': None, 'public_id': None}
        with pytest.raises(RuntimeError) as exc_info:
            upload_user_avatar(user=self._make_user(), uploaded_file=self._make_file())
        assert str(exc_info.value) == 'Upload avatar lên Cloudinary thất bại'

    @patch('accounts.cloudinary_storage.configure_cloudinary')
    @patch('accounts.cloudinary_storage._normalize_avatar_image')
    @patch('accounts.cloudinary_storage.cloudinary.uploader.upload')
    def test_TC10_branch3_hit_whitespace_only_values(self, mock_upload, mock_normalize, mock_configure):
        """
        Tests lines 144–155 (Branch 3 — HIT: values are whitespace → strip() → empty).
        Condition: secure_url = '   ', public_id = '   ' → after strip both become ''
        Expected : RuntimeError('Upload avatar lên Cloudinary thất bại')
        """
        mock_normalize.return_value = self._make_file()
        mock_upload.return_value = {'secure_url': '   ', 'public_id': '   '}
        with pytest.raises(RuntimeError) as exc_info:
            upload_user_avatar(user=self._make_user(), uploaded_file=self._make_file())
        assert str(exc_info.value) == 'Upload avatar lên Cloudinary thất bại'

    @patch('accounts.cloudinary_storage.configure_cloudinary')
    @patch('accounts.cloudinary_storage._normalize_avatar_image')
    @patch('accounts.cloudinary_storage.cloudinary.uploader.upload')
    def test_TC11_branch3_miss_both_values_present(self, mock_upload, mock_normalize, mock_configure):
        """
        Tests lines 152–155 (Branch 3 — MISS: both values non-empty).
        Condition: secure_url and public_id both have valid values
        Expected : no RuntimeError; function returns result dict
        """
        mock_normalize.return_value = self._make_file()
        mock_upload.return_value = {
            'secure_url': 'https://cdn.example.com/avatar.webp',
            'public_id': 'chung_vi/avatars/users/42/avatar_123',
        }
        result = upload_user_avatar(user=self._make_user(), uploaded_file=self._make_file())
        assert result['avatar_url'] == 'https://cdn.example.com/avatar.webp'

    # ------------------------------------------------------------------
    # Happy path — lines 157–161  (return dict with all 3 keys)
    # ------------------------------------------------------------------

    @patch('accounts.cloudinary_storage.configure_cloudinary')
    @patch('accounts.cloudinary_storage._normalize_avatar_image')
    @patch('accounts.cloudinary_storage.cloudinary.uploader.upload')
    def test_TC12_happy_path_returns_correct_dict(self, mock_upload, mock_normalize, mock_configure):
        """
        Tests lines 157–161 (Happy path).
        Condition: user valid, file valid, upload returns secure_url + public_id
        Expected : returns dict with keys 'avatar_url', 'avatar_storage_path', 'avatar_updated_at'
        """
        mock_normalize.return_value = self._make_file()
        mock_upload.return_value = {
            'secure_url': 'https://cdn.example.com/avatar.webp',
            'public_id': 'chung_vi/avatars/users/42/avatar_abc123',
        }
        result = upload_user_avatar(user=self._make_user(), uploaded_file=self._make_file())
        assert 'avatar_url' in result
        assert 'avatar_storage_path' in result
        assert 'avatar_updated_at' in result
        assert result['avatar_url'] == 'https://cdn.example.com/avatar.webp'
        assert result['avatar_storage_path'] == 'chung_vi/avatars/users/42/avatar_abc123'

    @patch('accounts.cloudinary_storage.configure_cloudinary')
    @patch('accounts.cloudinary_storage._normalize_avatar_image')
    @patch('accounts.cloudinary_storage.cloudinary.uploader.upload')
    def test_TC13_happy_path_configure_cloudinary_called(self, mock_upload, mock_normalize, mock_configure):
        """
        Tests line 121 (Happy path — configure_cloudinary called before upload).
        Condition: valid user and file
        Expected : configure_cloudinary() called exactly once before cloudinary.uploader.upload
        """
        mock_normalize.return_value = self._make_file()
        mock_upload.return_value = {
            'secure_url': 'https://cdn.example.com/avatar.webp',
            'public_id': 'chung_vi/avatars/users/42/avatar_xyz',
        }
        upload_user_avatar(user=self._make_user(), uploaded_file=self._make_file())
        mock_configure.assert_called_once()

    @patch('accounts.cloudinary_storage.configure_cloudinary')
    @patch('accounts.cloudinary_storage._normalize_avatar_image')
    @patch('accounts.cloudinary_storage.cloudinary.uploader.upload')
    def test_TC14_happy_path_normalize_called_with_file(self, mock_upload, mock_normalize, mock_configure):
        """
        Tests line 131–133 (Happy path — _normalize_avatar_image called with uploaded_file).
        Condition: valid user and file
        Expected : _normalize_avatar_image called once with the uploaded_file argument
        """
        uploaded = self._make_file()
        normalized = self._make_file()
        mock_normalize.return_value = normalized
        mock_upload.return_value = {
            'secure_url': 'https://cdn.example.com/avatar.webp',
            'public_id': 'chung_vi/avatars/users/42/avatar_xyz',
        }
        upload_user_avatar(user=self._make_user(), uploaded_file=uploaded)
        mock_normalize.assert_called_once_with(uploaded)

    @patch('accounts.cloudinary_storage.configure_cloudinary')
    @patch('accounts.cloudinary_storage._normalize_avatar_image')
    @patch('accounts.cloudinary_storage.cloudinary.uploader.upload')
    def test_TC15_happy_path_public_id_contains_user_id(self, mock_upload, mock_normalize, mock_configure):
        """
        Tests lines 126–129 (Happy path — public_id includes user.id).
        Condition: user.id = 99
        Expected : cloudinary.uploader.upload called with public_id containing '99'
        """
        user = self._make_user(user_id=99)
        mock_normalize.return_value = self._make_file()
        mock_upload.return_value = {
            'secure_url': 'https://cdn.example.com/avatar.webp',
            'public_id': 'chung_vi/avatars/users/99/avatar_abc',
        }
        upload_user_avatar(user=user, uploaded_file=self._make_file())
        call_kwargs = mock_upload.call_args
        assert '99' in call_kwargs.kwargs.get('public_id', call_kwargs[1].get('public_id', ''))
