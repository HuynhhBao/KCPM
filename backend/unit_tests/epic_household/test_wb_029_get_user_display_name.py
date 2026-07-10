from types import SimpleNamespace

from households.views import get_user_display_name


def test_wb029_01_virtual_user_has_full_name():
    user = SimpleNamespace(
        email="a@virtual.chungvi.local",
        full_name="Nguyễn An"
    )

    result = get_user_display_name(user)

    assert result == "Nguyễn An"


def test_wb029_02_virtual_user_without_full_name_returns_default_name():
    user = SimpleNamespace(
        email="a@virtual.chungvi.local",
        full_name=""
    )

    result = get_user_display_name(user)

    assert result == "Thành viên ảo"


def test_wb029_03_normal_user_has_full_name():
    user = SimpleNamespace(
        email="normal@gmail.com",
        full_name="Trần Bình"
    )

    result = get_user_display_name(user)

    assert result == "Trần Bình"


def test_wb029_04_normal_user_without_full_name_returns_email():
    user = SimpleNamespace(
        email="normal@gmail.com",
        full_name=""
    )

    result = get_user_display_name(user)

    assert result == "normal@gmail.com"