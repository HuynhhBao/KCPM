from django.urls import path

from payments.views import (
    ConfirmPaymentView,
    CreatePairPaymentView,
    MarkDebtPaidView,
    MyPaymentListView,
    PendingPaymentListView,
    RejectPaymentView,
    RecordVirtualReceiptView,
)

urlpatterns = [
    path(
        'debts/<uuid:debt_id>/mark-paid/',
        MarkDebtPaidView.as_view(),
    ),

    path(
        'households/<uuid:household_id>/pair-payments/',
        CreatePairPaymentView.as_view(),
    ),

    path(
        'households/<uuid:household_id>/virtual-receipts/',
        RecordVirtualReceiptView.as_view(),
    ),

    path(
        'pending/',
        PendingPaymentListView.as_view(),
    ),

    path(
        'mine/',
        MyPaymentListView.as_view(),
    ),

    path(
        '<uuid:pk>/confirm/',
        ConfirmPaymentView.as_view(),
    ),

    path(
        '<uuid:pk>/reject/',
        RejectPaymentView.as_view(),
    ),
]