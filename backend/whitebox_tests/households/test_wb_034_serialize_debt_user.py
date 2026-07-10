from types import SimpleNamespace
from unittest.mock import patch

from households.views import serialize_debt_user


def test_wb034_01_virtual_user_does_not_get_avatar():
    user = SimpleNamespace(
        id=1,
        email="virtual001@virtual.chungvi.local",
        full_name="Bạn ảo"
    )

    with patch("households.views.build_user_avatar_url") as mock_avatar:
        result = serialize_debt_user(user, request=None)

    assert result["other_avatar"] == ""
    assert result["is_virtual"] is True
    mock_avatar.assert_not_called()


def test_wb034_02_normal_user_gets_avatar():
    user = SimpleNamespace(
        id=2,
        email="normal@gmail.com",
        full_name="Người thật"
    )

    with patch("households.views.build_user_avatar_url", return_value="avatar-url") as mock_avatar:
        result = serialize_debt_user(user, request=None)

    assert result["other_avatar"] == "avatar-url"
    assert result["is_virtual"] is False
    mock_avatar.assert_called_once()