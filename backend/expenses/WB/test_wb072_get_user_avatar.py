"""
WB_072 — ExpenseParticipantSerializer.get_user_avatar
expenses-service
"""
from types import SimpleNamespace

from expenses.serializers import ExpenseParticipantSerializer


def make_participant(avatar):
    return SimpleNamespace(user=SimpleNamespace(avatar=avatar))


# ── TC_WB072_01: N2-True (có avatar và có request) ──
def test_get_user_avatar_returns_absolute_uri_when_avatar_and_request():
    avatar = SimpleNamespace(url='/media/avatar.jpg')
    obj = make_participant(avatar=avatar)
    request = SimpleNamespace(
        build_absolute_uri=lambda url: f'http://testserver{url}'
    )
    serializer = ExpenseParticipantSerializer(context={'request': request})

    result = serializer.get_user_avatar(obj)

    assert result == 'http://testserver/media/avatar.jpg'


# ── TC_WB072_02: N2-False (không có avatar, short-circuit) ──
def test_get_user_avatar_returns_empty_when_no_avatar():
    obj = make_participant(avatar=None)
    request = SimpleNamespace(build_absolute_uri=lambda url: f'http://testserver{url}')
    serializer = ExpenseParticipantSerializer(context={'request': request})

    result = serializer.get_user_avatar(obj)

    assert result == ''


# ── TC_WB072_03: N2-False (có avatar nhưng không có request) ──
def test_get_user_avatar_returns_empty_when_no_request():
    avatar = SimpleNamespace(url='/media/avatar.jpg')
    obj = make_participant(avatar=avatar)
    serializer = ExpenseParticipantSerializer(context={})

    result = serializer.get_user_avatar(obj)

    assert result == ''