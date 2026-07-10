import pytest
from rest_framework.test import force_authenticate
from rest_framework.exceptions import NotAuthenticated, ValidationError
from payments.views import CreatePairPaymentView
from payments.models import Payment
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_wb094_tc01_create_pair_payment_household_not_found(rf, owner):
    view = CreatePairPaymentView()
    django_request = rf.post('/', {'receiver_id': owner.id, 'payment_mode': Payment.Mode.FULL})
    request = view.initialize_request(django_request)
    force_authenticate(request, user=owner)
    request.user = owner
    view.request = request
    view.kwargs = {'household_id': "00000000-0000-0000-0000-000000000000"}
    response = view.post(request, household_id="00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert 'Không tìm thấy nhóm' in response.data['detail']

@pytest.mark.django_db
def test_wb094_tc02_create_pair_payment_payer_is_receiver(rf, owner, household):
    view = CreatePairPaymentView()
    django_request = rf.post('/', {'receiver_id': owner.id, 'payment_mode': Payment.Mode.FULL})
    request = view.initialize_request(django_request)
    force_authenticate(request, user=owner)
    request.user = owner
    view.request = request
    view.kwargs = {'household_id': household.id}
    response = view.post(request, household_id=household.id)
    assert response.status_code == 400
    assert 'Không thể tự thanh toán' in response.data['detail']

@pytest.mark.django_db
def test_wb094_tc03_create_pair_payment_virtual_user(rf, owner, virtual_user, household):
    view = CreatePairPaymentView()
    django_request = rf.post('/', {'receiver_id': virtual_user.id, 'payment_mode': Payment.Mode.FULL})
    request = view.initialize_request(django_request)
    force_authenticate(request, user=owner)
    request.user = owner
    view.request = request
    view.kwargs = {'household_id': household.id}
    response = view.post(request, household_id=household.id)
    assert response.status_code == 400
    assert 'thành viên ảo' in response.data['detail']

@pytest.mark.django_db
def test_wb094_tc04_create_pair_payment_no_debt(rf, owner, member, household):
    view = CreatePairPaymentView()
    django_request = rf.post('/', {'receiver_id': owner.id, 'payment_mode': Payment.Mode.FULL})
    request = view.initialize_request(django_request)
    force_authenticate(request, user=member)
    request.user = member
    view.request = request
    view.kwargs = {'household_id': household.id}
    response = view.post(request, household_id=household.id)
    assert response.status_code == 400
    assert 'Bạn hiện không còn nợ' in response.data['detail']

@pytest.mark.django_db
def test_wb094_tc05_create_pair_payment_custom_amount_null(rf, owner, debtor, household):
    view = CreatePairPaymentView()
    django_request = rf.post(
        '/',
        {'receiver_id': owner.id, 'payment_mode': Payment.Mode.CUSTOM_AMOUNT, 'amount': None},
        content_type='application/json'
    )
    request = view.initialize_request(django_request)
    force_authenticate(request, user=debtor)
    request.user = debtor
    view.request = request
    view.kwargs = {'household_id': household.id}
    with pytest.raises(ValidationError):
        view.post(request, household_id=household.id)

@pytest.mark.django_db
def test_wb094_tc06_create_pair_payment_happy_path(rf, owner, debtor, debt_instance, household):
    view = CreatePairPaymentView()
    django_request = rf.post('/', {'receiver_id': owner.id, 'payment_mode': Payment.Mode.FULL})
    request = view.initialize_request(django_request)
    force_authenticate(request, user=debtor)
    request.user = debtor
    view.request = request
    view.kwargs = {'household_id': household.id}
    response = view.post(request, household_id=household.id)
    assert response.status_code == 201
    assert 'Đã gửi yêu cầu xác nhận thanh toán' in response.data['message']
    assert Payment.objects.filter(household=household, payer=debtor, receiver=owner, status=Payment.Status.PENDING).exists()

@pytest.mark.django_db
def test_wb094_tc07_create_pair_payment_unauthenticated(rf, household):
    view = CreatePairPaymentView()
    django_request = rf.post('/', {'receiver_id': 1, 'payment_mode': Payment.Mode.FULL})
    request = view.initialize_request(django_request)
    view.request = request
    view.kwargs = {'household_id': household.id}
    with pytest.raises(NotAuthenticated):
        view.check_permissions(request)

@pytest.mark.django_db
def test_wb094_tc08_create_pair_payment_receiver_not_found(rf, owner, household):
    view = CreatePairPaymentView()
    django_request = rf.post('/', {'receiver_id': 9999, 'payment_mode': Payment.Mode.FULL})
    request = view.initialize_request(django_request)
    force_authenticate(request, user=owner)
    request.user = owner
    view.request = request
    view.kwargs = {'household_id': household.id}
    response = view.post(request, household_id=household.id)
    assert response.status_code == 404
    assert 'Người nhận không thuộc nhóm' in response.data['detail']
