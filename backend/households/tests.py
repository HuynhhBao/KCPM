from unittest.mock import MagicMock, patch
import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework import status
from rest_framework.test import (
    APIRequestFactory,
    force_authenticate,
)

from households.models import (
    Activity,
    Household,
    HouseholdMember,
)
from households.urls import urlpatterns
from households.views import (
    AddHouseholdMemberView,
    CreateVirtualHouseholdMemberView,
    HouseholdDetailView,
    HouseholdListCreateView,
    HouseholdSummaryListView,
    KickHouseholdMemberView,
    LeaveHouseholdView,
    MyDebtDetailView,
    MyDebtSummaryView,
)


User = get_user_model()


class HouseholdPart1RegressionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.owner = self.create_user(
            email='owner@example.com',
            username='owner_test',
            full_name='Chủ nhóm',
        )

        self.member = self.create_user(
            email='member@example.com',
            username='member_test',
            full_name='Thành viên',
        )

        self.household = Household.objects.create(
            name='Nhóm kiểm thử',
            description='Nhóm dùng cho regression test',
            owner=self.owner,
            invite_code='TEST0001',
            is_active=True,
        )

        HouseholdMember.objects.create(
            household=self.household,
            user=self.owner,
            role=HouseholdMember.Role.OWNER,
        )

        HouseholdMember.objects.create(
            household=self.household,
            user=self.member,
            role=HouseholdMember.Role.MEMBER,
        )

        Activity.objects.create(
            household=self.household,
            actor=self.owner,
            activity_type=(
                Activity.ActivityType.MEMBER_JOINED
            ),
            title='Hoạt động kiểm thử ban đầu',
        )

    def create_user(
        self,
        *,
        email,
        username,
        full_name,
    ):
        model_field_names = {
            field.name
            for field in User._meta.fields
        }

        user_data = {}

        if 'email' in model_field_names:
            user_data['email'] = email

        if 'username' in model_field_names:
            user_data['username'] = username

        if 'full_name' in model_field_names:
            user_data['full_name'] = full_name

        if 'is_active' in model_field_names:
            user_data['is_active'] = True

        if 'email_verified' in model_field_names:
            user_data['email_verified'] = True

        user = User.objects.create(
            **user_data
        )

        user.set_password(
            'TestPassword123!'
        )
        user.save()

        return user

    def authenticate(
        self,
        request,
        user=None,
    ):
        force_authenticate(
            request,
            user=user or self.owner,
        )

        return request

    def test_household_list_is_paginated_and_compact(self):
        request = self.factory.get(
            '/api/households/',
        )
        self.authenticate(request)

        response = HouseholdListCreateView.as_view()(
            request
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            'count',
            response.data,
        )
        self.assertIn(
            'next',
            response.data,
        )
        self.assertIn(
            'previous',
            response.data,
        )
        self.assertIn(
            'results',
            response.data,
        )

        self.assertEqual(
            response.data['count'],
            1,
        )

        result = response.data['results'][0]

        self.assertEqual(
            result['id'],
            str(self.household.id),
        )
        self.assertEqual(
            result['member_count'],
            2,
        )
        self.assertNotIn(
            'members',
            result,
        )

    def test_household_summary_uses_optimized_values(self):
        request = self.factory.get(
            '/api/households/summary/',
        )
        self.authenticate(request)

        response = HouseholdSummaryListView.as_view()(
            request
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data['count'],
            1,
        )

        result = response.data['results'][0]

        self.assertEqual(
            result['member_count'],
            2,
        )
        self.assertEqual(
            result['expense_count'],
            0,
        )
        self.assertEqual(
            result['total_owe'],
            0,
        )
        self.assertEqual(
            result['total_receive'],
            0,
        )
        self.assertEqual(
            result['latest_activity'],
            'Hoạt động kiểm thử ban đầu',
        )

    def test_add_member_with_null_email_returns_400(self):
        request = self.factory.post(
            '/members/add/',
            {
                'email': None,
                'role': 'member',
            },
            format='json',
        )
        self.authenticate(request)

        response = AddHouseholdMemberView.as_view()(
            request,
            household_id=self.household.id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            'email',
            response.data,
        )

    def test_add_member_with_invalid_role_returns_400(self):
        request = self.factory.post(
            '/members/add/',
            {
                'email': 'valid@example.com',
                'role': 'admin',
            },
            format='json',
        )
        self.authenticate(request)

        response = AddHouseholdMemberView.as_view()(
            request,
            household_id=self.household.id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            'role',
            response.data,
        )

    @patch(
        'households.views.Debt.objects.filter'
    )
    def test_member_cannot_leave_with_unpaid_debt(
        self,
        mocked_debt_filter,
    ):
        first_queryset = MagicMock()
        second_queryset = MagicMock()

        mocked_debt_filter.return_value = (
            first_queryset
        )
        first_queryset.filter.return_value = (
            second_queryset
        )
        second_queryset.exists.return_value = True

        request = self.factory.post(
            '/leave/',
            {},
            format='json',
        )
        self.authenticate(
            request,
            user=self.member,
        )

        response = LeaveHouseholdView.as_view()(
            request,
            household_id=self.household.id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data['detail'],
            (
                'Không thể rời nhóm khi còn công nợ '
                'chưa thanh toán liên quan đến bạn.'
            ),
        )

        membership_exists = (
            HouseholdMember.objects.filter(
                household=self.household,
                user=self.member,
            ).exists()
        )

        self.assertTrue(
            membership_exists
        )

    def test_debt_detail_rejects_invalid_paid_limit(self):
        request = self.factory.get(
            '/my-debts/detail/',
            {
                'paid_limit': 'abc',
            },
        )
        self.authenticate(request)

        response = MyDebtDetailView.as_view()(
            request,
            household_id=self.household.id,
            other_user_id=self.member.id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data['detail'],
            'paid_limit phải là số nguyên.',
        )

    def test_debt_detail_does_not_return_legacy_items_by_default(
        self,
    ):
        request = self.factory.get(
            '/my-debts/detail/',
        )
        self.authenticate(request)

        response = MyDebtDetailView.as_view()(
            request,
            household_id=self.household.id,
            other_user_id=self.member.id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertIn(
            'unpaid_items',
            response.data,
        )
        self.assertIn(
            'paid_items',
            response.data,
        )
        self.assertIn(
            'paid_items_limit',
            response.data,
        )
        self.assertIn(
            'paid_items_has_more',
            response.data,
        )
        self.assertNotIn(
            'items',
            response.data,
        )
        self.assertEqual(
            response.data['paid_items_limit'],
            20,
        )

    def test_debt_detail_can_return_legacy_items_when_requested(
        self,
    ):
        request = self.factory.get(
            '/my-debts/detail/',
            {
                'include_legacy_items': 'true',
            },
        )
        self.authenticate(request)

        response = MyDebtDetailView.as_view()(
            request,
            household_id=self.household.id,
            other_user_id=self.member.id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertIn(
            'items',
            response.data,
        )
        self.assertEqual(
            response.data['items'],
            response.data['unpaid_items'],
        )

    def test_virtual_member_activity_type_is_correct(self):
        request = self.factory.post(
            '/members/virtual/',
            {
                'display_name':
                    'Thành viên ảo kiểm thử',
                'note':
                    'Kiểm tra activity type',
            },
            format='json',
        )
        self.authenticate(request)

        response = (
            CreateVirtualHouseholdMemberView
            .as_view()
        )(
            request,
            household_id=self.household.id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        activity = Activity.objects.filter(
            household=self.household,
            metadata__action=(
                'virtual_member_created'
            ),
        ).order_by(
            '-created_at',
        ).first()

        self.assertIsNotNone(
            activity
        )
        self.assertEqual(
            activity.activity_type,
            (
                Activity.ActivityType
                .VIRTUAL_MEMBER_CREATED
            ),
        )

    def test_kick_member_activity_type_is_correct(self):
        membership = (
            HouseholdMember.objects.get(
                household=self.household,
                user=self.member,
            )
        )

        request = self.factory.delete(
            '/members/kick/',
        )
        self.authenticate(request)

        response = KickHouseholdMemberView.as_view()(
            request,
            household_id=self.household.id,
            member_id=membership.id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        activity = Activity.objects.filter(
            household=self.household,
            metadata__action='member_kicked',
        ).order_by(
            '-created_at',
        ).first()

        self.assertIsNotNone(
            activity
        )
        self.assertEqual(
            activity.activity_type,
            Activity.ActivityType.MEMBER_KICKED,
        )

    def test_leave_activity_type_is_correct(self):
        request = self.factory.post(
            '/leave/',
            {},
            format='json',
        )
        self.authenticate(
            request,
            user=self.member,
        )

        response = LeaveHouseholdView.as_view()(
            request,
            household_id=self.household.id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        activity = Activity.objects.filter(
            household=self.household,
            metadata__action='member_left',
        ).order_by(
            '-created_at',
        ).first()

        self.assertIsNotNone(
            activity
        )
        self.assertEqual(
            activity.activity_type,
            Activity.ActivityType.MEMBER_LEFT,
        )

    def test_delete_household_activity_type_is_correct(
        self,
    ):
        HouseholdMember.objects.filter(
            household=self.household,
            user=self.member,
        ).delete()

        request = self.factory.delete(
            '/households/detail/',
        )
        self.authenticate(request)

        response = HouseholdDetailView.as_view()(
            request,
            pk=self.household.id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        activity = Activity.objects.filter(
            household=self.household,
            metadata__action='household_deleted',
        ).order_by(
            '-created_at',
        ).first()

        self.assertIsNotNone(
            activity
        )
        self.assertEqual(
            activity.activity_type,
            (
                Activity.ActivityType
                .HOUSEHOLD_DELETED
            ),
        )

    def test_activity_route_is_registered_once(self):
        activity_route_count = sum(
            1
            for pattern in urlpatterns
            if str(pattern.pattern) == (
                '<uuid:household_id>/activities/'
            )
        )

        self.assertEqual(
            activity_route_count,
            1,
        )

    def test_my_debt_summary_without_debts(self):
        request = self.factory.get(
            '/my-debts/',
        )
        self.authenticate(request)

        response = MyDebtSummaryView.as_view()(
            request,
            household_id=self.household.id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data['total_i_owe'],
            0,
        )
        self.assertEqual(
            response.data['total_owed_to_me'],
            0,
        )
        self.assertEqual(
            response.data['i_owe'],
            [],
        )
        self.assertEqual(
            response.data['owed_to_me'],
            [],
        )