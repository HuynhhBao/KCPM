from types import SimpleNamespace
from unittest.mock import patch

from households.views import serialize_debt_payer


def test_wb035_01_user_none_returns_default_payer():
    result = serialize_debt_payer(None, request=None)

    assert result["payer_id"] is None
    assert result["payer_name"] == "Không rõ người chi"
    assert result["payer_email"] == ""
    assert result["payer_avatar"] == ""
    assert result["payer_is_virtual"] is False


def test_wb035_02_virtual_user_does_not_get_avatar():
    user = SimpleNamespace(
        id=1,
        email="virtual001@virtual.chungvi.local",
        full_name="Bạn ảo"
    )

    with patch("households.views.build_user_avatar_url") as mock_avatar:
        result = serialize_debt_payer(user, request=None)

    assert result["payer_avatar"] == ""
    assert result["payer_is_virtual"] is True
    mock_avatar.assert_not_called()


def test_wb035_03_normal_user_gets_avatar():
    user = SimpleNamespace(
        id=2,
        email="normal@gmail.com",
        full_name="Người thật"
    )

    with patch("households.views.build_user_avatar_url", return_value="avatar-url") as mock_avatar:
        result = serialize_debt_payer(user, request=None)

    assert result["payer_avatar"] == "avatar-url"
    assert result["payer_is_virtual"] is False
    mock_avatar.assert_called_once()