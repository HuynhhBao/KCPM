# pyrefly: ignore [missing-import]
import pytest
from rest_framework.exceptions import ValidationError
from accounts.serializers import validate_password_strength

def test_wb_014_branch_no_uppercase():
    with pytest.raises(ValidationError):
        validate_password_strength('nouppercase1!')

def test_wb_014_branch_no_digit():
    with pytest.raises(ValidationError):
        validate_password_strength('NoDigitPassword!')

def test_wb_014_branch_success():
    assert validate_password_strength('ValidPass123!') == 'ValidPass123!'
