from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from expenses.models import Debt, Expense, ExpenseParticipant
from households.models import Activity, HouseholdMember

from notifications.models import Notification
from notifications.services import create_notification


VIRTUAL_MEMBER_EMAIL_DOMAIN = '@virtual.chungvi.local'


def is_virtual_user(user):
    email = (getattr(user, 'email', '') or '').lower()
    return email.endswith(VIRTUAL_MEMBER_EMAIL_DOMAIN)


def get_user_display_name(user):
    if is_virtual_user(user):
        return user.full_name or 'Thành viên ảo'

    return user.full_name or user.email


def format_money(amount):
    return f'{amount:,.0f}đ'.replace(',', '.')

def is_user_expense_manager(user, expense):
    return expense.payer_id == user.id

class ExpenseParticipantInputSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

    share_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=0,
        required=False
    )


class ExpenseParticipantSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(
        source='user.id',
        read_only=True
    )

    user_name = serializers.SerializerMethodField()
    user_email = serializers.EmailField(
        source='user.email',
        read_only=True
    )
    user_avatar = serializers.SerializerMethodField()
    is_virtual = serializers.SerializerMethodField()

    class Meta:
        model = ExpenseParticipant
        fields = [
            'id',
            'user_id',
            'user_name',
            'user_email',
            'user_avatar',
            'is_virtual',
            'share_amount',
        ]

    def get_user_name(self, obj):
        return get_user_display_name(obj.user)

    def get_user_avatar(self, obj):
        request = self.context.get('request')

        if obj.user.avatar and request:
            return request.build_absolute_uri(
                obj.user.avatar.url
            )

        return ''

    def get_is_virtual(self, obj):
        return is_virtual_user(obj.user)


class ExpenseCreateUpdateSerializer(serializers.ModelSerializer):
    participants = ExpenseParticipantInputSerializer(
        many=True,
        write_only=True,
        required=False
    )

    class Meta:
        model = Expense
        fields = [
            'id',
            'household',
            'title',
            'amount',
            'split_type',
            'note',
            'participants',
            'expense_date',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance is None:
            self.fields['participants'].required = True
            self.fields['household'].required = True
        else:
            self.fields['household'].read_only = True

    def validate_title(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                'Tên khoản chi không được để trống.'
            )

        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Số tiền phải lớn hơn 0.'
            )

        return value

    def validate_expense_date(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError(
                'Ngày chi không được lớn hơn hôm nay.'
            )

        return value

    def validate(self, attrs):
        request = self.context.get('request')

        if not request:
            raise serializers.ValidationError(
                'Không xác định được người dùng hiện tại.'
            )

        instance = self.instance

        household = (
            attrs.get('household')
            if instance is None
            else instance.household
        )

        if not HouseholdMember.objects.filter(
            household=household,
            user=request.user
        ).exists():
            raise serializers.ValidationError(
                'Bạn không có quyền thao tác trong nhóm này.'
            )

        if instance is not None:
            if not is_user_expense_manager(
                request.user,
                instance
            ):
                raise serializers.ValidationError(
                    'Bạn không có quyền sửa khoản chi này.'
                )

            if instance.debts.filter(is_paid=True).exists():
                raise serializers.ValidationError(
                    'Không thể sửa khoản chi đã có công nợ được thanh toán.'
                )

            if instance.debts.filter(
                payments__status='pending'
            ).exists():
                raise serializers.ValidationError(
                    'Không thể sửa khoản chi đang chờ xác nhận thanh toán.'
                )

        payer = instance.payer if instance else request.user

        if is_virtual_user(payer):
            raise serializers.ValidationError(
                'Thành viên ảo không thể là người thanh toán khoản chi.'
            )

        if not HouseholdMember.objects.filter(
            household=household,
            user=payer
        ).exists():
            raise serializers.ValidationError(
                'Người tạo khoản chi không thuộc nhóm này.'
            )

        amount = attrs.get(
            'amount',
            instance.amount if instance else None
        )

        split_type = attrs.get(
            'split_type',
            instance.split_type if instance else Expense.SplitType.EQUAL
        )

        participants = attrs.get('participants')

        if participants is None and instance is not None:
            participants = [
                {
                    'user_id': item.user_id,
                    'share_amount': item.share_amount,
                }
                for item in instance.participants.all()
            ]

        if not participants:
            raise serializers.ValidationError(
                'Vui lòng chọn ít nhất một người tham gia chia tiền.'
            )

        participant_ids = [
            item['user_id']
            for item in participants
        ]

        if len(participant_ids) != len(set(participant_ids)):
            raise serializers.ValidationError(
                'Danh sách người chia tiền bị trùng.'
            )

        members = HouseholdMember.objects.filter(
            household=household,
            user_id__in=participant_ids
        ).select_related('user')

        if members.count() != len(set(participant_ids)):
            raise serializers.ValidationError(
                'Danh sách người chia tiền có người không thuộc nhóm.'
            )

        users_by_id = {
            member.user_id: member.user
            for member in members
        }

        split_items = self._build_split_items(
            amount=amount,
            split_type=split_type,
            participants=participants,
            users_by_id=users_by_id,
        )

        attrs['payer'] = payer
        attrs['_split_items'] = split_items

        return attrs

    def _build_split_items(
        self,
        *,
        amount,
        split_type,
        participants,
        users_by_id,
    ):
        if split_type == Expense.SplitType.MANUAL:
            total_share = Decimal('0')
            split_items = []

            for item in participants:
                if 'share_amount' not in item:
                    raise serializers.ValidationError(
                        'Chia thủ công cần nhập số tiền cho từng người.'
                    )

                share_amount = item['share_amount']

                if share_amount <= 0:
                    raise serializers.ValidationError(
                        'Số tiền chia cho từng người phải lớn hơn 0.'
                    )

                total_share += share_amount

                split_items.append(
                    (
                        users_by_id[item['user_id']],
                        share_amount,
                    )
                )

            if total_share != amount:
                raise serializers.ValidationError(
                    'Tổng số tiền chia phải bằng tổng khoản chi.'
                )

            return split_items

        total_amount = int(amount)
        participant_count = len(participants)

        base_share = total_amount // participant_count
        remainder = total_amount % participant_count

        split_items = []

        for index, item in enumerate(participants):
            share_amount = Decimal(
                base_share + (
                    remainder if index == 0 else 0
                )
            )

            split_items.append(
                (
                    users_by_id[item['user_id']],
                    share_amount,
                )
            )

        return split_items

    def _sync_participants_and_debts(
        self,
        *,
        expense,
        split_items,
        send_notifications=False,
    ):
        expense.participants.all().delete()
        expense.debts.all().delete()

        payer_name = get_user_display_name(expense.payer)

        for user, share_amount in split_items:
            ExpenseParticipant.objects.create(
                expense=expense,
                user=user,
                share_amount=share_amount
            )

            if user == expense.payer:
                continue

            debt = Debt.objects.create(
                household=expense.household,
                expense=expense,
                from_user=user,
                to_user=expense.payer,
                amount=share_amount
            )

            if (
                send_notifications and
                not is_virtual_user(user) and
                not is_virtual_user(expense.payer)
            ):
                create_notification(
                    recipient=user,
                    actor=expense.payer,
                    household=expense.household,
                    notification_type=(
                        Notification.NotificationType.DEBT_CREATED
                    ),
                    level=Notification.Level.PUSH,
                    title=(
                        f'{payer_name} đã thêm khoản "{expense.title}", '
                        f'bạn cần chia {format_money(share_amount)}'
                    ),
                    amount=share_amount,
                    metadata={
                        'expense_id': str(expense.id),
                        'debt_id': str(debt.id),
                        'payer_id': expense.payer.id,
                        'share_amount': str(share_amount),
                    },
                    push_title='Khoản chi mới',
                    push_body=(
                        f'{payer_name} vừa thêm '
                        f'"{expense.title}"'
                    ),
                )

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get('request')

        split_items = validated_data.pop('_split_items')
        validated_data.pop('participants', None)

        expense = Expense.objects.create(**validated_data)

        actor_name = get_user_display_name(request.user)

        Activity.objects.create(
            household=expense.household,
            actor=request.user,
            activity_type=Activity.ActivityType.EXPENSE_CREATED,
            title=f'{actor_name} đã thêm khoản "{expense.title}"',
            amount=expense.amount,
            metadata={
                'expense_id': str(expense.id),
                'participant_count': len(split_items),
            }
        )

        self._sync_participants_and_debts(
            expense=expense,
            split_items=split_items,
            send_notifications=True,
        )

        return expense

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get('request')

        split_items = validated_data.pop('_split_items')
        validated_data.pop('participants', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        self._sync_participants_and_debts(
            expense=instance,
            split_items=split_items,
            send_notifications=False,
        )

        actor_name = get_user_display_name(request.user)

        Activity.objects.create(
            household=instance.household,
            actor=request.user,
            activity_type=Activity.ActivityType.EXPENSE_UPDATED,
            title=f'{actor_name} đã sửa khoản "{instance.title}"',
            amount=instance.amount,
            metadata={
                'expense_id': str(instance.id),
                'participant_count': len(split_items),
            }
        )

        return instance

    def to_representation(self, instance):
        return ExpenseDetailSerializer(instance, context=self.context).data


class ExpenseListSerializer(serializers.ModelSerializer):
    payer_id = serializers.IntegerField(
        source='payer.id',
        read_only=True
    )

    payer_name = serializers.SerializerMethodField()

    payer_email = serializers.EmailField(
        source='payer.email',
        read_only=True
    )

    payer_avatar = serializers.SerializerMethodField()

    participants = ExpenseParticipantSerializer(
        many=True,
        read_only=True
    )

    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = [
            'id',
            'household',
            'title',
            'amount',
            'payer_id',
            'payer_name',
            'payer_email',
            'payer_avatar',
            'split_type',
            'participants',
            'expense_date',
            'note',
            'can_manage',
            'created_at',
            'updated_at',
        ]

    def get_payer_name(self, obj):
        return get_user_display_name(obj.payer)

    def get_payer_avatar(self, obj):
        request = self.context.get('request')

        if obj.payer.avatar and request:
            return request.build_absolute_uri(
                obj.payer.avatar.url
            )

        return ''

    def get_can_manage(self, obj):
        request = self.context.get('request')

        if not request:
            return False

        return obj.payer_id == request.user.id


class ExpenseDetailSerializer(ExpenseListSerializer):
    pass


class DebtSerializer(serializers.ModelSerializer):
    expense_id = serializers.UUIDField(
        source='expense.id',
        read_only=True
    )

    expense_title = serializers.CharField(
        source='expense.title',
        read_only=True
    )

    from_user_name = serializers.SerializerMethodField()

    from_user_email = serializers.EmailField(
        source='from_user.email',
        read_only=True
    )

    from_user_avatar = serializers.SerializerMethodField()

    to_user_name = serializers.SerializerMethodField()

    to_user_email = serializers.EmailField(
        source='to_user.email',
        read_only=True
    )

    to_user_avatar = serializers.SerializerMethodField()

    bank_name = serializers.CharField(
        source='to_user.bank_name',
        read_only=True
    )

    bank_account_number = serializers.CharField(
        source='to_user.bank_account_number',
        read_only=True
    )

    bank_account_holder = serializers.CharField(
        source='to_user.bank_account_holder',
        read_only=True
    )

    from_user_is_virtual = serializers.SerializerMethodField()
    to_user_is_virtual = serializers.SerializerMethodField()
    has_virtual_member = serializers.SerializerMethodField()

    pending_payment_id = serializers.SerializerMethodField()
    pending_payment_status = serializers.SerializerMethodField()
    can_mark_paid = serializers.SerializerMethodField()
    can_confirm_payment = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    original_amount = serializers.SerializerMethodField()
    paid_amount = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()

    class Meta:
        model = Debt
        fields = [
            'id',
            'expense_id',
            'expense_title',

            'from_user_name',
            'from_user_email',
            'from_user_avatar',
            'from_user_is_virtual',

            'to_user_name',
            'to_user_email',
            'to_user_avatar',
            'to_user_is_virtual',
            'has_virtual_member',

            'bank_name',
            'bank_account_number',
            'bank_account_holder',

            'amount',
            'is_paid',
            'pending_payment_id',
            'pending_payment_status',
            'can_mark_paid',
            'can_confirm_payment',
            'original_amount',
            'paid_amount',
            'remaining_amount',
        ]

    def get_from_user_name(self, obj):
        return get_user_display_name(obj.from_user)

    def get_to_user_name(self, obj):
        return get_user_display_name(obj.to_user)

    def get_from_user_is_virtual(self, obj):
        return is_virtual_user(obj.from_user)

    def get_to_user_is_virtual(self, obj):
        return is_virtual_user(obj.to_user)

    def get_has_virtual_member(self, obj):
        return (
            self.get_from_user_is_virtual(obj) or
            self.get_to_user_is_virtual(obj)
        )

    def get_pending_payment(self, obj):
        payment = obj.payments.filter(
            status='pending'
        ).order_by('-created_at').first()

        if payment:
            return payment

        from payments.models import Payment

        return Payment.objects.filter(
            household=obj.household,
            payer=obj.from_user,
            receiver=obj.to_user,
            status='pending',
        ).order_by('-created_at').first()

    def get_pending_payment_id(self, obj):
        payment = self.get_pending_payment(obj)

        if payment:
            return str(payment.id)

        return None

    def get_pending_payment_status(self, obj):
        payment = self.get_pending_payment(obj)

        if payment:
            return payment.status

        return ''

    def get_can_mark_paid(self, obj):
        request = self.context.get('request')

        if not request or obj.is_paid:
            return False

        if self.get_pending_payment(obj) is not None:
            return False

        has_virtual = self.get_has_virtual_member(obj)

        if has_virtual:
            if obj.from_user_id == request.user.id:
                return True

            if obj.to_user_id == request.user.id:
                return True

            return False

        return obj.from_user_id == request.user.id

    def get_can_confirm_payment(self, obj):
        request = self.context.get('request')

        if not request or obj.is_paid:
            return False

        if self.get_has_virtual_member(obj):
            return False

        if obj.to_user_id != request.user.id:
            return False

        return self.get_pending_payment(obj) is not None

    def get_from_user_avatar(self, obj):
        request = self.context.get('request')

        if obj.from_user.avatar and request:
            return request.build_absolute_uri(
                obj.from_user.avatar.url
            )

        return ''

    def get_to_user_avatar(self, obj):
        request = self.context.get('request')

        if obj.to_user.avatar and request:
            return request.build_absolute_uri(
                obj.to_user.avatar.url
            )

        return ''
    
    def get_amount(self, obj):
        return int(obj.remaining_amount)


    def get_original_amount(self, obj):
        return int(obj.amount)


    def get_paid_amount(self, obj):
        return int(obj.paid_amount or 0)


    def get_remaining_amount(self, obj):
        return int(obj.remaining_amount)
