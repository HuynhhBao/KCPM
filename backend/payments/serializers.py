from rest_framework import serializers

from payments.models import Payment
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

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=0
    )

    note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500
    )

    def validate_amount(self, value):
        if value <= Decimal('0'):
            raise serializers.ValidationError(
                'Số tiền thanh toán phải lớn hơn 0.'
            )

        return value

class VirtualReceiptCreateSerializer(serializers.Serializer):
    virtual_user_id = serializers.IntegerField()

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=0
    )

    note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500
    )

    def validate_amount(self, value):
        if value <= Decimal('0'):
            raise serializers.ValidationError(
                'Số tiền nhận phải lớn hơn 0.'
            )

        return value

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
