#WB 063
from unittest.mock import MagicMock
from expenses.serializers import ExpenseListSerializer


def make_serializer(request=None):
    context = {'request': request} if request is not None else {}
    return ExpenseListSerializer(context=context)


def make_obj(has_avatar=True):
    obj = MagicMock()
    obj.payer.avatar = MagicMock() if has_avatar else None
    if has_avatar:
        obj.payer.avatar.url = '/media/avatar.jpg'
    return obj


# ── TC_WB063_01: D1-True — avatar + request đều có ──
def test_get_payer_avatar_returns_absolute_uri():
    mock_request = MagicMock()
    mock_request.build_absolute_uri.return_value = 'http://testserver/media/avatar.jpg'
    serializer = make_serializer(request=mock_request)
    result = serializer.get_payer_avatar(make_obj(has_avatar=True))
    assert result == 'http://testserver/media/avatar.jpg'
    mock_request.build_absolute_uri.assert_called_once_with('/media/avatar.jpg')


# ── TC_WB063_02: D1-False (C1=False) — payer không có avatar ──
def test_get_payer_avatar_no_avatar_returns_empty():
    mock_request = MagicMock()
    serializer = make_serializer(request=mock_request)
    result = serializer.get_payer_avatar(make_obj(has_avatar=False))
    assert result == ''


# ── TC_WB063_03: D1-False (C2=False) — request là None ──
def test_get_payer_avatar_no_request_returns_empty():
    serializer = make_serializer(request=None)
    result = serializer.get_payer_avatar(make_obj(has_avatar=True))
    assert result == ''