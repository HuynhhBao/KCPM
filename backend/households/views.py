import secrets

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db import transaction
from django.db.models import Q

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
    CreateVirtualMemberSerializer,
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


def serialize_debt_user(user, request=None):
    avatar_url = ''

    if getattr(user, 'avatar', None) and request:
        avatar_url = request.build_absolute_uri(
            user.avatar.url
        )

    return {
        'other_user_id': user.id,
        'other_name': get_user_display_name(user),
        'other_email': user.email,
        'other_avatar': avatar_url,
        'is_virtual': is_virtual_user(user),
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


class HouseholdListCreateView(
    generics.ListCreateAPIView
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
        ).distinct().order_by('-updated_at')

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

    def get_queryset(self):
        return Household.objects.filter(
            is_active=True,
            members__user=self.request.user
        ).prefetch_related(
            'members',
            'expenses',
            'debts',
            'activities',
        ).distinct().order_by('-updated_at')


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
            activity_type=Activity.ActivityType.MEMBER_JOINED,
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
        email = (
            request.data.get('email', '')
            .strip()
            .lower()
        )

        role = request.data.get(
            'role',
            HouseholdMember.Role.MEMBER
        )

        if not email:
            return Response(
                {
                    'detail':
                    'Vui lòng nhập email thành viên.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if email.endswith(VIRTUAL_MEMBER_EMAIL_DOMAIN):
            return Response(
                {
                    'detail':
                    'Email này thuộc thành viên ảo, không thể thêm như tài khoản thật.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if role not in [
            HouseholdMember.Role.MEMBER,
            HouseholdMember.Role.OWNER,
        ]:
            return Response(
                {
                    'detail':
                    'Vai trò thành viên không hợp lệ.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

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
            activity_type=Activity.ActivityType.MEMBER_JOINED,
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
            activity_type=Activity.ActivityType.MEMBER_JOINED,
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


class DefaultPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


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

        Activity.objects.create(
            household=household,
            actor=request.user,
            activity_type=Activity.ActivityType.MEMBER_JOINED,
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

        debts = Debt.objects.filter(
            household=household,
            is_paid=False,
        ).filter(
            Q(from_user=current_user) |
            Q(to_user=current_user)
        ).select_related(
            'from_user',
            'to_user',
            'expense',
        )

        pair_map = {}

        for debt in debts:
            if debt.from_user_id == current_user.id:
                other_user = debt.to_user
                direction = 'i_owe'
            else:
                other_user = debt.from_user
                direction = 'owed_to_me'

            if other_user.id not in pair_map:
                user_data = serialize_debt_user(
                    other_user,
                    request,
                )

                pair_map[other_user.id] = {
                    **user_data,
                    'i_owe_amount': 0,
                    'owed_to_me_amount': 0,
                    'expense_ids': set(),
                }

            amount = debt_remaining_to_int(debt)

            if amount <= 0:
                continue

            if direction == 'i_owe':
                pair_map[other_user.id]['i_owe_amount'] += amount
            else:
                pair_map[other_user.id]['owed_to_me_amount'] += amount

            pair_map[other_user.id]['expense_ids'].add(
                str(debt.expense_id)
            )

        i_owe = []
        owed_to_me = []

        total_i_owe = 0
        total_owed_to_me = 0

        for item in pair_map.values():
            net_amount = (
                item['i_owe_amount'] -
                item['owed_to_me_amount']
            )

            if net_amount == 0:
                continue

            response_item = {
                'other_user_id': item['other_user_id'],
                'other_name': item['other_name'],
                'other_email': item['other_email'],
                'other_avatar': item['other_avatar'],
                'is_virtual': item['is_virtual'],
                'amount': abs(net_amount),
                'expense_count': len(item['expense_ids']),
            }

            if net_amount > 0:
                total_i_owe += net_amount
                i_owe.append(response_item)
            else:
                total_owed_to_me += abs(net_amount)
                owed_to_me.append(response_item)

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

        debts = Debt.objects.filter(
            household=household,
            is_paid=False,
        ).filter(
            Q(
                from_user=current_user,
                to_user=other_user,
            ) |
            Q(
                from_user=other_user,
                to_user=current_user,
            )
        ).select_related(
            'from_user',
            'to_user',
            'expense',
            'expense__payer',
        ).order_by(
            '-created_at',
        )

        total_i_owe = 0
        total_owed_to_me = 0
        items = []

        for debt in debts:
            amount = debt_remaining_to_int(debt)

            if amount <= 0:
                continue

            if debt.from_user_id == current_user.id:
                direction = 'i_owe'
                total_i_owe += amount
            else:
                direction = 'owed_to_me'
                total_owed_to_me += amount

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
                    'payer_name': get_user_display_name(
                        debt.expense.payer
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

        pending_payment = None
        receiver_bank_info = None
        can_pay_now = False

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

        payment_timeline = get_pair_payment_timeline(
            household=household,
            user_a=current_user,
            user_b=other_user,
            request=request,
        )

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
                'net_amount': abs(net_amount),
                'total_i_owe': total_i_owe,
                'total_owed_to_me': total_owed_to_me,
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
                'payment_timeline': payment_timeline,
                'items': items,
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

        debts = Debt.objects.filter(
            household=household,
            is_paid=False,
        ).filter(
            Q(from_user=virtual_user) |
            Q(to_user=virtual_user)
        ).select_related(
            'from_user',
            'to_user',
            'expense',
        )

        pair_map = {}

        for debt in debts:
            if debt.from_user_id == virtual_user.id:
                other_user = debt.to_user
                direction = 'virtual_owes'
            else:
                other_user = debt.from_user
                direction = 'owed_to_virtual'

            if other_user.id not in pair_map:
                user_data = serialize_debt_user(
                    other_user,
                    request,
                )

                pair_map[other_user.id] = {
                    'other_user_id': user_data['other_user_id'],
                    'other_name': user_data['other_name'],
                    'other_email': user_data['other_email'],
                    'other_avatar': user_data['other_avatar'],
                    'other_is_virtual': user_data['is_virtual'],
                    'virtual_owes_amount': 0,
                    'owed_to_virtual_amount': 0,
                    'expense_ids': set(),
                }

            amount = debt_remaining_to_int(debt)

            if amount <= 0:
                continue

            if direction == 'virtual_owes':
                pair_map[other_user.id][
                    'virtual_owes_amount'
                ] += amount
            else:
                pair_map[other_user.id][
                    'owed_to_virtual_amount'
                ] += amount

            pair_map[other_user.id]['expense_ids'].add(
                str(debt.expense_id)
            )

        virtual_owes = []
        owed_to_virtual = []

        total_virtual_owes = 0
        total_owed_to_virtual = 0

        for item in pair_map.values():
            net_amount = (
                item['virtual_owes_amount'] -
                item['owed_to_virtual_amount']
            )

            if net_amount == 0:
                continue

            response_item = {
                'other_user_id': item['other_user_id'],
                'other_name': item['other_name'],
                'other_email': item['other_email'],
                'other_avatar': item['other_avatar'],
                'other_is_virtual': item['other_is_virtual'],
                'amount': abs(net_amount),
                'expense_count': len(item['expense_ids']),
            }

            if net_amount > 0:
                total_virtual_owes += net_amount
                virtual_owes.append(response_item)
            else:
                total_owed_to_virtual += abs(net_amount)
                owed_to_virtual.append(response_item)

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
                    'payer_name': get_user_display_name(
                        debt.expense.payer
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