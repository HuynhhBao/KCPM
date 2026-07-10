# pyrefly: ignore [missing-import]
import pytest
from unittest.mock import patch
from accounts.views import get_google_identity, GoogleProviderUnavailableError, GoogleTokenInvalidError

def test_wb_003_branch_1_no_client_id():
    with patch('accounts.views.settings') as mock_settings, \
         patch('accounts.views.os.getenv') as mock_getenv:
        mock_settings.GOOGLE_CLIENT_ID = ''
        mock_settings.GOOGLE_WEB_CLIENT_ID = ''
        mock_getenv.return_value = ''
        
        with pytest.raises(GoogleProviderUnavailableError):
            get_google_identity('test_token')

def test_wb_003_branch_2_verify_token_fails_audience_mismatch():
    with patch('accounts.views.settings') as mock_settings, \
         patch('accounts.views.id_token.verify_oauth2_token') as mock_verify, \
         patch('accounts.views.request_google_json') as mock_request:
        mock_settings.GOOGLE_CLIENT_ID = 'valid_id'
        mock_verify.side_effect = ValueError('Invalid token')
        mock_request.return_value = {'audience': 'invalid_id'}
        with pytest.raises(GoogleTokenInvalidError):
            get_google_identity('test_token')

def test_wb_003_branch_3_empty_email():
    with patch('accounts.views.settings') as mock_settings, \
         patch('accounts.views.id_token.verify_oauth2_token') as mock_verify:
        mock_settings.GOOGLE_CLIENT_ID = 'valid_id'
        mock_verify.return_value = {'email': '', 'email_verified': True}
        with pytest.raises(GoogleTokenInvalidError):
            get_google_identity('test_token')

def test_wb_003_branch_4_email_not_verified():
    with patch('accounts.views.settings') as mock_settings, \
         patch('accounts.views.id_token.verify_oauth2_token') as mock_verify:
        mock_settings.GOOGLE_CLIENT_ID = 'valid_id'
        mock_verify.return_value = {'email': 'test@example.com', 'verified_email': False}
        with pytest.raises(GoogleTokenInvalidError):
            get_google_identity('test_token')

def test_wb_003_branch_5_success():
    with patch('accounts.views.settings') as mock_settings, \
         patch('accounts.views.id_token.verify_oauth2_token') as mock_verify:
        mock_settings.GOOGLE_CLIENT_ID = 'valid_id'
        mock_verify.return_value = {'email': 'test@example.com', 'email_verified': True, 'name': 'User Name'}
        result = get_google_identity('test_token')
        assert result == {'email': 'test@example.com', 'full_name': 'User Name'}
