#WB 061
import pytest
from decimal import Decimal
from rest_framework import serializers
from expenses.serializers import ExpenseCreateUpdateSerializer
from expenses.models import Expense


@pytest.fixture
def serializer():
    return ExpenseCreateUpdateSerializer()


def make_user_map(*user_ids):
    """Helper tạo users_by_id giả lập, chỉ cần key tồn tại cho _build_split_items."""
    return {uid: f'user_{uid}' for uid in user_ids}


# ── TC_WB061_01: D2-True — MANUAL, thiếu share_amount ──
def test_build_split_items_manual_missing_share_amount_raises(serializer):
    with pytest.raises(serializers.ValidationError):
        serializer._build_split_items(
            amount=Decimal('100000'),
            split_type=Expense.SplitType.MANUAL,
            participants=[{'user_id': 1}],  # thiếu key 'share_amount'
            users_by_id=make_user_map(1),
        )


# ── TC_WB061_02: D3-True — MANUAL, share_amount <= 0 (boundary) ──
def test_build_split_items_manual_zero_share_amount_raises(serializer):
    with pytest.raises(serializers.ValidationError):
        serializer._build_split_items(
            amount=Decimal('100000'),
            split_type=Expense.SplitType.MANUAL,
            participants=[{'user_id': 1, 'share_amount': Decimal('0')}],
            users_by_id=make_user_map(1),
        )


# ── TC_WB061_03: D4-True — MANUAL, tổng share khác amount ──
def test_build_split_items_manual_total_mismatch_raises(serializer):
    with pytest.raises(serializers.ValidationError):
        serializer._build_split_items(
            amount=Decimal('100000'),
            split_type=Expense.SplitType.MANUAL,
            participants=[{'user_id': 1, 'share_amount': Decimal('50000')}],
            users_by_id=make_user_map(1),
        )


# ── TC_WB061_04: D4-False — MANUAL, happy path, nhiều participants ──
def test_build_split_items_manual_happy_path(serializer):
    participants = [
        {'user_id': 1, 'share_amount': Decimal('40000')},
        {'user_id': 2, 'share_amount': Decimal('30000')},
        {'user_id': 3, 'share_amount': Decimal('30000')},
    ]
    result = serializer._build_split_items(
        amount=Decimal('100000'),
        split_type=Expense.SplitType.MANUAL,
        participants=participants,
        users_by_id=make_user_map(1, 2, 3),
    )
    assert len(result) == 3
    assert result[0] == ('user_1', Decimal('40000'))


# ── TC_WB061_05: D1-False (EQUAL), chia có dư, dư về index 0 ──
def test_build_split_items_equal_with_remainder(serializer):
    participants = [{'user_id': i} for i in (1, 2, 3)]
    result = serializer._build_split_items(
        amount=Decimal('100'),
        split_type=Expense.SplitType.EQUAL,
        participants=participants,
        users_by_id=make_user_map(1, 2, 3),
    )
    # 100 // 3 = 33, remainder = 1 -> index 0 nhận 33+1=34, còn lại 33
    assert result[0][1] == Decimal('34')
    assert result[1][1] == Decimal('33')
    assert result[2][1] == Decimal('33')


# ── TC_WB061_06: D1-False (EQUAL), chia chẵn tuyệt đối (remainder=0) ──
def test_build_split_items_equal_no_remainder(serializer):
    participants = [{'user_id': i} for i in (1, 2, 3)]
    result = serializer._build_split_items(
        amount=Decimal('300'),
        split_type=Expense.SplitType.EQUAL,
        participants=participants,
        users_by_id=make_user_map(1, 2, 3),
    )
    assert all(share == Decimal('100') for _, share in result)


# ── TC_WB061_07: D1-False (EQUAL), chỉ 1 participant ──
def test_build_split_items_equal_single_participant(serializer):
    result = serializer._build_split_items(
        amount=Decimal('100000'),
        split_type=Expense.SplitType.EQUAL,
        participants=[{'user_id': 1}],
        users_by_id=make_user_map(1),
    )
    assert len(result) == 1
    assert result[0][1] == Decimal('100000')