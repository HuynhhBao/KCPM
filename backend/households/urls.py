from django.urls import path

from households.views import (
    ActivityListView,
    AddHouseholdMemberView,
    CreateVirtualHouseholdMemberView,
    AllActivityListView,
    HouseholdDetailView,
    HouseholdListCreateView,
    HouseholdSummaryListView,
    JoinHouseholdView,
    KickHouseholdMemberView,
    LeaveHouseholdView,
    MyDebtDetailView,
    MyDebtSummaryView,
    SettleVirtualMemberDebtPairView,
    VirtualMemberDebtDetailView,
    VirtualMemberDebtSummaryView,
)

urlpatterns = [
    path(
        '',
        HouseholdListCreateView.as_view(),
    ),

    path(
        'join/',
        JoinHouseholdView.as_view(),
    ),

    path(
        'activities/',
        AllActivityListView.as_view(),
    ),

    path(
        'summary/',
        HouseholdSummaryListView.as_view(),
    ),

    path(
        '<uuid:pk>/',
        HouseholdDetailView.as_view(),
    ),

    path(
        '<uuid:household_id>/members/add/',
        AddHouseholdMemberView.as_view(),
    ),

    path(
        '<uuid:household_id>/members/virtual/',
        CreateVirtualHouseholdMemberView.as_view(),
    ),

    path(
        '<uuid:household_id>/members/<uuid:member_id>/kick/',
        KickHouseholdMemberView.as_view(),
    ),

    path(
        '<uuid:household_id>/leave/',
        LeaveHouseholdView.as_view(),
    ),

    path(
        '<uuid:household_id>/my-debts/',
        MyDebtSummaryView.as_view(),
    ),

    path(
        '<uuid:household_id>/my-debts/<int:other_user_id>/',
        MyDebtDetailView.as_view(),
    ),

    path(
        '<uuid:household_id>/virtual-members/<int:virtual_user_id>/debts/',
        VirtualMemberDebtSummaryView.as_view(),
    ),

    path(
        '<uuid:household_id>/virtual-members/<int:virtual_user_id>/debts/<int:other_user_id>/',
        VirtualMemberDebtDetailView.as_view(),
    ),

    path(
        '<uuid:household_id>/virtual-members/<int:virtual_user_id>/debts/<int:other_user_id>/settle/',
        SettleVirtualMemberDebtPairView.as_view(),
    ),

    path(
        '<uuid:household_id>/activities/',
        ActivityListView.as_view(),
    ),

    path(
        '<uuid:household_id>/activities/',
        ActivityListView.as_view(),
    ),
]