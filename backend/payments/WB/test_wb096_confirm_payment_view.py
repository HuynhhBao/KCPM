import pytest
from rest_framework.exceptions import PermissionDenied, NotAuthenticated
from rest_framework.test import force_authenticate
from payments.views import ConfirmPaymentView
from payments.models import Payment, PaymentAllocation
from expenses.models import Debt
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_wb096_tc01_confirm_payment_not_found(rf, owner):
    view = ConfirmPaymentView()
    django_request = rf.post('/', {})
    request = view.initialize_request(django_request)
    force_authenticate(request, user=owner)
    request.user = owner
    view.request = request
    view.kwargs = {'pk': "00000000-0000-0000-0000-000000000000"}
    response = view.post(request, pk="00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert 'Không tìm thấy yêu cầu thanh toán' in response.data['detail']

@pytest.mark.django_db
def test_wb096_tc02_confirm_payment_not_receiver(rf, other_user, debtor, owner, household):
    payment = Payment.objects.create(
        household=household, payer=debtor, receiver=owner, amount=10000, status=Payment.Status.PENDING
    )
    view = ConfirmPaymentView()
    django_request = rf.post('/', {})
    request = view.initialize_request(django_request)
    force_authenticate(request, user=other_user)
    request.user = other_user
    view.request = request
    view.kwargs = {'pk': payment.id}
    with pytest.raises(PermissionDenied):
        view.post(request, pk=payment.id)

@pytest.mark.django_db
def test_wb096_tc03_confirm_payment_not_pending(rf, debtor, owner, household):
    payment = Payment.objects.create(
        household=household, payer=debtor, receiver=owner, amount=10000, status=Payment.Status.CONFIRMED
    )
    view = ConfirmPaymentView()
    django_request = rf.post('/', {})
    request = view.initialize_request(django_request)
    force_authenticate(request, user=owner)
    request.user = owner
    view.request = request
    view.kwargs = {'pk': payment.id}
    response = view.post(request, pk=payment.id)
    assert response.status_code == 400
    assert 'không còn chờ xác nhận' in response.data['detail']

@pytest.mark.django_db
def test_wb096_tc04_confirm_payment_happy_path(rf, debtor, owner, debt_instance, household):
    payment = Payment.objects.create(
        household=household, payer=debtor, receiver=owner, amount=20000, status=Payment.Status.PENDING, is_pair_payment=True
    )
    PaymentAllocation.objects.create(payment=payment, debt=debt_instance, allocated_amount=20000)
    view = ConfirmPaymentView()
    django_request = rf.post('/', {})
    request = view.initialize_request(django_request)
    force_authenticate(request, user=owner)
    request.user = owner
    view.request = request
    view.kwargs = {'pk': payment.id}
    response = view.post(request, pk=payment.id)
    assert response.status_code == 200
    payment.refresh_from_db()
    assert payment.status == Payment.Status.CONFIRMED
    debt_instance.refresh_from_db()
    assert debt_instance.paid_amount == 20000

@pytest.mark.django_db
def test_wb096_tc05_confirm_payment_unauthenticated(rf):
    view = ConfirmPaymentView()
    django_request = rf.post('/', {})
    request = view.initialize_request(django_request)
    view.request = request
    view.kwargs = {'pk': "00000000-0000-0000-0000-000000000000"}
    with pytest.raises(NotAuthenticated):
        view.check_permissions(request)
