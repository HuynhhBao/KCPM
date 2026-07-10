"""
WB_108 — DebtSerializer.get_has_virtual_member
expenses-service

get_from_user_is_virtual / get_to_user_is_virtual không có mã WB riêng và chỉ
delegate 1 dòng (return is_virtual_user(obj.from_user/to_user)) -> mock trực tiếp
qua patch.object, không cần dựng obj/User thật trong DB.

CFG:
  N1: Điều kiện (or) — self.get_from_user_is_virtual(obj)
      True  -> N2 (return True, short-circuit — to_user KHÔNG được kiểm tra)
      False -> N3 (return self.get_to_user_is_virtual(obj))

V(G) = 1 decision point + 1 = 2. "or" có 2 atomic condition (from_user_is_virtual,
to_user_is_virtual) nên cần 3 TC để đủ Condition Coverage: TC_01 (A=True, short-circuit),
TC_02 (A=False, B=True), TC_03 (A=False, B=False).
"""
from unittest.mock import patch

from expenses.serializers import DebtSerializer


# ── TC_WB108_01: N1-True (from_user là virtual, short-circuit) ──
def test_get_has_virtual_member_true_when_from_user_virtual():
    serializer = DebtSerializer()

    with patch.object(DebtSerializer, 'get_from_user_is_virtual', return_value=True), \
         patch.object(DebtSerializer, 'get_to_user_is_virtual') as mock_to_user:
        result = serializer.get_has_virtual_member(obj=None)

        mock_to_user.assert_not_called()  # short-circuit: to_user không được gọi

    assert result is True


# ── TC_WB108_02: N1-False, to_user là virtual ──
def test_get_has_virtual_member_true_when_to_user_virtual():
    serializer = DebtSerializer()

    with patch.object(DebtSerializer, 'get_from_user_is_virtual', return_value=False), \
         patch.object(DebtSerializer, 'get_to_user_is_virtual', return_value=True):
        result = serializer.get_has_virtual_member(obj=None)

    assert result is True


# ── TC_WB108_03: N1-False, không ai là virtual ──
def test_get_has_virtual_member_false_when_neither_virtual():
    serializer = DebtSerializer()

    with patch.object(DebtSerializer, 'get_from_user_is_virtual', return_value=False), \
         patch.object(DebtSerializer, 'get_to_user_is_virtual', return_value=False):
        result = serializer.get_has_virtual_member(obj=None)

    assert result is False