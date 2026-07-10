"""
WB_055 — get_user_display_name (module-level function)
expenses-service

is_virtual_user(user) chỉ kiểm tra hậu tố email ('@virtual.chungvi.local') -> không
cần DB thật, dùng SimpleNamespace(full_name=..., email=...) để giả lập user.

CFG:
  N1: Điều kiện D1 — is_virtual_user(user)
      True  -> N2
      False -> N5
  N2: Điều kiện D2 (lồng trong D1-True)  — user.full_name
      True  -> N3 (return user.full_name)
      False -> N4 (return 'Thành viên ảo')
  N5: Điều kiện D3 (lồng trong D1-False) — user.full_name
      True  -> N6 (return user.full_name)
      False -> N7 (return user.email)

V(G) = 3 decision points (D1, D2, D3) + 1 = 4 -> 4 TC, mỗi TC ứng đúng 1 tổ hợp lồng.
"""
from types import SimpleNamespace

from expenses.serializers import get_user_display_name

VIRTUAL_EMAIL = 'ghost@virtual.chungvi.local'
REAL_EMAIL = 'thanh@example.com'


# ── TC_WB055_01: D1-True, D2-True (virtual user, có full_name) ──
def test_get_user_display_name_virtual_user_with_full_name():
    user = SimpleNamespace(email=VIRTUAL_EMAIL, full_name='Thành viên A')

    result = get_user_display_name(user)

    assert result == 'Thành viên A'


# ── TC_WB055_02: D1-True, D2-False (virtual user, không có full_name) ──
def test_get_user_display_name_virtual_user_without_full_name():
    user = SimpleNamespace(email=VIRTUAL_EMAIL, full_name='')

    result = get_user_display_name(user)

    assert result == 'Thành viên ảo'


# ── TC_WB055_03: D1-False, D3-True (user thật, có full_name) ──
def test_get_user_display_name_real_user_with_full_name():
    user = SimpleNamespace(email=REAL_EMAIL, full_name='Nguyễn Văn Thanh')

    result = get_user_display_name(user)

    assert result == 'Nguyễn Văn Thanh'


# ── TC_WB055_04: D1-False, D3-False (user thật, không có full_name) ──
def test_get_user_display_name_real_user_without_full_name():
    user = SimpleNamespace(email=REAL_EMAIL, full_name='')

    result = get_user_display_name(user)

    assert result == REAL_EMAIL