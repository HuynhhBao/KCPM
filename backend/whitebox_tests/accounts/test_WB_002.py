import pytest
import requests as pyrequests
from unittest.mock import patch, Mock
from accounts.views import request_google_json, GoogleProviderUnavailableError, GoogleTokenInvalidError

def test_wb_002_branch_1_timeout_or_connection_error():
    with patch('accounts.views.pyrequests.get') as mock_get:
        mock_get.side_effect = pyrequests.Timeout('Timeout error')
        with pytest.raises(GoogleProviderUnavailableError):
            request_google_json('http://test.url', params={})

def test_wb_002_branch_2_invalid_token_status():
    with patch('accounts.views.pyrequests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 401
        http_error = pyrequests.HTTPError('Unauthorized')
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response
        with pytest.raises(GoogleTokenInvalidError):
            request_google_json('http://test.url', params={})

def test_wb_002_branch_3_other_http_error():
    with patch('accounts.views.pyrequests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = pyrequests.HTTPError('HTTP error')
        mock_get.return_value = mock_response
        with pytest.raises(GoogleProviderUnavailableError):
            request_google_json('http://test.url', params={})

def test_wb_002_branch_4_json_parse_error():
    with patch('accounts.views.pyrequests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError('Invalid JSON')
        mock_get.return_value = mock_response
        with pytest.raises(GoogleProviderUnavailableError):
            request_google_json('http://test.url', params={})

def test_wb_002_branch_5_success():
    with patch('accounts.views.pyrequests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        mock_get.return_value = mock_response
        result = request_google_json('http://test.url', params={})
        assert result == {'data': 'test'}
