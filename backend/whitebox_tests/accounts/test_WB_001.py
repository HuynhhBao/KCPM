# pyrefly: ignore [missing-import]
import pytest
from unittest.mock import patch
from accounts.views import consume_cached_otp, OTP_MAX_ATTEMPTS

def test_wb_001_branch_1_cached_otp_not_exists():
    with patch('accounts.views.cache.get') as mock_get:
        mock_get.return_value = None
        result = consume_cached_otp(
            otp_key='otp_key',
            attempts_key='attempts_key',
            submitted_otp='123456'
        )
        assert result is False

def test_wb_001_branch_2_attempts_not_int():
    with patch('accounts.views.cache.get') as mock_get, \
         patch('accounts.views.cache.set') as mock_set:
        def mock_get_side_effect(key, default=None):
            if key == 'otp_key':
                return '123456'
            if key == 'attempts_key':
                return 'not_int_value'
            return default
        mock_get.side_effect = mock_get_side_effect
        
        result = consume_cached_otp(
            otp_key='otp_key',
            attempts_key='attempts_key',
            submitted_otp='654321'
        )
        assert result is False
        mock_set.assert_called_once()
        assert mock_set.call_args[0][1] == 1

def test_wb_001_branch_3_attempts_maxed_out():
    with patch('accounts.views.cache.get') as mock_get, \
         patch('accounts.views.cache.delete') as mock_delete:
        def mock_get_side_effect(key, default=None):
            if key == 'otp_key':
                return '123456'
            if key == 'attempts_key':
                return OTP_MAX_ATTEMPTS
            return default
        mock_get.side_effect = mock_get_side_effect
        
        result = consume_cached_otp(
            otp_key='otp_key',
            attempts_key='attempts_key',
            submitted_otp='123456'
        )
        assert result is False
        assert mock_delete.call_count == 2

def test_wb_001_branch_4_wrong_otp():
    with patch('accounts.views.cache.get') as mock_get, \
         patch('accounts.views.cache.set') as mock_set, \
         patch('accounts.views.cache.delete') as mock_delete:
        def mock_get_side_effect(key, default=None):
            if key == 'otp_key':
                return '123456'
            if key == 'attempts_key':
                return OTP_MAX_ATTEMPTS - 1
            return default
        mock_get.side_effect = mock_get_side_effect
        
        result = consume_cached_otp(
            otp_key='otp_key',
            attempts_key='attempts_key',
            submitted_otp='654321'
        )
        assert result is False
        assert mock_set.call_count == 1
        assert mock_delete.call_count == 1
        assert mock_delete.call_args[0][0] == 'otp_key'

def test_wb_001_branch_5_correct_otp():
    with patch('accounts.views.cache.get') as mock_get, \
         patch('accounts.views.cache.delete') as mock_delete:
        def mock_get_side_effect(key, default=None):
            if key == 'otp_key':
                return '123456'
            if key == 'attempts_key':
                return 1
            return default
        mock_get.side_effect = mock_get_side_effect
        
        result = consume_cached_otp(
            otp_key='otp_key',
            attempts_key='attempts_key',
            submitted_otp='123456'
        )
        assert result is True
        assert mock_delete.call_count == 2
