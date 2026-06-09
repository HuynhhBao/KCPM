from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from rest_framework import generics
from rest_framework import permissions
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from expenses.models import Debt
from households.models import (
    Household,
    HouseholdMember,
)
from notifications.models import Notification
from notifications.services import create_notification
from payments.models import Payment, PaymentAllocation
from payments.serializers import (
    PairPaymentCreateSerializer,
    PaymentActionSerializer,
    PaymentSerializer,
    VirtualReceiptCreateSerializer,
)
from decimal import Decimal


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

def debt_remaining_amount(debt):
    paid_amount = debt.paid_amount or Decimal('0')
    remaining = debt.amount - paid_amount

    if remaining <= 0:
        return Decimal('0')

    return remaining

def get_pending_amount_for_debt(debt):
    total = Decimal('0')

    for allocation in debt.payment_allocations.filter(
        payment__status=Payment.Status.PENDING,
    ):
        total += allocation.allocated_amount

    return total


def get_debt_payable_amount(debt):
    remaining = debt_remaining_amount(debt)
    pending = get_pending_amount_for_debt(debt)

    payable = remaining - pending

    if payable <= 0:
        return Decimal('0')

    return payable


def get_forward_debts_queryset(
    *,
    household,
    payer,
    receiver,
    lock=False,
):
    queryset = Debt.objects.filter(
        household=household,
        from_user=payer,
        to_user=receiver,
        is_paid=False,
    ).select_related(
        'household',
        'expense',
        'from_user',
        'to_user',
    ).prefetch_related(
        'payment_allocations',
        'payment_allocations__payment',
    ).order_by(
        'expense__expense_date',
        'created_at',
    )

    if lock:
        queryset = queryset.select_for_update()

    return queryset


def build_allocations_for_payment_mode(
    *,
    household,
    payer,
    receiver,
    payment_mode,
    amount=None,
    debt_ids=None,
    lock=False,
):
    debts = list(
        get_forward_debts_queryset(
            household=household,
            payer=payer,
            receiver=receiver,
            lock=lock,
        )
    )

    payable_items = []

    for debt in debts:
        payable_amount = get_debt_payable_amount(debt)

        if payable_amount <= 0:
            continue

        payable_items.append(
            {
                'debt': debt,
                'payable_amount': payable_amount,
            }
        )

    total_payable = sum(
        item['payable_amount']
        for item in payable_items
    ) or Decimal('0')

    if total_payable <= 0:
        raise ValueError('Không còn khoản nào có thể thanh toán.')

    allocations = []

    if payment_mode == Payment.Mode.FULL:
        for item in payable_items:
            allocations.append(
                {
                    'debt': item['debt'],
                    'allocated_amount': item['payable_amount'],
                }
            )

        return total_payable, allocations

    if payment_mode == Payment.Mode.SELECTED_ITEMS:
        selected_ids = {
            str(item)
            for item in (debt_ids or [])
        }

        if not selected_ids:
            raise ValueError('Vui lòng chọn ít nhất một khoản cần thanh toán.')

        valid_ids = {
            str(item['debt'].id)
            for item in payable_items
        }

        invalid_ids = selected_ids - valid_ids

        if invalid_ids:
            raise ValueError(
                'Có khoản thanh toán không hợp lệ hoặc đã được thanh toán.'
            )

        total_selected = Decimal('0')

        for item in payable_items:
            if str(item['debt'].id) not in selected_ids:
                continue

            total_selected += item['payable_amount']

            allocations.append(
                {
                    'debt': item['debt'],
                    'allocated_amount': item['payable_amount'],
                }
            )

        if total_selected <= 0:
            raise ValueError('Không có khoản nào được chọn để thanh toán.')

        return total_selected, allocations

    if payment_mode == Payment.Mode.CUSTOM_AMOUNT:
        amount = Decimal(amount or 0)

        if amount <= 0:
            raise ValueError('Số tiền thanh toán phải lớn hơn 0.')

        if amount > total_payable:
            raise ValueError(
                'Số tiền thanh toán không được lớn hơn số nợ hiện tại.'
            )

        remaining_amount = amount

        for item in payable_items:
            if remaining_amount <= 0:
                break

            allocated_amount = min(
                item['payable_amount'],
                remaining_amount,
            )

            allocations.append(
                {
                    'debt': item['debt'],
                    'allocated_amount': allocated_amount,
                }
            )

            remaining_amount -= allocated_amount

        return amount, allocations

    raise ValueError('Hình thức thanh toán không hợp lệ.')


def get_pair_debt_state(
    *,
    household,
    payer,
    receiver,
    lock=False,
):
    queryset = Debt.objects.filter(
        household=household,
        is_paid=False,
    ).filter(
        Q(
            from_user=payer,
            to_user=receiver,
        ) |
        Q(
            from_user=receiver,
            to_user=payer,
        )
    ).select_related(
        'household',
        'expense',
        'from_user',
        'to_user',
    ).order_by(
        'created_at',
    )

    if lock:
        queryset = queryset.select_for_update()

    forward_debts = []
    reverse_debts = []

    forward_total = Decimal('0')
    reverse_total = Decimal('0')

    for debt in queryset:
        remaining = debt_remaining_amount(debt)

        if remaining <= 0:
            continue

        if debt.from_user_id == payer.id:
            forward_debts.append(debt)
            forward_total += remaining
        else:
            reverse_debts.append(debt)
            reverse_total += remaining

    net_amount = forward_total - reverse_total

    if net_amount <= 0:
        net_amount = Decimal('0')

    return {
        'forward_debts': forward_debts,
        'reverse_debts': reverse_debts,
        'forward_total': forward_total,
        'reverse_total': reverse_total,
        'net_amount': net_amount,
    }


def apply_pair_payment_to_debts(
    *,
    state,
    amount,
):
    amount = Decimal(amount)

    offset_amount = state['reverse_total']
    amount_to_apply = amount + offset_amount

    for debt in state['reverse_debts']:
        debt.mark_fully_paid()
        debt.save(
            update_fields=[
                'paid_amount',
                'is_paid',
                'updated_at',
            ]
        )

    for debt in state['forward_debts']:
        if amount_to_apply <= 0:
            break

        remaining = debt_remaining_amount(debt)

        if remaining <= 0:
            continue

        applied_amount = min(
            remaining,
            amount_to_apply,
        )

        debt.apply_payment(applied_amount)
        debt.save(
            update_fields=[
                'paid_amount',
                'is_paid',
                'updated_at',
            ]
        )

        amount_to_apply -= applied_amount


def is_household_owner(user, household):
    return HouseholdMember.objects.filter(
        household=household,
        user=user,
        role=HouseholdMember.Role.OWNER,
    ).exists()


def debt_has_virtual_member(debt):
    return (
        is_virtual_user(debt.from_user) or
        is_virtual_user(debt.to_user)
    )


class PaymentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class MarkDebtPaidView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, debt_id):
        action_serializer = PaymentActionSerializer(
            data=request.data
        )
        action_serializer.is_valid(raise_exception=True)

        try:
            debt = Debt.objects.select_for_update().select_related(
                'household',
                'expense',
                'from_user',
                'to_user',
            ).get(id=debt_id)
        except Debt.DoesNotExist:
            return Response(
                {'detail': 'Không tìm thấy công nợ.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if debt.is_paid:
            return Response(
                {'detail': 'Công nợ này đã được thanh toán.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if debt_has_virtual_member(debt):
            can_settle_virtual_debt = (
                debt.from_user_id == request.user.id or
                debt.to_user_id == request.user.id
            )

            if not can_settle_virtual_debt:
                raise PermissionDenied(
                    'Bạn không có quyền đánh dấu công nợ này đã thanh toán.'
                )

            debt.mark_fully_paid()
            debt.save(
                update_fields=[
                    'paid_amount',
                    'is_paid',
                    'updated_at',
                ]
            )

            return Response(
                {
                    'message':
                    'Đã đánh dấu công nợ liên quan thành viên ảo là đã thanh toán ngoài đời.',
                    'virtual_settlement': True,
                    'debt_id': str(debt.id),
                },
                status=status.HTTP_200_OK
            )

        if debt.from_user_id != request.user.id:
            raise PermissionDenied(
                'Chỉ người đang nợ mới có thể báo đã thanh toán.'
            )

        existing_pending_payment = Payment.objects.filter(
            debt=debt,
            status=Payment.Status.PENDING
        ).select_related(
            'debt',
            'debt__expense',
            'household',
            'payer',
            'receiver',
        ).first()

        if existing_pending_payment:
            return Response(
                {
                    'message': 'Yêu cầu thanh toán đang chờ xác nhận.',
                    'payment': PaymentSerializer(
                        existing_pending_payment
                    ).data,
                },
                status=status.HTTP_200_OK
            )

        remaining_amount = debt_remaining_amount(debt)

        if remaining_amount <= 0:
            debt.mark_fully_paid()
            debt.save(
                update_fields=[
                    'paid_amount',
                    'is_paid',
                    'updated_at',
                ]
            )

            return Response(
                {'detail': 'Công nợ này đã được thanh toán.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment = Payment.objects.create(
            debt=debt,
            household=debt.household,
            payer=debt.from_user,
            receiver=debt.to_user,
            amount=remaining_amount,
            payer_note=action_serializer.validated_data.get(
                'note',
                ''
            )
        )

        payer_name = get_user_display_name(payment.payer)

        create_notification(
            recipient=payment.receiver,
            actor=payment.payer,
            household=payment.household,
            notification_type=Notification.NotificationType.PAYMENT_RECEIVED,
            level=Notification.Level.PUSH,
            title=(
                f'{payer_name} báo đã thanh toán '
                f'{format_money(payment.amount)} cho khoản '
                f'"{debt.expense.title}". Vui lòng xác nhận.'
            ),
            amount=payment.amount,
            metadata={
                'payment_id': str(payment.id),
                'debt_id': str(debt.id),
                'expense_id': str(debt.expense_id),
                'status': payment.status,
            },
            push_title='Xác nhận thanh toán',
            push_body=(
                f'{payer_name} báo đã thanh toán '
                f'{format_money(payment.amount)}'
            ),
        )

        return Response(
            {
                'message': 'Đã gửi yêu cầu xác nhận thanh toán.',
                'payment': PaymentSerializer(payment).data,
            },
            status=status.HTTP_201_CREATED
        )

class CreatePairPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, household_id):
        serializer = PairPaymentCreateSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        receiver_id = serializer.validated_data['receiver_id']

        payment_mode = serializer.validated_data.get(
            'payment_mode',
            Payment.Mode.CUSTOM_AMOUNT,
        )

        amount = serializer.validated_data.get('amount')
        debt_ids = serializer.validated_data.get('debt_ids', [])
        note = serializer.validated_data.get('note', '')

        household = Household.objects.filter(
            id=household_id,
            is_active=True,
            members__user=request.user,
        ).distinct().first()

        if not household:
            return Response(
                {
                    'detail':
                    'Không tìm thấy nhóm hoặc bạn không thuộc nhóm này.'
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        receiver_membership = HouseholdMember.objects.filter(
            household=household,
            user_id=receiver_id,
        ).select_related(
            'user',
        ).first()

        if not receiver_membership:
            return Response(
                {
                    'detail':
                    'Người nhận không thuộc nhóm này.'
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        payer = request.user
        receiver = receiver_membership.user

        if payer.id == receiver.id:
            return Response(
                {
                    'detail':
                    'Không thể tự thanh toán cho chính mình.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if is_virtual_user(payer) or is_virtual_user(receiver):
            return Response(
                {
                    'detail':
                    'Công nợ liên quan thành viên ảo cần dùng chức năng xử lý ngoài đời.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        state = get_pair_debt_state(
            household=household,
            payer=payer,
            receiver=receiver,
            lock=True,
        )

        net_amount = state['net_amount']

        if net_amount <= 0:
            return Response(
                {
                    'detail':
                    'Bạn hiện không còn nợ người này.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_pending_payment = Payment.objects.filter(
            household=household,
            payer=payer,
            receiver=receiver,
            status=Payment.Status.PENDING,
        ).select_related(
            'household',
            'payer',
            'receiver',
        ).first()

        if existing_pending_payment:
            return Response(
                {
                    'message':
                    'Bạn đang có yêu cầu thanh toán chờ xác nhận với người này.',
                    'payment': PaymentSerializer(
                        existing_pending_payment,
                        context={'request': request},
                    ).data,
                },
                status=status.HTTP_200_OK,
            )

        allocation_mode = payment_mode
        allocation_amount = amount

        if payment_mode == Payment.Mode.FULL:
            allocation_mode = Payment.Mode.CUSTOM_AMOUNT
            allocation_amount = net_amount

        try:
            payment_amount, allocations = build_allocations_for_payment_mode(
                household=household,
                payer=payer,
                receiver=receiver,
                payment_mode=allocation_mode,
                amount=allocation_amount,
                debt_ids=debt_ids,
                lock=True,
            )
        except ValueError as exc:
            return Response(
                {
                    'detail': str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payment_amount > net_amount:
            return Response(
                {
                    'detail':
                    'Số tiền thanh toán không được lớn hơn số nợ hiện tại.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment = Payment.objects.create(
            debt=None,
            household=household,
            payer=payer,
            receiver=receiver,
            amount=payment_amount,
            payment_mode=payment_mode,
            is_pair_payment=True,
            payer_note=note,
        )

        for item in allocations:
            PaymentAllocation.objects.create(
                payment=payment,
                debt=item['debt'],
                allocated_amount=item['allocated_amount'],
            )

        payer_name = get_user_display_name(payer)
        remaining_after_request = net_amount - payment_amount

        if payment_mode == Payment.Mode.FULL:
            message = 'Đã gửi yêu cầu xác nhận thanh toán toàn bộ.'

        elif payment_mode == Payment.Mode.SELECTED_ITEMS:
            if remaining_after_request > 0:
                message = (
                    f'Đã gửi yêu cầu xác nhận thanh toán '
                    f'{len(allocations)} khoản. '
                    f'Còn nợ {format_money(remaining_after_request)}.'
                )
            else:
                message = (
                    f'Đã gửi yêu cầu xác nhận thanh toán '
                    f'{len(allocations)} khoản.'
                )

        else:
            if remaining_after_request > 0:
                message = (
                    f'Đã gửi yêu cầu xác nhận thanh toán trước '
                    f'{format_money(payment_amount)}. '
                    f'Còn nợ {format_money(remaining_after_request)}.'
                )
            else:
                message = 'Đã gửi yêu cầu xác nhận thanh toán toàn bộ.'

        create_notification(
            recipient=receiver,
            actor=payer,
            household=household,
            notification_type=Notification.NotificationType.PAYMENT_RECEIVED,
            level=Notification.Level.PUSH,
            title=(
                f'{payer_name} báo đã thanh toán '
                f'{format_money(payment_amount)}. Vui lòng xác nhận.'
            ),
            amount=payment_amount,
            metadata={
                'payment_id': str(payment.id),
                'household_id': str(household.id),
                'payer_id': payer.id,
                'receiver_id': receiver.id,
                'status': payment.status,
                'is_pair_payment': True,
                'payment_mode': payment.payment_mode,
                'allocation_count': len(allocations),
            },
            push_title='Xác nhận thanh toán',
            push_body=(
                f'{payer_name} báo đã thanh toán '
                f'{format_money(payment_amount)}'
            ),
        )

        return Response(
            {
                'message': message,
                'remaining_after_request': int(remaining_after_request),
                'payment': PaymentSerializer(
                    payment,
                    context={'request': request},
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )
    
class RecordVirtualReceiptView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, household_id):
        serializer = VirtualReceiptCreateSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        virtual_user_id = serializer.validated_data['virtual_user_id']
        amount = serializer.validated_data['amount']
        note = serializer.validated_data.get('note', '')

        household = Household.objects.filter(
            id=household_id,
            is_active=True,
            members__user=request.user,
        ).distinct().first()

        if not household:
            return Response(
                {
                    'detail':
                    'Không tìm thấy nhóm hoặc bạn không thuộc nhóm này.'
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        virtual_membership = HouseholdMember.objects.filter(
            household=household,
            user_id=virtual_user_id,
        ).select_related(
            'user',
        ).first()

        if not virtual_membership:
            return Response(
                {
                    'detail': 'Thành viên ảo không thuộc nhóm này.'
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        virtual_user = virtual_membership.user

        if not is_virtual_user(virtual_user):
            return Response(
                {
                    'detail': 'Người được chọn không phải thành viên ảo.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        receiver = request.user

        if receiver.id == virtual_user.id:
            return Response(
                {
                    'detail': 'Dữ liệu người nhận không hợp lệ.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        state = get_pair_debt_state(
            household=household,
            payer=virtual_user,
            receiver=receiver,
            lock=True,
        )

        net_amount = state['net_amount']

        if net_amount <= 0:
            return Response(
                {
                    'detail':
                    'Thành viên ảo này hiện không còn nợ bạn.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if amount > net_amount:
            return Response(
                {
                    'detail':
                    'Số tiền nhận không được lớn hơn số nợ hiện tại.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        remaining_after_confirm = net_amount - amount

        apply_pair_payment_to_debts(
            state=state,
            amount=amount,
        )

        payment = Payment.objects.create(
            debt=None,
            household=household,
            payer=virtual_user,
            receiver=receiver,
            amount=amount,
            is_pair_payment=True,
            remaining_after_confirm=remaining_after_confirm,
            status=Payment.Status.CONFIRMED,
            receiver_note=note,
            confirmed_at=timezone.now(),
        )

        if remaining_after_confirm > 0:
            message = (
                f'Đã ghi nhận nhận {format_money(amount)}. '
                f'Còn {format_money(remaining_after_confirm)}.'
            )
        else:
            message = 'Đã ghi nhận nhận đủ tiền từ thành viên ảo.'

        return Response(
            {
                'message': message,
                'remaining_after_confirm': int(remaining_after_confirm),
                'payment': PaymentSerializer(
                    payment,
                    context={'request': request},
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

class PendingPaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PaymentPagination

    def get_queryset(self):
        return Payment.objects.filter(
            receiver=self.request.user,
            status=Payment.Status.PENDING
        ).select_related(
            'debt',
            'debt__expense',
            'household',
            'payer',
            'receiver',
        ).order_by('-created_at')


class MyPaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PaymentPagination

    def get_queryset(self):
        return Payment.objects.filter(
            Q(payer=self.request.user) |
            Q(receiver=self.request.user)
        ).select_related(
            'debt',
            'debt__expense',
            'household',
            'payer',
            'receiver',
        ).order_by('-created_at')


class ConfirmPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        action_serializer = PaymentActionSerializer(
            data=request.data
        )
        action_serializer.is_valid(raise_exception=True)

        try:
            payment = Payment.objects.select_for_update().select_related(
                'household',
                'payer',
                'receiver',
            ).get(id=pk)

            if payment.debt_id:
                payment.debt = Debt.objects.select_for_update().select_related(
                    'expense',
                    'household',
                    'from_user',
                    'to_user',
                ).get(id=payment.debt_id)

        except Payment.DoesNotExist:
            return Response(
                {'detail': 'Không tìm thấy yêu cầu thanh toán.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Debt.DoesNotExist:
            return Response(
                {'detail': 'Không tìm thấy công nợ của yêu cầu thanh toán.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if payment.receiver_id != request.user.id:
            raise PermissionDenied(
                'Chỉ người nhận tiền mới có thể xác nhận thanh toán.'
            )

        if payment.status != Payment.Status.PENDING:
            return Response(
                {
                    'detail':
                    'Yêu cầu thanh toán này không còn chờ xác nhận.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if payment.is_pair_payment or payment.debt_id is None:
            allocations = list(
                payment.allocations.select_related(
                    'debt',
                    'debt__expense',
                    'debt__household',
                    'debt__from_user',
                    'debt__to_user',
                )
            )

            if not allocations:
                return Response(
                    {
                        'detail':
                        'Yêu cầu thanh toán này chưa có phân bổ công nợ.'
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            for allocation in allocations:
                debt = allocation.debt
                remaining_amount = debt_remaining_amount(debt)

                if remaining_amount <= 0:
                    continue

                if allocation.allocated_amount > remaining_amount:
                    return Response(
                        {
                            'detail':
                            f'Khoản "{debt.expense.title}" có số tiền thanh toán lớn hơn số còn nợ.'
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                debt.apply_payment(allocation.allocated_amount)
                debt.save(
                    update_fields=[
                        'paid_amount',
                        'is_paid',
                        'updated_at',
                    ]
                )

            payment.remaining_after_confirm = sum(
                debt_remaining_amount(allocation.debt)
                for allocation in allocations
            )
        else:
            remaining_amount = debt_remaining_amount(payment.debt)

            if remaining_amount <= 0:
                return Response(
                    {
                        'detail':
                        'Công nợ này đã được thanh toán.'
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if payment.amount > remaining_amount:
                return Response(
                    {
                        'detail':
                        'Số tiền thanh toán lớn hơn công nợ hiện tại.'
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payment.debt.apply_payment(payment.amount)
            payment.debt.save(
                update_fields=[
                    'paid_amount',
                    'is_paid',
                    'updated_at',
                ]
            )

            payment.remaining_after_confirm = payment.debt.remaining_amount

        payment.status = Payment.Status.CONFIRMED
        payment.receiver_note = action_serializer.validated_data.get(
            'note',
            ''
        )
        payment.confirmed_at = timezone.now()
        payment.save(
            update_fields=[
                'status',
                'receiver_note',
                'confirmed_at',
                'remaining_after_confirm',
                'updated_at',
            ]
        )

        receiver_name = get_user_display_name(payment.receiver)

        create_notification(
            recipient=payment.payer,
            actor=payment.receiver,
            household=payment.household,
            notification_type=Notification.NotificationType.PAYMENT_SENT,
            level=Notification.Level.PUSH,
            title=(
                f'{receiver_name} đã xác nhận nhận '
                f'{format_money(payment.amount)}.'
            ),
            amount=payment.amount,
            metadata={
                'payment_id': str(payment.id),
                'debt_id': str(payment.debt_id) if payment.debt_id else None,
                'expense_id': (
                    str(payment.debt.expense_id)
                    if payment.debt and payment.debt.expense_id
                    else None
                ),
                'household_id': str(payment.household_id),
                'payer_id': payment.payer_id,
                'receiver_id': payment.receiver_id,
                'status': payment.status,
                'is_pair_payment': payment.is_pair_payment,
            },
            push_title='Thanh toán đã được xác nhận',
            push_body=(
                f'{receiver_name} đã xác nhận nhận tiền.'
            ),
        )

        return Response(
            {
                'message': 'Đã xác nhận nhận tiền.',
                'payment': PaymentSerializer(payment).data,
            },
            status=status.HTTP_200_OK
        )


class RejectPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        action_serializer = PaymentActionSerializer(
            data=request.data
        )
        action_serializer.is_valid(raise_exception=True)

        try:
            payment = Payment.objects.select_for_update().select_related(
                'household',
                'payer',
                'receiver',
            ).get(id=pk)

            if payment.debt_id:
                payment.debt = Debt.objects.select_related(
                    'expense',
                    'household',
                    'from_user',
                    'to_user',
                ).get(id=payment.debt_id)

        except Payment.DoesNotExist:
            return Response(
                {'detail': 'Không tìm thấy yêu cầu thanh toán.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Debt.DoesNotExist:
            return Response(
                {'detail': 'Không tìm thấy công nợ của yêu cầu thanh toán.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if payment.receiver_id != request.user.id:
            raise PermissionDenied(
                'Chỉ người nhận tiền mới có thể từ chối thanh toán.'
            )

        if payment.status != Payment.Status.PENDING:
            return Response(
                {
                    'detail':
                    'Yêu cầu thanh toán này không còn chờ xác nhận.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        payment.status = Payment.Status.REJECTED
        payment.receiver_note = action_serializer.validated_data.get(
            'note',
            ''
        )
        payment.rejected_at = timezone.now()
        payment.save(
            update_fields=[
                'status',
                'receiver_note',
                'rejected_at',
                'updated_at',
            ]
        )

        receiver_name = get_user_display_name(payment.receiver)

        create_notification(
            recipient=payment.payer,
            actor=payment.receiver,
            household=payment.household,
            notification_type=Notification.NotificationType.PAYMENT_SENT,
            level=Notification.Level.PUSH,
            title=(
                f'{receiver_name} chưa xác nhận khoản thanh toán '
                f'{format_money(payment.amount)}.'
            ),
            amount=payment.amount,
            metadata={
                'payment_id': str(payment.id),
                'debt_id': str(payment.debt_id) if payment.debt_id else None,
                'expense_id': (
                    str(payment.debt.expense_id)
                    if payment.debt and payment.debt.expense_id
                    else None
                ),
                'household_id': str(payment.household_id),
                'payer_id': payment.payer_id,
                'receiver_id': payment.receiver_id,
                'status': payment.status,
                'is_pair_payment': payment.is_pair_payment,
            },
            push_title='Thanh toán bị từ chối',
            push_body=(
                f'{receiver_name} chưa xác nhận khoản thanh toán.'
            ),
        )

        return Response(
            {
                'message': 'Đã từ chối yêu cầu thanh toán.',
                'payment': PaymentSerializer(payment).data,
            },
            status=status.HTTP_200_OK
        )
