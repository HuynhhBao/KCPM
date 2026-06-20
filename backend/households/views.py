import secrets

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db import transaction
from django.db.models import (
    Case,
    Count,
    DecimalField,
    F,
    IntegerField,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Sum,
    Value,
    When,
)

from django.db.models.functions import Coalesce
from accounts.avatar_utils import build_user_avatar_url

from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework import status

from rest_framework.permissions import (
    IsAuthenticated,
)

from rest_framework.response import Response
from rest_framework.views import APIView

from expenses.models import Debt
from payments.models import Payment
from payments.serializers import PaymentSerializer

from households.models import (
    Activity,
    Household,
    HouseholdMember,
)

from households.serializers import (
    ActivitySerializer,
    AddHouseholdMemberSerializer,
    CreateVirtualMemberSerializer,
    HouseholdListSerializer,
    HouseholdSerializer,
    HouseholdSummarySerializer,
    JoinHouseholdSerializer,
)

User = get_user_model()

VIRTUAL_MEMBER_EMAIL_DOMAIN = '@virtual.chungvi.local'


def is_virtual_user(user):
    email = (getattr(user, 'email', '') or '').lower()
    return email.endswith(VIRTUAL_MEMBER_EMAIL_DOMAIN)


def get_user_display_name(user):
    if is_virtual_user(user):
        return user.full_name or 'Thành viên ảo'

    return user.full_name or user.email


def make_virtual_email(household):
    return (
        f'virtual+{household.id.hex}+'
        f'{secrets.token_hex(6)}'
        f'{VIRTUAL_MEMBER_EMAIL_DOMAIN}'
    )



def money_to_int(amount):
    if amount is None:
        return 0

    return int(amount)

def debt_remaining_to_int(debt):
    paid_amount = getattr(debt, 'paid_amount', 0) or 0
    remaining = debt.amount - paid_amount

    if remaining <= 0:
        return 0

    return int(remaining)

def get_debt_summary_rows(
    *,
    household,
    subject_user,
):
    money_field = DecimalField(
        max_digits=12,
        decimal_places=0,
    )

    zero_money = Value(
        0,
        output_field=money_field,
    )

    paid_amount = Coalesce(
        F('paid_amount'),
        zero_money,
        output_field=money_field,
    )

    remaining_amount = Case(
        When(
            paid_amount__gte=F('amount'),
            then=zero_money,
        ),
        default=F('amount') - paid_amount,
        output_field=money_field,
    )

    rows = list(
        Debt.objects.filter(
            household=household,
            is_paid=False,
        ).filter(
            Q(from_user=subject_user) |
            Q(to_user=subject_user)
        ).annotate(
            other_user_id=Case(
                When(
                    from_user=subject_user,
                    then=F('to_user_id'),
                ),
                default=F('from_user_id'),
                output_field=IntegerField(),
            ),
        ).values(
            'other_user_id',
        ).annotate(
            subject_owes_amount=Sum(
                Case(
                    When(
                        from_user=subject_user,
                        then=remaining_amount,
                    ),
                    default=zero_money,
                    output_field=money_field,
                )
            ),
            owed_to_subject_amount=Sum(
                Case(
                    When(
                        to_user=subject_user,
                        then=remaining_amount,
                    ),
                    default=zero_money,
                    output_field=money_field,
                )
            ),
            expense_count=Count(
                'expense_id',
                distinct=True,
            ),
        ).order_by()
    )

    other_user_ids = [
        row['other_user_id']
        for row in rows
    ]

    users_by_id = User.objects.filter(
        id__in=other_user_ids,
    ).in_bulk()

    return rows, users_by_id

def debt_pending_amount_to_int(debt):
    total = 0

    for payment in debt.payments.all():
        if payment.status == Payment.Status.PENDING:
            total += money_to_int(payment.amount)

    if hasattr(debt, 'payment_allocations'):
        for allocation in debt.payment_allocations.all():
            payment = getattr(allocation, 'payment', None)

            if payment and payment.status == Payment.Status.PENDING:
                total += money_to_int(allocation.allocated_amount)

    return total


def get_debt_item_status(debt, pending_amount):
    remaining_amount = debt_remaining_to_int(debt)
    paid_amount = money_to_int(getattr(debt, 'paid_amount', 0))

    if debt.is_paid or remaining_amount <= 0:
        return 'paid'

    if pending_amount > 0 and paid_amount > 0:
        return 'partial_paid_pending'

    if pending_amount > 0:
        return 'pending'

    if paid_amount > 0:
        return 'partial_paid'

    return 'unpaid'


def serialize_debt_detail_item(
    *,
    debt,
    direction,
    request,
):
    pending_amount = debt_pending_amount_to_int(debt)
    remaining_amount = debt_remaining_to_int(debt)
    paid_amount = money_to_int(getattr(debt, 'paid_amount', 0))
    original_amount = money_to_int(debt.amount)

    status_value = get_debt_item_status(
        debt,
        pending_amount,
    )

    payable_amount = remaining_amount - pending_amount

    if payable_amount < 0:
        payable_amount = 0

    return {
        'debt_id': str(debt.id),
        'expense_id': str(debt.expense_id),
        'expense_title': debt.expense.title,
        'expense_date': (
            debt.expense.expense_date.isoformat()
            if debt.expense.expense_date
            else ''
        ),
        **serialize_debt_payer(
            debt.expense.payer,
            request,
        ),
        'from_user_id': debt.from_user_id,
        'from_user_name': get_user_display_name(
            debt.from_user
        ),
        'to_user_id': debt.to_user_id,
        'to_user_name': get_user_display_name(
            debt.to_user
        ),
        'direction': direction,

        # Giữ tương thích với frontend cũ:
        'amount': remaining_amount,

        # Field mới cho màn Chưa thanh toán / Đã thanh toán:
        'original_amount': original_amount,
        'paid_amount': paid_amount,
        'pending_amount': pending_amount,
        'remaining_amount': remaining_amount,
        'payable_amount': payable_amount,
        'remaining_after_pending': payable_amount,
        'status': status_value,

        'is_paid': debt.is_paid,
        'created_at': (
            debt.created_at.isoformat()
            if debt.created_at
            else ''
        ),
        'updated_at': (
            debt.updated_at.isoformat()
            if debt.updated_at
            else ''
        ),
        'paid_at': (
            debt.updated_at.isoformat()
            if debt.is_paid and debt.updated_at
            else ''
        ),
    }


def serialize_debt_user(user, request=None):
    avatar_url = ''

    if not is_virtual_user(user):
        avatar_url = build_user_avatar_url(
            user,
            request,
        )

    return {
        'other_user_id': user.id,
        'other_name': get_user_display_name(user),
        'other_email': user.email,
        'other_avatar': avatar_url,
        'is_virtual': is_virtual_user(user),
    }

def serialize_debt_payer(user, request=None):
    if not user:
        return {
            'payer_id': None,
            'payer_name': 'Không rõ người chi',
            'payer_email': '',
            'payer_avatar': '',
            'payer_is_virtual': False,
        }

    avatar_url = ''

    if not is_virtual_user(user):
        avatar_url = build_user_avatar_url(
            user,
            request,
        )

    return {
        'payer_id': user.id,
        'payer_name': get_user_display_name(user),
        'payer_email': user.email,
        'payer_avatar': avatar_url,
        'payer_is_virtual': is_virtual_user(user),
    }

def serialize_bank_info(user):
    return {
        'bank_name': getattr(user, 'bank_name', '') or '',
        'bank_account_number': getattr(
            user,
            'bank_account_number',
            '',
        ) or '',
        'bank_account_holder': getattr(
            user,
            'bank_account_holder',
            '',
        ) or '',
    }


def get_pending_pair_payment(
    *,
    household,
    payer,
    receiver,
):
    return Payment.objects.filter(
        household=household,
        payer=payer,
        receiver=receiver,
        status=Payment.Status.PENDING,
    ).select_related(
        'household',
        'payer',
        'receiver',
        'debt',
        'debt__expense',
    ).prefetch_related(
        'allocations',
        'allocations__debt',
        'allocations__debt__expense',
    ).order_by(
        '-created_at',
    ).first()


def get_pair_payment_timeline(
    *,
    household,
    user_a,
    user_b,
    request,
):
    payments = Payment.objects.filter(
        household=household,
    ).filter(
        Q(payer=user_a, receiver=user_b) |
        Q(payer=user_b, receiver=user_a)
    ).select_related(
        'household',
        'payer',
        'receiver',
        'debt',
        'debt__expense',
    ).order_by(
        '-created_at',
    )[:20]

    timeline = []

    for payment in payments:
        timeline.append(
            {
                'type': f'payment_{payment.status}',
                'payment_id': str(payment.id),
                'payer_id': payment.payer_id,
                'payer_name': get_user_display_name(payment.payer),
                'receiver_id': payment.receiver_id,
                'receiver_name': get_user_display_name(payment.receiver),
                'amount': money_to_int(payment.amount),
                'status': payment.status,
                'is_pair_payment': payment.is_pair_payment,
                'remaining_after_confirm': money_to_int(
                    payment.remaining_after_confirm
                ),
                'created_at': payment.created_at.isoformat()
                if payment.created_at
                else '',
                'confirmed_at': payment.confirmed_at.isoformat()
                if payment.confirmed_at
                else '',
                'rejected_at': payment.rejected_at.isoformat()
                if payment.rejected_at
                else '',
            }
        )

    return timeline

def get_owner_household_or_response(request, household_id):
    household = Household.objects.filter(
        id=household_id,
        is_active=True,
        members__user=request.user,
    ).distinct().first()

    if not household:
        return None, Response(
            {
                'detail':
                'Không tìm thấy nhóm hoặc bạn không thuộc nhóm này.'
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    is_owner = HouseholdMember.objects.filter(
        household=household,
        user=request.user,
        role=HouseholdMember.Role.OWNER,
    ).exists()

    if not is_owner:
        return None, Response(
            {
                'detail':
                'Chỉ chủ nhóm mới được xem công nợ của thành viên ảo.'
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    return household, None

def get_virtual_pair_household_or_response(
    request,
    household_id,
    other_user_id,
):
    household = Household.objects.filter(
        id=household_id,
        is_active=True,
        members__user=request.user,
    ).distinct().first()

    if not household:
        return None, Response(
            {
                'detail':
                'Không tìm thấy nhóm hoặc bạn không thuộc nhóm này.'
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    is_owner = HouseholdMember.objects.filter(
        household=household,
        user=request.user,
        role=HouseholdMember.Role.OWNER,
    ).exists()

    is_involved_user = request.user.id == other_user_id

    if not is_owner and not is_involved_user:
        return None, Response(
            {
                'detail':
                'Bạn chỉ được xem công nợ thành viên ảo khi là chủ nhóm hoặc là người liên quan trực tiếp.'
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    return household, None


def get_virtual_user_or_response(household, virtual_user_id):
    membership = HouseholdMember.objects.filter(
        household=household,
        user_id=virtual_user_id,
    ).select_related(
        'user',
    ).first()

    if not membership:
        return None, Response(
            {
                'detail': 'Thành viên này không thuộc nhóm.'
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if not is_virtual_user(membership.user):
        return None, Response(
            {
                'detail': 'Chỉ được xem giùm thành viên ảo.'
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return membership.user, None

class DefaultPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class HouseholdListCreateView(
    generics.ListCreateAPIView
):
    serializer_class = HouseholdSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return HouseholdListSerializer

        return HouseholdSerializer

    def get_queryset(self):
        household_ids = HouseholdMember.objects.filter(
            user=self.request.user,
        ).values(
            'household_id',
        )

        return Household.objects.filter(
            id__in=household_ids,
            is_active=True,
        ).select_related(
            'owner',
        ).annotate(
            member_count=Count(
                'members',
                distinct=True,
            ),
        ).order_by(
            '-updated_at',
        )

    @transaction.atomic
    def perform_create(self, serializer):
        household = serializer.save(
            owner=self.request.user
        )

        HouseholdMember.objects.create(
            household=household,
            user=self.request.user,
            role=HouseholdMember.Role.OWNER
        )

        Activity.objects.create(
            household=household,
            actor=self.request.user,
            activity_type=(
                Activity.ActivityType
                .MEMBER_JOINED
            ),
            title=(
                f'{self.request.user.email} '
                f'đã tạo nhóm'
            ),
        )


class HouseholdSummaryListView(
    generics.ListAPIView
):
    serializer_class = HouseholdSummarySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination

    def get_queryset(self):
        current_user = self.request.user

        household_ids = HouseholdMember.objects.filter(
            user=current_user,
        ).values(
            'household_id',
        )

        latest_activity_title = Activity.objects.filter(
            household_id=OuterRef('pk'),
        ).order_by(
            '-created_at',
        ).values(
            'title',
        )[:1]

        relevant_debts = Debt.objects.filter(
            is_paid=False,
        ).filter(
            Q(from_user=current_user) |
            Q(to_user=current_user)
        )

        return Household.objects.filter(
            id__in=household_ids,
            is_active=True,
        ).annotate(
            summary_member_count=Count(
                'members',
                distinct=True,
            ),
            summary_expense_count=Count(
                'expenses',
                distinct=True,
            ),
            summary_latest_activity_title=Subquery(
                latest_activity_title,
            ),
        ).prefetch_related(
            Prefetch(
                'debts',
                queryset=relevant_debts,
                to_attr='summary_debts',
            ),
        ).order_by(
            '-updated_at',
        )


class HouseholdDetailView(
    generics.RetrieveDestroyAPIView
):
    serializer_class = HouseholdSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Household.objects.filter(
            is_active=True,
            members__user=self.request.user
        ).prefetch_related(
            'members',
            'members__user',
        ).distinct()

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        household = Household.objects.select_for_update().filter(
            id=kwargs.get('pk'),
            is_active=True,
        ).first()

        if not household:
            return Response(
                {
                    'detail':
                    'Không tìm thấy nhóm.'
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        membership = HouseholdMember.objects.filter(
            household=household,
            user=request.user,
        ).first()

        if not membership:
            return Response(
                {
                    'detail':
                    'Bạn không thuộc nhóm này.'
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if membership.role != HouseholdMember.Role.OWNER:
            return Response(
                {
                    'detail':
                    'Chỉ chủ nhóm mới được xóa nhóm.'
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        has_unpaid_debt = Debt.objects.filter(
            household=household,
            is_paid=False,
        ).exists()

        if has_unpaid_debt:
            return Response(
                {
                    'detail':
                    'Không thể xóa nhóm khi còn công nợ chưa thanh toán.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        household.is_active = False
        household.save(
            update_fields=[
                'is_active',
                'updated_at',
            ]
        )

        Activity.objects.create(
            household=household,
            actor=request.user,
            activity_type=(
                Activity.ActivityType.HOUSEHOLD_DELETED
            ),
            title=f'{request.user.email} đã xóa nhóm',
            metadata={
                'action': 'household_deleted',
                'household_id': str(household.id),
                'household_name': household.name,
            },
        )

        return Response(
            {
                'message': 'Đã xóa nhóm.'
            },
            status=status.HTTP_200_OK,
        )


class JoinHouseholdView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = JoinHouseholdSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        invite_code = serializer.validated_data[
            'invite_code'
        ]

        household = Household.objects.select_for_update().filter(
            invite_code=invite_code,
            is_active=True
        ).first()

        if not household:
            return Response(
                {
                    'detail':
                    'Mã mời không hợp lệ.'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        if HouseholdMember.objects.filter(
            household=household,
            user=request.user
        ).exists():
            return Response(
                {
                    'detail':
                    'Bạn đã ở trong nhóm.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            HouseholdMember.objects.create(
                household=household,
                user=request.user,
                role=HouseholdMember.Role.MEMBER
            )
        except IntegrityError:
            return Response(
                {
                    'detail':
                    'Bạn đã ở trong nhóm.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        Activity.objects.create(
            household=household,
            actor=request.user,
            activity_type=Activity.ActivityType.MEMBER_JOINED,
            title=(
                f'{request.user.email} '
                f'đã tham gia nhóm'
            ),
        )

        household.refresh_from_db()

        response_serializer = HouseholdSerializer(
            household,
            context={
                'request': request
            }
        )

        return Response(
            {
                'message':
                'Tham gia nhóm thành công.',
                'household':
                response_serializer.data
            },
            status=status.HTTP_200_OK
        )


class AddHouseholdMemberView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, household_id):
        input_serializer = AddHouseholdMemberSerializer(
            data=request.data,
        )
        input_serializer.is_valid(
            raise_exception=True,
        )

        email = input_serializer.validated_data[
            'email'
        ]
        role = input_serializer.validated_data[
            'role'
        ]

        household = Household.objects.select_for_update().filter(
            id=household_id,
            is_active=True,
            members__user=request.user,
        ).first()

        if not household:
            return Response(
                {
                    'detail':
                    'Không tìm thấy nhóm hoặc bạn không thuộc nhóm này.'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        owner_membership = HouseholdMember.objects.filter(
            household=household,
            user=request.user,
            role=HouseholdMember.Role.OWNER,
        ).first()

        if not owner_membership:
            return Response(
                {
                    'detail':
                    'Chỉ chủ nhóm mới được thêm thành viên.'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        user = User.objects.filter(
            email__iexact=email
        ).first()

        if not user:
            return Response(
                {
                    'detail':
                    'Không tìm thấy tài khoản với email này.'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        if HouseholdMember.objects.filter(
            household=household,
            user=user
        ).exists():
            return Response(
                {
                    'detail':
                    'Người này đã ở trong nhóm.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            HouseholdMember.objects.create(
                household=household,
                user=user,
                role=role,
            )
        except IntegrityError:
            return Response(
                {
                    'detail':
                    'Người này đã ở trong nhóm.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        Activity.objects.create(
            household=household,
            actor=request.user,
            activity_type=Activity.ActivityType.MEMBER_JOINED,
            title=(
                f'{request.user.email} '
                f'đã thêm {user.email} vào nhóm'
            ),
            metadata={
                'added_user_email': user.email,
                'role': role,
            },
        )

        household.save(
            update_fields=[
                'updated_at',
            ]
        )

        household.refresh_from_db()

        response_serializer = HouseholdSerializer(
            household,
            context={
                'request': request
            }
        )

        return Response(
            {
                'message': 'Đã thêm thành viên.',
                'household': response_serializer.data,
            },
            status=status.HTTP_201_CREATED
        )


class CreateVirtualHouseholdMemberView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, household_id):
        serializer = CreateVirtualMemberSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        household = Household.objects.select_for_update().filter(
            id=household_id,
            is_active=True,
        ).first()

        if not household:
            return Response(
                {
                    'detail':
                    'Không tìm thấy nhóm.'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        owner_membership = HouseholdMember.objects.filter(
            household=household,
            user=request.user,
            role=HouseholdMember.Role.OWNER,
        ).first()

        if not owner_membership:
            return Response(
                {
                    'detail':
                    'Chỉ chủ nhóm mới được tạo thành viên ảo.'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        display_name = serializer.validated_data['display_name']
        note = serializer.validated_data.get('note', '')

        exists_name = HouseholdMember.objects.filter(
            household=household,
            user__email__iendswith=VIRTUAL_MEMBER_EMAIL_DOMAIN,
            user__full_name__iexact=display_name,
        ).exists()

        if exists_name:
            return Response(
                {
                    'detail':
                    'Nhóm đã có thành viên ảo cùng tên.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        username = (
            f'virtual_{household.id.hex[:10]}_'
            f'{secrets.token_hex(4)}'
        )
        email = make_virtual_email(household)

        while User.objects.filter(email=email).exists():
            email = make_virtual_email(household)

        while User.objects.filter(username=username).exists():
            username = (
                f'virtual_{household.id.hex[:10]}_'
                f'{secrets.token_hex(4)}'
            )

        virtual_user = User.objects.create(
            email=email,
            username=username,
            full_name=display_name,
            is_active=False,
            email_verified=True,
        )
        virtual_user.set_unusable_password()

        try:
            virtual_user.auth_provider = 'virtual'
        except Exception:
            pass

        virtual_user.save()

        HouseholdMember.objects.create(
            household=household,
            user=virtual_user,
            role=HouseholdMember.Role.MEMBER,
        )

        actor_name = get_user_display_name(request.user)

        Activity.objects.create(
            household=household,
            actor=request.user,
            activity_type=(
                Activity.ActivityType
                .VIRTUAL_MEMBER_CREATED
            ),
            title=(
                f'{actor_name} đã tạo thành viên ảo {display_name}'
            ),
            metadata={
                'action': 'virtual_member_created',
                'virtual_user_id': str(virtual_user.id),
                'virtual_user_name': display_name,
                'note': note,
            },
        )

        household.save(
            update_fields=[
                'updated_at',
            ]
        )

        household.refresh_from_db()

        response_serializer = HouseholdSerializer(
            household,
            context={
                'request': request
            }
        )

        return Response(
            {
                'message': 'Đã tạo thành viên ảo.',
                'household': response_serializer.data,
            },
            status=status.HTTP_201_CREATED
        )


class KickHouseholdMemberView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def delete(self, request, household_id, member_id):
        household = Household.objects.select_for_update().filter(
            id=household_id,
            is_active=True,
        ).first()

        if not household:
            return Response(
                {
                    'detail':
                    'Không tìm thấy nhóm.'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        owner_membership = HouseholdMember.objects.filter(
            household=household,
            user=request.user,
            role=HouseholdMember.Role.OWNER,
        ).first()

        if not owner_membership:
            return Response(
                {
                    'detail':
                    'Chỉ chủ nhóm mới được xóa thành viên.'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        target_membership = (
            HouseholdMember.objects.select_for_update()
            .select_related('user')
            .filter(
                id=member_id,
                household=household,
            )
            .first()
        )

        if not target_membership:
            return Response(
                {
                    'detail':
                    'Thành viên không tồn tại trong nhóm.'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        if target_membership.user_id == request.user.id:
            return Response(
                {
                    'detail':
                    'Bạn không thể tự xóa chính mình. Hãy dùng chức năng rời nhóm.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if target_membership.role == HouseholdMember.Role.OWNER:
            return Response(
                {
                    'detail':
                    'Không thể xóa chủ nhóm.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        has_unpaid_debt = Debt.objects.filter(
            household=household,
            is_paid=False,
        ).filter(
            from_user=target_membership.user
        ).exists() or Debt.objects.filter(
            household=household,
            is_paid=False,
        ).filter(
            to_user=target_membership.user
        ).exists()

        if has_unpaid_debt:
            return Response(
                {
                    'detail':
                    'Không thể xóa thành viên khi còn công nợ chưa thanh toán.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        kicked_user = target_membership.user
        kicked_email = kicked_user.email
        kicked_name = get_user_display_name(kicked_user)
        actor_name = get_user_display_name(request.user)

        Activity.objects.create(
            household=household,
            actor=request.user,
            activity_type=(
                Activity.ActivityType.MEMBER_KICKED
            ),
            title=(
                f'{actor_name} đã xóa {kicked_name} khỏi nhóm'
            ),
            metadata={
                'action': 'member_kicked',
                'kicked_user_id': str(kicked_user.id),
                'kicked_user_email': kicked_email,
            },
        )

        target_membership.delete()

        household.save(
            update_fields=[
                'updated_at',
            ]
        )

        household.refresh_from_db()

        response_serializer = HouseholdSerializer(
            household,
            context={
                'request': request
            }
        )

        return Response(
            {
                'message':
                'Đã xóa thành viên khỏi nhóm.',
                'household':
                response_serializer.data,
            },
            status=status.HTTP_200_OK
        )


class ActivityListView(generics.ListAPIView):
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination

    def get_queryset(self):
        household_id = self.kwargs[
            'household_id'
        ]

        return Activity.objects.filter(
            household_id=household_id,
            household__members__user=(
                self.request.user
            )
        ).select_related(
            'actor',
            'household'
        ).order_by('-created_at')


class AllActivityListView(
    generics.ListAPIView
):
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination

    def get_queryset(self):
        return Activity.objects.filter(
            household__members__user=(
                self.request.user
            )
        ).select_related(
            'actor',
            'household'
        ).order_by('-created_at')


class LeaveHouseholdView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, household_id):
        household = Household.objects.select_for_update().filter(
            id=household_id,
            is_active=True,
            members__user=request.user,
        ).first()

        if not household:
            return Response(
                {
                    'detail':
                    'Không tìm thấy nhóm hoặc bạn không thuộc nhóm này.'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        membership = HouseholdMember.objects.select_for_update().filter(
            household=household,
            user=request.user,
        ).first()

        if not membership:
            return Response(
                {
                    'detail':
                    'Bạn không thuộc nhóm này.'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        member_count = HouseholdMember.objects.filter(
            household=household
        ).count()

        if (
            membership.role == HouseholdMember.Role.OWNER
            and member_count > 1
        ):
            return Response(
                {
                    'detail':
                    'Chủ nhóm không thể rời khi nhóm còn thành viên khác.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        has_unpaid_debt = Debt.objects.filter(
            household=household,
            is_paid=False,
        ).filter(
            Q(from_user=request.user) |
            Q(to_user=request.user)
        ).exists()

        if has_unpaid_debt:
            return Response(
                {
                    'detail':
                    'Không thể rời nhóm khi còn công nợ chưa thanh toán liên quan đến bạn.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        Activity.objects.create(
            household=household,
            actor=request.user,
            activity_type=Activity.ActivityType.MEMBER_LEFT,
            title=f'{request.user.email} đã rời nhóm',
            metadata={
                'action': 'member_left',
                'user_email': request.user.email,
            },
        )

        membership.delete()

        if member_count == 1:
            household.is_active = False
            household.save(
                update_fields=[
                    'is_active',
                    'updated_at',
                ]
            )
        else:
            household.save(
                update_fields=[
                    'updated_at',
                ]
            )

        return Response(
            {
                'message': 'Bạn đã rời nhóm.'
            },
            status=status.HTTP_200_OK
        )
    
class MyDebtSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, household_id):
        household = Household.objects.filter(
            id=household_id,
            is_active=True,
            members__user=request.user,
        ).first()

        if not household:
            return Response(
                {
                    'detail':
                    'Không tìm thấy nhóm hoặc bạn không thuộc nhóm này.'
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        current_user = request.user

        summary_rows, users_by_id = (
            get_debt_summary_rows(
                household=household,
                subject_user=current_user,
            )
        )

        i_owe = []
        owed_to_me = []

        total_i_owe = 0
        total_owed_to_me = 0

        for row in summary_rows:
            other_user = users_by_id.get(
                row['other_user_id']
            )

            if not other_user:
                continue

            i_owe_amount = money_to_int(
                row['subject_owes_amount']
            )

            owed_to_me_amount = money_to_int(
                row['owed_to_subject_amount']
            )

            net_amount = (
                i_owe_amount -
                owed_to_me_amount
            )

            if net_amount == 0:
                continue

            user_data = serialize_debt_user(
                other_user,
                request,
            )

            response_item = {
                'other_user_id':
                    user_data['other_user_id'],
                'other_name':
                    user_data['other_name'],
                'other_email':
                    user_data['other_email'],
                'other_avatar':
                    user_data['other_avatar'],
                'is_virtual':
                    user_data['is_virtual'],
                'amount': abs(net_amount),
                'expense_count':
                    row['expense_count'],
            }

            if net_amount > 0:
                total_i_owe += net_amount
                i_owe.append(response_item)
            else:
                amount_to_receive = abs(
                    net_amount
                )

                total_owed_to_me += (
                    amount_to_receive
                )

                owed_to_me.append(
                    response_item
                )

        i_owe.sort(
            key=lambda item: item['amount'],
            reverse=True,
        )

        owed_to_me.sort(
            key=lambda item: item['amount'],
            reverse=True,
        )

        return Response(
            {
                'household_id': str(household.id),
                'user_id': current_user.id,
                'total_i_owe': total_i_owe,
                'total_owed_to_me': total_owed_to_me,
                'i_owe': i_owe,
                'owed_to_me': owed_to_me,
            },
            status=status.HTTP_200_OK,
        )


class MyDebtDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, household_id, other_user_id):
        household = Household.objects.filter(
            id=household_id,
            is_active=True,
            members__user=request.user,
        ).first()

        if not household:
            return Response(
                {
                    'detail':
                    'Không tìm thấy nhóm hoặc bạn không thuộc nhóm này.'
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        other_membership = HouseholdMember.objects.filter(
            household=household,
            user_id=other_user_id,
        ).select_related(
            'user',
        ).first()

        if not other_membership:
            return Response(
                {
                    'detail':
                    'Người này không thuộc nhóm.'
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        current_user = request.user
        other_user = other_membership.user

        paid_limit_raw = request.query_params.get(
            'paid_limit',
            '20',
        )

        try:
            paid_limit = int(paid_limit_raw)
        except (TypeError, ValueError):
            return Response(
                {
                    'detail':
                    'paid_limit phải là số nguyên.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if paid_limit < 1 or paid_limit > 100:
            return Response(
                {
                    'detail':
                    'paid_limit phải nằm trong khoảng từ 1 đến 100.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        include_legacy_items = (
            request.query_params.get(
                'include_legacy_items',
                'false',
            ).strip().lower()
            in ['1', 'true', 'yes']
        )

        pair_filter = (
            Q(
                from_user=current_user,
                to_user=other_user,
            ) |
            Q(
                from_user=other_user,
                to_user=current_user,
            )
        )

        debt_detail_queryset = Debt.objects.filter(
            household=household,
        ).filter(
            pair_filter,
        ).select_related(
            'from_user',
            'to_user',
            'expense',
            'expense__payer',
        ).prefetch_related(
            'payments',
            'payment_allocations',
            'payment_allocations__payment',
        )

        unpaid_debts = debt_detail_queryset.filter(
            is_paid=False,
        ).order_by(
            'expense__expense_date',
            'created_at',
        )

        paid_debt_rows = list(
            debt_detail_queryset.filter(
                is_paid=True,
            ).order_by(
                '-updated_at',
                '-created_at',
            )[:paid_limit + 1]
        )

        paid_items_has_more = (
            len(paid_debt_rows) > paid_limit
        )

        paid_debts = paid_debt_rows[
            :paid_limit
        ]

        total_i_owe = 0
        total_owed_to_me = 0

        unpaid_items = []
        paid_items = []

        for debt in unpaid_debts:
            if debt.from_user_id == current_user.id:
                direction = 'i_owe'
            else:
                direction = 'owed_to_me'

            item = serialize_debt_detail_item(
                debt=debt,
                direction=direction,
                request=request,
            )

            remaining_amount = item[
                'remaining_amount'
            ]

            if (
                item['status'] == 'paid'
                or remaining_amount <= 0
            ):
                paid_items.append(item)
                continue

            if direction == 'i_owe':
                total_i_owe += remaining_amount
            else:
                total_owed_to_me += remaining_amount

            unpaid_items.append(item)

        for debt in paid_debts:
            if debt.from_user_id == current_user.id:
                direction = 'i_owe'
            else:
                direction = 'owed_to_me'

            paid_items.append(
                serialize_debt_detail_item(
                    debt=debt,
                    direction=direction,
                    request=request,
                )
            )

        net_amount = total_i_owe - total_owed_to_me

        if net_amount > 0:
            net_direction = 'i_owe'
        elif net_amount < 0:
            net_direction = 'owed_to_me'
        else:
            net_direction = 'settled'

        other_user_data = serialize_debt_user(
            other_user,
            request,
        )

        other_name = other_user_data['other_name']

        if net_direction == 'i_owe':
            summary_display_text = f'Bạn còn nợ {other_name}'
        elif net_direction == 'owed_to_me':
            summary_display_text = f'{other_name} còn nợ bạn'
        else:
            summary_display_text = 'Hai bên đã thanh toán xong'

        pending_payment = None
        receiver_bank_info = None
        can_pay_now = False
        can_confirm_payment = False

        if net_direction == 'i_owe':
            pending_payment = get_pending_pair_payment(
                household=household,
                payer=current_user,
                receiver=other_user,
            )

            receiver_bank_info = serialize_bank_info(
                other_user
            )

            can_pay_now = (
                abs(net_amount) > 0 and
                pending_payment is None and
                not is_virtual_user(current_user) and
                not is_virtual_user(other_user)
            )

        elif net_direction == 'owed_to_me':
            pending_payment = get_pending_pair_payment(
                household=household,
                payer=other_user,
                receiver=current_user,
            )

            receiver_bank_info = serialize_bank_info(
                current_user
            )

            can_confirm_payment = (
                pending_payment is not None and
                pending_payment.receiver_id == current_user.id
            )

        payment_timeline = get_pair_payment_timeline(
            household=household,
            user_a=current_user,
            user_b=other_user,
            request=request,
        )

        if net_direction in ['i_owe', 'owed_to_me']:
            unpaid_items = [
                item
                for item in unpaid_items
                if item['direction'] == net_direction
            ]

            paid_items = [
                item
                for item in paid_items
                if item['direction'] == net_direction
            ]

        net_remaining_amount = abs(net_amount)

        return Response(
            {
                'household_id': str(household.id),
                'current_user_id': current_user.id,

                'other_user_id': other_user.id,
                'other_name': other_user_data['other_name'],
                'other_email': other_user_data['other_email'],
                'other_avatar': other_user_data['other_avatar'],
                'is_virtual': other_user_data['is_virtual'],

                'net_direction': net_direction,
                'net_amount': net_remaining_amount,
                'total_i_owe': total_i_owe,
                'total_owed_to_me': total_owed_to_me,

                'summary': {
                    'direction': net_direction,
                    'display_text': summary_display_text,
                    'remaining_amount': net_remaining_amount,
                },

                'unpaid_items': unpaid_items,
                'paid_items': paid_items,
                'paid_items_limit': paid_limit,
                'paid_items_has_more':
                    paid_items_has_more,

                **(
                    {
                        'items': unpaid_items,
                    }
                    if include_legacy_items
                    else {}
                ),

                'pending_payment': (
                    PaymentSerializer(
                        pending_payment,
                        context={'request': request},
                    ).data
                    if pending_payment
                    else None
                ),

                'receiver_bank_info': receiver_bank_info,

                'can_pay_now': can_pay_now,

                'permissions': {
                    'can_pay_now': can_pay_now,
                    'can_confirm_payment': can_confirm_payment,
                    'can_select_items_to_pay': can_pay_now,
                    'can_pay_custom_amount': can_pay_now,
                    'can_pay_full': can_pay_now,
                },

                'payment_timeline': payment_timeline,
            },
            status=status.HTTP_200_OK,
        )
    
class VirtualMemberDebtSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, household_id, virtual_user_id):
        household, error_response = get_owner_household_or_response(
            request,
            household_id,
        )

        if error_response:
            return error_response

        virtual_user, error_response = get_virtual_user_or_response(
            household,
            virtual_user_id,
        )

        if error_response:
            return error_response

        summary_rows, users_by_id = (
            get_debt_summary_rows(
                household=household,
                subject_user=virtual_user,
            )
        )

        virtual_owes = []
        owed_to_virtual = []

        total_virtual_owes = 0
        total_owed_to_virtual = 0

        for row in summary_rows:
            other_user = users_by_id.get(
                row['other_user_id']
            )

            if not other_user:
                continue

            virtual_owes_amount = money_to_int(
                row['subject_owes_amount']
            )

            owed_to_virtual_amount = money_to_int(
                row['owed_to_subject_amount']
            )

            net_amount = (
                virtual_owes_amount -
                owed_to_virtual_amount
            )

            if net_amount == 0:
                continue

            user_data = serialize_debt_user(
                other_user,
                request,
            )

            response_item = {
                'other_user_id':
                    user_data['other_user_id'],
                'other_name':
                    user_data['other_name'],
                'other_email':
                    user_data['other_email'],
                'other_avatar':
                    user_data['other_avatar'],
                'other_is_virtual':
                    user_data['is_virtual'],
                'amount': abs(net_amount),
                'expense_count':
                    row['expense_count'],
            }

            if net_amount > 0:
                total_virtual_owes += net_amount

                virtual_owes.append(
                    response_item
                )
            else:
                amount_to_receive = abs(
                    net_amount
                )

                total_owed_to_virtual += (
                    amount_to_receive
                )

                owed_to_virtual.append(
                    response_item
                )

        virtual_owes.sort(
            key=lambda item: item['amount'],
            reverse=True,
        )

        owed_to_virtual.sort(
            key=lambda item: item['amount'],
            reverse=True,
        )

        return Response(
            {
                'household_id': str(household.id),
                'virtual_user_id': virtual_user.id,
                'virtual_name': get_user_display_name(
                    virtual_user
                ),
                'virtual_email': virtual_user.email,
                'total_virtual_owes': total_virtual_owes,
                'total_owed_to_virtual': total_owed_to_virtual,
                'virtual_owes': virtual_owes,
                'owed_to_virtual': owed_to_virtual,
            },
            status=status.HTTP_200_OK,
        )


class VirtualMemberDebtDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(
        self,
        request,
        household_id,
        virtual_user_id,
        other_user_id,
    ):
        household, error_response = get_virtual_pair_household_or_response(
            request,
            household_id,
            other_user_id,
        )

        if error_response:
            return error_response

        virtual_user, error_response = get_virtual_user_or_response(
            household,
            virtual_user_id,
        )

        if error_response:
            return error_response

        other_membership = HouseholdMember.objects.filter(
            household=household,
            user_id=other_user_id,
        ).select_related(
            'user',
        ).first()

        if not other_membership:
            return Response(
                {
                    'detail': 'Người này không thuộc nhóm.'
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        other_user = other_membership.user

        debts = Debt.objects.filter(
            household=household,
            is_paid=False,
        ).filter(
            Q(
                from_user=virtual_user,
                to_user=other_user,
            ) |
            Q(
                from_user=other_user,
                to_user=virtual_user,
            )
        ).select_related(
            'from_user',
            'to_user',
            'expense',
            'expense__payer',
        ).order_by(
            '-created_at',
        )

        total_virtual_owes = 0
        total_owed_to_virtual = 0
        items = []

        for debt in debts:
            amount = debt_remaining_to_int(debt)

            if amount <= 0:
                continue

            if debt.from_user_id == virtual_user.id:
                direction = 'virtual_owes'
                total_virtual_owes += amount
            else:
                direction = 'owed_to_virtual'
                total_owed_to_virtual += amount

            items.append(
                {
                    'debt_id': str(debt.id),
                    'expense_id': str(debt.expense_id),
                    'expense_title': debt.expense.title,
                    'expense_date': (
                        debt.expense.expense_date.isoformat()
                        if debt.expense.expense_date
                        else ''
                    ),
                    **serialize_debt_payer(
                        debt.expense.payer,
                        request,
                    ),
                    'from_user_name': get_user_display_name(
                        debt.from_user
                    ),
                    'to_user_name': get_user_display_name(
                        debt.to_user
                    ),
                    'direction': direction,
                    'amount': amount,
                    'original_amount': money_to_int(debt.amount),
                    'paid_amount': money_to_int(
                        getattr(debt, 'paid_amount', 0)
                    ),
                }
            )

        net_amount = total_virtual_owes - total_owed_to_virtual

        if net_amount > 0:
            net_direction = 'virtual_owes'
        elif net_amount < 0:
            net_direction = 'owed_to_virtual'
        else:
            net_direction = 'settled'

        other_user_data = serialize_debt_user(
            other_user,
            request,
        )

        return Response(
            {
                'household_id': str(household.id),
                'virtual_user_id': virtual_user.id,
                'virtual_name': get_user_display_name(
                    virtual_user
                ),
                'other_user_id': other_user.id,
                'other_name': other_user_data['other_name'],
                'other_email': other_user_data['other_email'],
                'other_avatar': other_user_data['other_avatar'],
                'other_is_virtual': other_user_data['is_virtual'],
                'net_direction': net_direction,
                'net_amount': abs(net_amount),
                'total_virtual_owes': total_virtual_owes,
                'total_owed_to_virtual': total_owed_to_virtual,
                'pending_payment': None,
                'receiver_bank_info': None,
                'can_pay_now': False,
                'can_settle_virtual': abs(net_amount) > 0,
                'payment_timeline': [],
                'items': items,

            },
            status=status.HTTP_200_OK,
        )


class SettleVirtualMemberDebtPairView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(
        self,
        request,
        household_id,
        virtual_user_id,
        other_user_id,
    ):
        household, error_response = get_virtual_pair_household_or_response(
            request,
            household_id,
            other_user_id,
        )

        if error_response:
            return error_response

        virtual_user, error_response = get_virtual_user_or_response(
            household,
            virtual_user_id,
        )

        if error_response:
            return error_response

        other_membership = HouseholdMember.objects.filter(
            household=household,
            user_id=other_user_id,
        ).select_related(
            'user',
        ).first()

        if not other_membership:
            return Response(
                {
                    'detail': 'Người này không thuộc nhóm.'
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        other_user = other_membership.user

        debts = list(
            Debt.objects.select_for_update().filter(
                household=household,
                is_paid=False,
            ).filter(
                Q(
                    from_user=virtual_user,
                    to_user=other_user,
                ) |
                Q(
                    from_user=other_user,
                    to_user=virtual_user,
                )
            )
        )

        if not debts:
            return Response(
                {
                    'detail':
                    'Không còn công nợ chưa xử lý giữa hai thành viên này.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        settled_total_amount = 0

        for debt in debts:
            settled_total_amount += debt_remaining_to_int(debt)
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
                'message': 'Đã đánh dấu xử lý ngoài đời.',
                'settled_debt_count': len(debts),
                'settled_total_amount': settled_total_amount,
            },
            status=status.HTTP_200_OK,
        )