import pytest
from payments.views import get_user_display_name
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_wb085_tc01_real_user_with_name():
    user = User(email="test@test.com", full_name="John Doe")
    assert get_user_display_name(user) == "John Doe"

@pytest.mark.django_db
def test_wb085_tc02_virtual_user_without_name():
    user = User(email="virtual@virtual.chungvi.local", full_name="")
    assert get_user_display_name(user) == "Thành viên ảo"

@pytest.mark.django_db
def test_wb085_tc03_real_user_without_name():
    user = User(email="test@test.com", full_name="")
    assert get_user_display_name(user) == "test@test.com"
