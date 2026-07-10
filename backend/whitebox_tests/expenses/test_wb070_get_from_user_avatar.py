"""
WB_070 — DebtSerializer.get_from_user_avatar
expenses-service
"""
from types import SimpleNamespace

from expenses.serializers import DebtSerializer


def make_debt(avatar):
    return SimpleNamespace(from_user=SimpleNamespace(avatar=avatar))


# ── TC_WB070_01: N2-True (có avatar và có request) ──
def test_get_from_user_avatar_returns_absolute_uri_when_avatar_and_request():
    avatar = SimpleNamespace(url='/media/avatar.jpg')
    obj = make_debt(avatar=avatar)
    request = SimpleNamespace(
        build_absolute_uri=lambda url: f'http://testserver{url}'
    )
    serializer = DebtSerializer(context={'request': request})

    result = serializer.get_from_user_avatar(obj)

    assert result == 'http://testserver/media/avatar.jpg'


# ── TC_WB070_02: N2-False (không có avatar, short-circuit) ──
def test_get_from_user_avatar_returns_empty_when_no_avatar():
    obj = make_debt(avatar=None)
    request = SimpleNamespace(build_absolute_uri=lambda url: f'http://testserver{url}')
    serializer = DebtSerializer(context={'request': request})

    result = serializer.get_from_user_avatar(obj)

    assert result == ''


# ── TC_WB070_03: N2-False (có avatar nhưng không có request) ──
def test_get_from_user_avatar_returns_empty_when_no_request():
    avatar = SimpleNamespace(url='/media/avatar.jpg')
    obj = make_debt(avatar=avatar)
    serializer = DebtSerializer(context={})

    result = serializer.get_from_user_avatar(obj)

    assert result == ''