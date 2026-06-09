from rest_framework import serializers
import uuid

from payments.models import Payment, PaymentAllocation
from decimal import Decimal


VIRTUAL_MEMBER_EMAIL_DOMAIN = '@virtual.chungvi.local'


def is_virtual_user(user):
    email = (getattr(user, 'email', '') or '').lower()
    return email.endswith(VIRTUAL_MEMBER_EMAIL_DOMAIN)


def get_user_display_name(user):
    if is_virtual_user(user):
        return user.full_name or 'Thành viên ảo'

    return user.full_name or user.email


class PaymentActionSerializer(serializers.Serializer):
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500
    )

class PairPaymentCreateSerializer(serializers.Serializer):
    receiver_id = serializers.IntegerField()

    payment_mode = serializers.ChoiceField(
        choices=[
            Payment.Mode.FULL,
            Payment.Mode.SELECTED_ITEMS,
            Payment.Mode.CUSTOM_AMOUNT,
        ],
        default=Payment.Mode.CUSTOM_AMOUNT,
    )

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=0,
        required=False,
    )

    debt_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=False,
    )

    note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
    )

    def validate(self, attrs):
        payment_mode = attrs.get(
            'payment_mode',
            Payment.Mode.CUSTOM_AMOUNT,
        )

        amount = attrs.get('amount')
        debt_ids = attrs.get('debt_ids')

        if payment_mode == Payment.Mode.CUSTOM_AMOUNT:
            if amount is None:
                raise serializers.ValidationError(
                    {
                        'amount':
                        'Vui lòng nhập số tiền muốn thanh toán trước.'
                    }
                )

            if amount <= Decimal('0'):
                raise serializers.ValidationError(
                    {
                        'amount':
                        'Số tiền thanh toán phải lớn hơn 0.'
                    }
                )

        elif payment_mode == Payment.Mode.SELECTED_ITEMS:
            if not debt_ids:
                raise serializers.ValidationError(
                    {
                        'debt_ids':
                        'Vui lòng chọn ít nhất một khoản cần thanh toán.'
                    }
                )

        return attrs

class VirtualReceiptCreateSerializer(serializers.Serializer):
    virtual_user_id = serializers.IntegerField()

    payment_mode = serializers.ChoiceField(
        choices=[
            Payment.Mode.FULL,
            Payment.Mode.SELECTED_ITEMS,
            Payment.Mode.CUSTOM_AMOUNT,
        ],
        default=Payment.Mode.CUSTOM_AMOUNT,
    )

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=0,
        required=False,
    )

    debt_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=False,
    )

    note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
    )

    def validate(self, attrs):
        payment_mode = attrs.get(
            'payment_mode',
            Payment.Mode.CUSTOM_AMOUNT,
        )

        amount = attrs.get('amount')
        debt_ids = attrs.get('debt_ids')

        if payment_mode == Payment.Mode.CUSTOM_AMOUNT:
            if amount is None:
                raise serializers.ValidationError(
                    {
                        'amount':
                        'Vui lòng nhập số tiền đã nhận trước.'
                    }
                )

            if amount <= Decimal('0'):
                raise serializers.ValidationError(
                    {
                        'amount':
                        'Số tiền nhận phải lớn hơn 0.'
                    }
                )

        elif payment_mode == Payment.Mode.SELECTED_ITEMS:
            if not debt_ids:
                raise serializers.ValidationError(
                    {
                        'debt_ids':
                        'Vui lòng chọn ít nhất một khoản đã nhận.'
                    }
                )

        return attrs
    
class PaymentAllocationSerializer(serializers.ModelSerializer):
    debt_id = serializers.SerializerMethodField()
    expense_id = serializers.SerializerMethodField()
    expense_title = serializers.SerializerMethodField()

    class Meta:
        model = PaymentAllocation
        fields = [
            'id',
            'debt_id',
            'expense_id',
            'expense_title',
            'allocated_amount',
        ]

    def get_debt_id(self, obj):
        return str(obj.debt_id)

    def get_expense_id(self, obj):
        if obj.debt and obj.debt.expense_id:
            return str(obj.debt.expense_id)

        return None

    def get_expense_title(self, obj):
        if obj.debt and obj.debt.expense:
            return obj.debt.expense.title

        return ''
    
class PaymentSerializer(serializers.ModelSerializer):
    debt_id = serializers.SerializerMethodField()
    expense_id = serializers.SerializerMethodField()
    expense_title = serializers.SerializerMethodField()

    receiver_bank_name = serializers.CharField(
        source='receiver.bank_name',
        read_only=True
    )

    receiver_bank_account_number = serializers.CharField(
        source='receiver.bank_account_number',
        read_only=True
    )

    receiver_bank_account_holder = serializers.CharField(
        source='receiver.bank_account_holder',
        read_only=True
    )

    household_id = serializers.UUIDField(
        source='household.id',
        read_only=True
    )

    household_name = serializers.CharField(
        source='household.name',
        read_only=True
    )

    payer_id = serializers.IntegerField(
        source='payer.id',
        read_only=True
    )

    payer_name = serializers.SerializerMethodField()

    payer_email = serializers.EmailField(
        source='payer.email',
        read_only=True
    )

    receiver_id = serializers.IntegerField(
        source='receiver.id',
        read_only=True
    )

    receiver_name = serializers.SerializerMethodField()

    receiver_email = serializers.EmailField(
        source='receiver.email',
        read_only=True
    )

    status_label = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    allocations = PaymentAllocationSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Payment
        fields = [
            'id',
            'debt_id',
            'household_id',
            'household_name',
            'expense_id',
            'expense_title',
            'payer_id',
            'payer_name',
            'payer_email',
            'receiver_id',
            'receiver_name',
            'receiver_email',
            'amount',
            'payment_mode',
            'allocations',
            'status',
            'status_label',
            'payer_note',
            'receiver_note',
            'confirmed_at',
            'rejected_at',
            'created_at',
            'updated_at',
            'is_pair_payment',
            'remaining_after_confirm',
            'receiver_bank_name',
            'receiver_bank_account_number',
            'receiver_bank_account_holder',
        ]

    def get_payer_name(self, obj):
        return get_user_display_name(obj.payer)

    def get_receiver_name(self, obj):
        return get_user_display_name(obj.receiver)
    
    def get_debt_id(self, obj):
        if obj.debt_id:
            return str(obj.debt_id)

        return None


    def get_expense_id(self, obj):
        if obj.debt and obj.debt.expense_id:
            return str(obj.debt.expense_id)

        return None


    def get_expense_title(self, obj):
        if obj.debt and obj.debt.expense:
            return obj.debt.expense.title

        return ''
