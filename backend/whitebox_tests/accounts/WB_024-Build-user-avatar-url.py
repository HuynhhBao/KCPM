import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from accounts.avatar_utils import build_user_avatar_url


class TestBuildUserAvatarUrl:
    """
    White-box tests for build_user_avatar_url() — lines 4–66 (avatar_utils.py)

    Covers:
      - Branch 1 (lines 5–6)  : user is None/falsy              → return ''
      - Branch 2 (lines 12–13): avatar_url field has value       → return avatar_url directly
      - Branch 3 (lines 21–47): avatar_data has value            → build internal path;
                                  sub-branch 3a: avatar_updated_at present → append ?v=<timestamp>
                                  sub-branch 3b: no avatar_updated_at      → no version suffix
                                  sub-branch 3c: request present           → build_absolute_uri
                                  sub-branch 3d: no request                → return relative url
      - Branch 4 (lines 55–64): avatar field has value           → get avatar.url;
                                  sub-branch 4a: ValueError raised          → return ''
                                  sub-branch 4b: request present            → build_absolute_uri
                                  sub-branch 4c: no request                 → return url directly
      - Branch 5 (line 66)    : nothing available                → return ''
    """

    @staticmethod
    def _make_user(**kwargs):
        """Helper: build a mock user with configurable attributes."""
        user = MagicMock()
        user.id = kwargs.get('id', 1)
        user.avatar_url = kwargs.get('avatar_url', '')
        user.avatar_data = kwargs.get('avatar_data', None)
        user.avatar_updated_at = kwargs.get('avatar_updated_at', None)
        user.avatar = kwargs.get('avatar', None)
        return user

    # ------------------------------------------------------------------
    # Branch 1 — lines 5–6  (user is falsy → return '')
    # ------------------------------------------------------------------

    def test_TC1_branch1_hit_user_none(self):
        """
        Tests lines 5–6 (Branch 1 — HIT).
        Condition: user = None → `not user` is True
        Expected : returns ''
        """
        result = build_user_avatar_url(None)
        assert result == ''

    def test_TC2_branch1_hit_user_false(self):
        """
        Tests lines 5–6 (Branch 1 — HIT).
        Condition: user = False → `not user` is True
        Expected : returns ''
        """
        result = build_user_avatar_url(False)
        assert result == ''

    # ------------------------------------------------------------------
    # Branch 2 — lines 12–13  (avatar_url has value → return directly)
    # ------------------------------------------------------------------

    def test_TC3_branch2_hit_avatar_url_set(self):
        """
        Tests lines 12–13 (Branch 2 — HIT).
        Condition: user.avatar_url = 'https://cdn.example.com/avatar.jpg' (non-empty after strip)
        Expected : returns 'https://cdn.example.com/avatar.jpg' immediately
        """
        user = self._make_user(avatar_url='https://cdn.example.com/avatar.jpg')
        result = build_user_avatar_url(user)
        assert result == 'https://cdn.example.com/avatar.jpg'

    def test_TC4_branch2_hit_avatar_url_with_whitespace(self):
        """
        Tests lines 8–13 (Branch 2 — HIT: strip applied before check).
        Condition: user.avatar_url = '  https://cdn.example.com/avatar.jpg  '
        Expected : returns 'https://cdn.example.com/avatar.jpg' (stripped)
        """
        user = self._make_user(avatar_url='  https://cdn.example.com/avatar.jpg  ')
        result = build_user_avatar_url(user)
        assert result == 'https://cdn.example.com/avatar.jpg'

    def test_TC5_branch2_miss_avatar_url_empty(self):
        """
        Tests lines 12–13 (Branch 2 — MISS).
        Condition: user.avatar_url = '' → falsy → branch 2 not taken
        Expected : execution continues to avatar_data check
        """
        user = self._make_user(avatar_url='', avatar_data=None, avatar=None)
        result = build_user_avatar_url(user)
        assert result == ''  # falls through to Branch 5

    # ------------------------------------------------------------------
    # Branch 3 — lines 21–47  (avatar_data has value → build internal path)
    # ------------------------------------------------------------------

    @patch('accounts.avatar_utils.reverse')
    def test_TC6_branch3_hit_no_updated_at_no_request(self, mock_reverse):
        """
        Tests lines 21–47 (Branch 3 — HIT: sub-branch 3b + 3d).
        Condition: avatar_data truthy, avatar_updated_at = None, request = None
        Expected : returns relative path without ?v= suffix
        """
        mock_reverse.return_value = '/api/users/1/avatar/'
        user = self._make_user(avatar_url='', avatar_data=b'imagedata', avatar_updated_at=None)
        result = build_user_avatar_url(user, request=None)
        assert result == '/api/users/1/avatar/'
        mock_reverse.assert_called_once_with('user-avatar', kwargs={'user_id': user.id})

    @patch('accounts.avatar_utils.reverse')
    def test_TC7_branch3_hit_with_updated_at_no_request(self, mock_reverse):
        """
        Tests lines 21–47 (Branch 3 — HIT: sub-branch 3a + 3d).
        Condition: avatar_data truthy, avatar_updated_at set, request = None
        Expected : returns relative path with ?v=<timestamp> suffix
        """
        mock_reverse.return_value = '/api/users/1/avatar/'
        ts = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        user = self._make_user(avatar_url='', avatar_data=b'imagedata', avatar_updated_at=ts)
        result = build_user_avatar_url(user, request=None)
        expected_version = f'?v={int(ts.timestamp())}'
        assert result == f'/api/users/1/avatar/{expected_version}'

    @patch('accounts.avatar_utils.reverse')
    def test_TC8_branch3_hit_no_updated_at_with_request(self, mock_reverse):
        """
        Tests lines 21–47 (Branch 3 — HIT: sub-branch 3b + 3c).
        Condition: avatar_data truthy, avatar_updated_at = None, request provided
        Expected : returns request.build_absolute_uri(path)
        """
        mock_reverse.return_value = '/api/users/1/avatar/'
        user = self._make_user(avatar_url='', avatar_data=b'imagedata', avatar_updated_at=None)
        mock_request = MagicMock()
        mock_request.build_absolute_uri.return_value = 'http://localhost/api/users/1/avatar/'
        result = build_user_avatar_url(user, request=mock_request)
        mock_request.build_absolute_uri.assert_called_once_with('/api/users/1/avatar/')
        assert result == 'http://localhost/api/users/1/avatar/'

    @patch('accounts.avatar_utils.reverse')
    def test_TC9_branch3_hit_with_updated_at_and_request(self, mock_reverse):
        """
        Tests lines 21–47 (Branch 3 — HIT: sub-branch 3a + 3c).
        Condition: avatar_data truthy, avatar_updated_at set, request provided
        Expected : returns request.build_absolute_uri(path?v=timestamp)
        """
        mock_reverse.return_value = '/api/users/1/avatar/'
        ts = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        user = self._make_user(avatar_url='', avatar_data=b'imagedata', avatar_updated_at=ts)
        mock_request = MagicMock()
        expected_url = f'/api/users/1/avatar/?v={int(ts.timestamp())}'
        mock_request.build_absolute_uri.return_value = f'http://localhost{expected_url}'
        result = build_user_avatar_url(user, request=mock_request)
        mock_request.build_absolute_uri.assert_called_once_with(expected_url)
        assert result == f'http://localhost{expected_url}'

    # ------------------------------------------------------------------
    # Branch 4 — lines 55–64  (avatar field has value → get avatar.url)
    # ------------------------------------------------------------------

    def test_TC10_branch4_hit_avatar_url_no_request(self):
        """
        Tests lines 55–64 (Branch 4 — HIT: sub-branch 4c).
        Condition: avatar_data = None, avatar.url = '/media/avatars/photo.jpg', request = None
        Expected : returns '/media/avatars/photo.jpg'
        """
        mock_avatar = MagicMock()
        mock_avatar.url = '/media/avatars/photo.jpg'
        user = self._make_user(avatar_url='', avatar_data=None, avatar=mock_avatar)
        result = build_user_avatar_url(user, request=None)
        assert result == '/media/avatars/photo.jpg'

    def test_TC11_branch4_hit_avatar_url_with_request(self):
        """
        Tests lines 55–64 (Branch 4 — HIT: sub-branch 4b).
        Condition: avatar_data = None, avatar.url set, request provided
        Expected : returns request.build_absolute_uri(avatar.url)
        """
        mock_avatar = MagicMock()
        mock_avatar.url = '/media/avatars/photo.jpg'
        user = self._make_user(avatar_url='', avatar_data=None, avatar=mock_avatar)
        mock_request = MagicMock()
        mock_request.build_absolute_uri.return_value = 'http://localhost/media/avatars/photo.jpg'
        result = build_user_avatar_url(user, request=mock_request)
        mock_request.build_absolute_uri.assert_called_once_with('/media/avatars/photo.jpg')
        assert result == 'http://localhost/media/avatars/photo.jpg'

    def test_TC12_branch4_hit_avatar_url_raises_value_error(self):
        """
        Tests lines 56–59 (Branch 4 — HIT: sub-branch 4a — ValueError).
        Condition: avatar_data = None, avatar.url raises ValueError (no file associated)
        Expected : returns '' (exception caught and suppressed)
        """
        mock_avatar = MagicMock()
        type(mock_avatar).url = property(lambda self: (_ for _ in ()).throw(ValueError("No file")))
        user = self._make_user(avatar_url='', avatar_data=None, avatar=mock_avatar)
        result = build_user_avatar_url(user, request=None)
        assert result == ''

    def test_TC13_branch4_miss_avatar_none(self):
        """
        Tests lines 55–64 (Branch 4 — MISS: avatar is None/falsy).
        Condition: avatar_data = None, avatar = None → `if avatar` is False
        Expected : execution falls through to Branch 5 → returns ''
        """
        user = self._make_user(avatar_url='', avatar_data=None, avatar=None)
        result = build_user_avatar_url(user)
        assert result == ''

    # ------------------------------------------------------------------
    # Branch 5 — line 66  (nothing available → return '')
    # ------------------------------------------------------------------

    def test_TC14_branch5_hit_all_fields_empty(self):
        """
        Tests line 66 (Branch 5 — HIT).
        Condition: avatar_url='', avatar_data=None, avatar=None → all checks fail
        Expected : returns ''
        """
        user = self._make_user(avatar_url='', avatar_data=None, avatar=None)
        result = build_user_avatar_url(user)
        assert result == ''

    def test_TC15_branch5_hit_no_request_no_avatar_fields(self):
        """
        Tests line 66 (Branch 5 — HIT).
        Condition: user has no avatar-related attributes at all (getattr returns defaults)
        Expected : returns ''
        """
        user = MagicMock(spec=[])  # no attributes defined
        result = build_user_avatar_url(user)
        assert result == ''
