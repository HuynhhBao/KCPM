import pytest
from unittest.mock import patch
import accounts.cloudinary_storage as cloudinary_storage_module
from accounts.cloudinary_storage import configure_cloudinary


class TestConfigureCloudinary:
    """
    White-box tests for configure_cloudinary() — lines 15–58 (cloudinary_storage.py)

    Covers:
      - Branch 1 (lines 18–19): _CLOUDINARY_CONFIGURED is True  → return immediately
      - Branch 2 (lines 36–39): cloud_name is empty             → raise RuntimeError('Thiếu biến môi trường CLOUDINARY_CLOUD_NAME')
      - Branch 3 (lines 41–44): api_key is empty                → raise RuntimeError('Thiếu biến môi trường CLOUDINARY_API_KEY')
      - Branch 4 (lines 46–49): api_secret is empty             → raise RuntimeError('Thiếu biến môi trường CLOUDINARY_API_SECRET')
      - Happy path (lines 51–58): all 3 values present          → cloudinary.config called; _CLOUDINARY_CONFIGURED set True
    """

    def setup_method(self):
        """Reset the global flag before each test."""
        cloudinary_storage_module._CLOUDINARY_CONFIGURED = False

    # ------------------------------------------------------------------
    # Branch 1 — lines 18–19  (_CLOUDINARY_CONFIGURED is True → return)
    # ------------------------------------------------------------------

    @patch('accounts.cloudinary_storage.cloudinary.config')
    def test_TC1_branch1_hit_already_configured(self, mock_cloudinary_config):
        """
        Tests lines 18–19 (Branch 1 — HIT).
        Condition: _CLOUDINARY_CONFIGURED = True before call
        Expected : returns immediately; cloudinary.config NOT called
        """
        cloudinary_storage_module._CLOUDINARY_CONFIGURED = True
        configure_cloudinary()
        mock_cloudinary_config.assert_not_called()

    @patch('accounts.cloudinary_storage.cloudinary.config')
    def test_TC2_branch1_miss_not_yet_configured(self, mock_cloudinary_config):
        """
        Tests lines 18–19 (Branch 1 — MISS).
        Condition: _CLOUDINARY_CONFIGURED = False → branch not taken; execution continues
        Expected : proceeds past the early-return check
        """
        cloudinary_storage_module._CLOUDINARY_CONFIGURED = False
        # Provide all valid env vars so it doesn't raise
        with patch('accounts.cloudinary_storage.config', side_effect=lambda key, default='': {
            'CLOUDINARY_CLOUD_NAME': 'mycloud',
            'CLOUDINARY_API_KEY': 'mykey',
            'CLOUDINARY_API_SECRET': 'mysecret',
        }.get(key, default)):
            configure_cloudinary()
        mock_cloudinary_config.assert_called_once()

    # ------------------------------------------------------------------
    # Branch 2 — lines 36–39  (cloud_name empty → RuntimeError)
    # ------------------------------------------------------------------

    def test_TC3_branch2_hit_cloud_name_missing(self):
        """
        Tests lines 36–39 (Branch 2 — HIT).
        Condition: CLOUDINARY_CLOUD_NAME = '' (not set)
        Expected : RuntimeError('Thiếu biến môi trường CLOUDINARY_CLOUD_NAME')
        """
        with patch('accounts.cloudinary_storage.config', side_effect=lambda key, default='': {
            'CLOUDINARY_CLOUD_NAME': '',
            'CLOUDINARY_API_KEY': 'mykey',
            'CLOUDINARY_API_SECRET': 'mysecret',
        }.get(key, default)):
            with pytest.raises(RuntimeError) as exc_info:
                configure_cloudinary()
        assert str(exc_info.value) == 'Thiếu biến môi trường CLOUDINARY_CLOUD_NAME'

    def test_TC4_branch2_hit_cloud_name_whitespace_only(self):
        """
        Tests lines 21–39 (Branch 2 — HIT: whitespace stripped to empty).
        Condition: CLOUDINARY_CLOUD_NAME = '   ' → after strip() = ''
        Expected : RuntimeError('Thiếu biến môi trường CLOUDINARY_CLOUD_NAME')
        """
        with patch('accounts.cloudinary_storage.config', side_effect=lambda key, default='': {
            'CLOUDINARY_CLOUD_NAME': '   ',
            'CLOUDINARY_API_KEY': 'mykey',
            'CLOUDINARY_API_SECRET': 'mysecret',
        }.get(key, default)):
            with pytest.raises(RuntimeError) as exc_info:
                configure_cloudinary()
        assert str(exc_info.value) == 'Thiếu biến môi trường CLOUDINARY_CLOUD_NAME'

    def test_TC5_branch2_miss_cloud_name_present(self):
        """
        Tests lines 36–39 (Branch 2 — MISS).
        Condition: CLOUDINARY_CLOUD_NAME = 'mycloud' → not empty → branch not taken
        Expected : no RuntimeError for cloud_name; execution continues to api_key check
        """
        with patch('accounts.cloudinary_storage.config', side_effect=lambda key, default='': {
            'CLOUDINARY_CLOUD_NAME': 'mycloud',
            'CLOUDINARY_API_KEY': '',
            'CLOUDINARY_API_SECRET': '',
        }.get(key, default)):
            with pytest.raises(RuntimeError) as exc_info:
                configure_cloudinary()
        # Should fail on api_key, not cloud_name
        assert str(exc_info.value) == 'Thiếu biến môi trường CLOUDINARY_API_KEY'

    # ------------------------------------------------------------------
    # Branch 3 — lines 41–44  (api_key empty → RuntimeError)
    # ------------------------------------------------------------------

    def test_TC6_branch3_hit_api_key_missing(self):
        """
        Tests lines 41–44 (Branch 3 — HIT).
        Condition: cloud_name present, CLOUDINARY_API_KEY = ''
        Expected : RuntimeError('Thiếu biến môi trường CLOUDINARY_API_KEY')
        """
        with patch('accounts.cloudinary_storage.config', side_effect=lambda key, default='': {
            'CLOUDINARY_CLOUD_NAME': 'mycloud',
            'CLOUDINARY_API_KEY': '',
            'CLOUDINARY_API_SECRET': 'mysecret',
        }.get(key, default)):
            with pytest.raises(RuntimeError) as exc_info:
                configure_cloudinary()
        assert str(exc_info.value) == 'Thiếu biến môi trường CLOUDINARY_API_KEY'

    def test_TC7_branch3_hit_api_key_whitespace_only(self):
        """
        Tests lines 26–44 (Branch 3 — HIT: whitespace stripped to empty).
        Condition: CLOUDINARY_API_KEY = '   ' → after strip() = ''
        Expected : RuntimeError('Thiếu biến môi trường CLOUDINARY_API_KEY')
        """
        with patch('accounts.cloudinary_storage.config', side_effect=lambda key, default='': {
            'CLOUDINARY_CLOUD_NAME': 'mycloud',
            'CLOUDINARY_API_KEY': '   ',
            'CLOUDINARY_API_SECRET': 'mysecret',
        }.get(key, default)):
            with pytest.raises(RuntimeError) as exc_info:
                configure_cloudinary()
        assert str(exc_info.value) == 'Thiếu biến môi trường CLOUDINARY_API_KEY'

    def test_TC8_branch3_miss_api_key_present(self):
        """
        Tests lines 41–44 (Branch 3 — MISS).
        Condition: cloud_name + api_key present, api_secret = '' → branch 3 not taken
        Expected : no RuntimeError for api_key; execution continues to api_secret check
        """
        with patch('accounts.cloudinary_storage.config', side_effect=lambda key, default='': {
            'CLOUDINARY_CLOUD_NAME': 'mycloud',
            'CLOUDINARY_API_KEY': 'mykey',
            'CLOUDINARY_API_SECRET': '',
        }.get(key, default)):
            with pytest.raises(RuntimeError) as exc_info:
                configure_cloudinary()
        assert str(exc_info.value) == 'Thiếu biến môi trường CLOUDINARY_API_SECRET'

    # ------------------------------------------------------------------
    # Branch 4 — lines 46–49  (api_secret empty → RuntimeError)
    # ------------------------------------------------------------------

    def test_TC9_branch4_hit_api_secret_missing(self):
        """
        Tests lines 46–49 (Branch 4 — HIT).
        Condition: cloud_name + api_key present, CLOUDINARY_API_SECRET = ''
        Expected : RuntimeError('Thiếu biến môi trường CLOUDINARY_API_SECRET')
        """
        with patch('accounts.cloudinary_storage.config', side_effect=lambda key, default='': {
            'CLOUDINARY_CLOUD_NAME': 'mycloud',
            'CLOUDINARY_API_KEY': 'mykey',
            'CLOUDINARY_API_SECRET': '',
        }.get(key, default)):
            with pytest.raises(RuntimeError) as exc_info:
                configure_cloudinary()
        assert str(exc_info.value) == 'Thiếu biến môi trường CLOUDINARY_API_SECRET'

    def test_TC10_branch4_hit_api_secret_whitespace_only(self):
        """
        Tests lines 31–49 (Branch 4 — HIT: whitespace stripped to empty).
        Condition: CLOUDINARY_API_SECRET = '   ' → after strip() = ''
        Expected : RuntimeError('Thiếu biến môi trường CLOUDINARY_API_SECRET')
        """
        with patch('accounts.cloudinary_storage.config', side_effect=lambda key, default='': {
            'CLOUDINARY_CLOUD_NAME': 'mycloud',
            'CLOUDINARY_API_KEY': 'mykey',
            'CLOUDINARY_API_SECRET': '   ',
        }.get(key, default)):
            with pytest.raises(RuntimeError) as exc_info:
                configure_cloudinary()
        assert str(exc_info.value) == 'Thiếu biến môi trường CLOUDINARY_API_SECRET'

    def test_TC11_branch4_miss_api_secret_present(self):
        """
        Tests lines 46–49 (Branch 4 — MISS).
        Condition: all 3 values present → branch 4 not taken
        Expected : no RuntimeError; cloudinary.config called; _CLOUDINARY_CONFIGURED = True
        """
        with patch('accounts.cloudinary_storage.config', side_effect=lambda key, default='': {
            'CLOUDINARY_CLOUD_NAME': 'mycloud',
            'CLOUDINARY_API_KEY': 'mykey',
            'CLOUDINARY_API_SECRET': 'mysecret',
        }.get(key, default)):
            with patch('accounts.cloudinary_storage.cloudinary.config') as mock_cloudinary_config:
                configure_cloudinary()
        mock_cloudinary_config.assert_called_once_with(
            cloud_name='mycloud',
            api_key='mykey',
            api_secret='mysecret',
            secure=True,
        )

    # ------------------------------------------------------------------
    # Happy path — lines 51–58  (all values present → configure + set flag)
    # ------------------------------------------------------------------

    @patch('accounts.cloudinary_storage.cloudinary.config')
    def test_TC12_happy_path_all_values_present(self, mock_cloudinary_config):
        """
        Tests lines 51–58 (Happy path).
        Condition: all 3 env vars set with valid values
        Expected : cloudinary.config called with correct args; _CLOUDINARY_CONFIGURED set to True
        """
        with patch('accounts.cloudinary_storage.config', side_effect=lambda key, default='': {
            'CLOUDINARY_CLOUD_NAME': 'mycloudname',
            'CLOUDINARY_API_KEY': 'myapikey123',
            'CLOUDINARY_API_SECRET': 'myapisecret456',
        }.get(key, default)):
            configure_cloudinary()

        mock_cloudinary_config.assert_called_once_with(
            cloud_name='mycloudname',
            api_key='myapikey123',
            api_secret='myapisecret456',
            secure=True,
        )
        assert cloudinary_storage_module._CLOUDINARY_CONFIGURED is True

    @patch('accounts.cloudinary_storage.cloudinary.config')
    def test_TC13_happy_path_idempotent_second_call_skipped(self, mock_cloudinary_config):
        """
        Tests lines 18–19 + 51–58 (Happy path — idempotency).
        Condition: configure_cloudinary() called twice; second call should be no-op
        Expected : cloudinary.config called exactly once (first call only)
        """
        with patch('accounts.cloudinary_storage.config', side_effect=lambda key, default='': {
            'CLOUDINARY_CLOUD_NAME': 'mycloudname',
            'CLOUDINARY_API_KEY': 'myapikey123',
            'CLOUDINARY_API_SECRET': 'myapisecret456',
        }.get(key, default)):
            configure_cloudinary()
            configure_cloudinary()  # second call — should be skipped

        mock_cloudinary_config.assert_called_once()
