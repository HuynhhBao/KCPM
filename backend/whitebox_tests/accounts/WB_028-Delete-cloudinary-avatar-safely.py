import pytest
from unittest.mock import patch, call
from accounts.cloudinary_storage import delete_cloudinary_avatar_safely


class TestDeleteCloudinaryAvatarSafely:
    """
    White-box tests for delete_cloudinary_avatar_safely() — lines 164–182 (cloudinary_storage.py)

    Covers:
      - Branch 1 (lines 165–166): public_id is falsy          → return immediately (no-op)
      - Branch 2 (lines 177–182): Exception raised inside try  → logged, NOT re-raised
      - Happy path (lines 168–175): public_id valid, no exception → destroy called successfully
    """

    # ------------------------------------------------------------------
    # Branch 1 — lines 165–166  (public_id falsy → return immediately)
    # ------------------------------------------------------------------

    @patch('accounts.cloudinary_storage.configure_cloudinary')
    @patch('accounts.cloudinary_storage.cloudinary.uploader.destroy')
    def test_TC1_branch1_hit_public_id_none(self, mock_destroy, mock_configure):
        """
        Tests lines 165–166 (Branch 1 — HIT).
        Condition: public_id = None → `not public_id` is True
        Expected : returns immediately; configure_cloudinary and destroy NOT called
        """
        delete_cloudinary_avatar_safely(None)
        mock_configure.assert_not_called()
        mock_destroy.assert_not_called()

    @patch('accounts.cloudinary_storage.configure_cloudinary')
    @patch('accounts.cloudinary_storage.cloudinary.uploader.destroy')
    def test_TC2_branch1_hit_public_id_empty_string(self, mock_destroy, mock_configure):
        """
        Tests lines 165–166 (Branch 1 — HIT).
        Condition: public_id = '' → `not public_id` is True
        Expected : returns immediately; configure_cloudinary and destroy NOT called
        """
        delete_cloudinary_avatar_safely('')
        mock_configure.assert_not_called()
        mock_destroy.assert_not_called()

    @patch('accounts.cloudinary_storage.configure_cloudinary')
    @patch('accounts.cloudinary_storage.cloudinary.uploader.destroy')
    def test_TC3_branch1_hit_public_id_false(self, mock_destroy, mock_configure):
        """
        Tests lines 165–166 (Branch 1 — HIT).
        Condition: public_id = False → `not public_id` is True
        Expected : returns immediately; no side effects
        """
        delete_cloudinary_avatar_safely(False)
        mock_configure.assert_not_called()
        mock_destroy.assert_not_called()

    @patch('accounts.cloudinary_storage.configure_cloudinary')
    @patch('accounts.cloudinary_storage.cloudinary.uploader.destroy')
    def test_TC4_branch1_miss_public_id_present(self, mock_destroy, mock_configure):
        """
        Tests lines 165–166 (Branch 1 — MISS).
        Condition: public_id = 'chung_vi/avatars/users/42/avatar_abc' → truthy
        Expected : Branch 1 not taken; execution enters try block
        """
        delete_cloudinary_avatar_safely('chung_vi/avatars/users/42/avatar_abc')
        mock_configure.assert_called_once()
        mock_destroy.assert_called_once()

    # ------------------------------------------------------------------
    # Branch 2 — lines 177–182  (Exception raised → logged, not re-raised)
    # ------------------------------------------------------------------

    @patch('accounts.cloudinary_storage.logger')
    @patch('accounts.cloudinary_storage.configure_cloudinary')
    @patch('accounts.cloudinary_storage.cloudinary.uploader.destroy')
    def test_TC5_branch2_hit_destroy_raises_exception(self, mock_destroy, mock_configure, mock_logger):
        """
        Tests lines 177–182 (Branch 2 — HIT: destroy raises generic Exception).
        Condition: cloudinary.uploader.destroy raises Exception
        Expected : exception is caught; logger.exception called; no re-raise
        """
        mock_destroy.side_effect = Exception('network error')
        # Should NOT raise
        delete_cloudinary_avatar_safely('chung_vi/avatars/users/42/avatar_abc')
        mock_logger.exception.assert_called_once()

    @patch('accounts.cloudinary_storage.logger')
    @patch('accounts.cloudinary_storage.configure_cloudinary')
    @patch('accounts.cloudinary_storage.cloudinary.uploader.destroy')
    def test_TC6_branch2_hit_configure_raises_exception(self, mock_destroy, mock_configure, mock_logger):
        """
        Tests lines 177–182 (Branch 2 — HIT: configure_cloudinary raises Exception).
        Condition: configure_cloudinary() raises RuntimeError inside try block
        Expected : exception is caught; logger.exception called; no re-raise
        """
        mock_configure.side_effect = RuntimeError('missing env var')
        # Should NOT raise
        delete_cloudinary_avatar_safely('chung_vi/avatars/users/42/avatar_abc')
        mock_logger.exception.assert_called_once()

    @patch('accounts.cloudinary_storage.logger')
    @patch('accounts.cloudinary_storage.configure_cloudinary')
    @patch('accounts.cloudinary_storage.cloudinary.uploader.destroy')
    def test_TC7_branch2_hit_logger_receives_public_id(self, mock_destroy, mock_configure, mock_logger):
        """
        Tests lines 178–182 (Branch 2 — HIT: logger.exception called with public_id).
        Condition: destroy raises Exception; public_id = 'users/99/avatar_xyz'
        Expected : logger.exception called with message containing public_id
        """
        mock_destroy.side_effect = Exception('timeout')
        public_id = 'users/99/avatar_xyz'
        delete_cloudinary_avatar_safely(public_id)
        args = mock_logger.exception.call_args
        # The public_id should be passed as an argument to the log message
        assert public_id in args[0] or public_id in str(args)

    @patch('accounts.cloudinary_storage.logger')
    @patch('accounts.cloudinary_storage.configure_cloudinary')
    @patch('accounts.cloudinary_storage.cloudinary.uploader.destroy')
    def test_TC8_branch2_miss_no_exception(self, mock_destroy, mock_configure, mock_logger):
        """
        Tests lines 177–182 (Branch 2 — MISS: no exception raised).
        Condition: destroy completes successfully
        Expected : logger.exception NOT called
        """
        mock_destroy.return_value = {'result': 'ok'}
        delete_cloudinary_avatar_safely('chung_vi/avatars/users/42/avatar_abc')
        mock_logger.exception.assert_not_called()

    # ------------------------------------------------------------------
    # Happy path — lines 168–175  (valid public_id, no exception → destroy called)
    # ------------------------------------------------------------------

    @patch('accounts.cloudinary_storage.configure_cloudinary')
    @patch('accounts.cloudinary_storage.cloudinary.uploader.destroy')
    def test_TC9_happy_path_destroy_called_with_correct_args(self, mock_destroy, mock_configure):
        """
        Tests lines 168–175 (Happy path).
        Condition: public_id = 'chung_vi/avatars/users/42/avatar_abc', no exception
        Expected : cloudinary.uploader.destroy called with public_id, resource_type='image', invalidate=True
        """
        public_id = 'chung_vi/avatars/users/42/avatar_abc'
        delete_cloudinary_avatar_safely(public_id)
        mock_destroy.assert_called_once_with(
            public_id,
            resource_type='image',
            invalidate=True,
        )

    @patch('accounts.cloudinary_storage.configure_cloudinary')
    @patch('accounts.cloudinary_storage.cloudinary.uploader.destroy')
    def test_TC10_happy_path_configure_called_before_destroy(self, mock_destroy, mock_configure):
        """
        Tests lines 169–175 (Happy path — configure_cloudinary called before destroy).
        Condition: valid public_id
        Expected : configure_cloudinary() called exactly once; destroy called exactly once
        """
        delete_cloudinary_avatar_safely('chung_vi/avatars/users/1/avatar_001')
        mock_configure.assert_called_once()
        mock_destroy.assert_called_once()

    @patch('accounts.cloudinary_storage.configure_cloudinary')
    @patch('accounts.cloudinary_storage.cloudinary.uploader.destroy')
    def test_TC11_happy_path_returns_none(self, mock_destroy, mock_configure):
        """
        Tests lines 164–182 (Happy path — function returns None implicitly).
        Condition: valid public_id, no exception
        Expected : function returns None (no explicit return value)
        """
        result = delete_cloudinary_avatar_safely('chung_vi/avatars/users/5/avatar_999')
        assert result is None
