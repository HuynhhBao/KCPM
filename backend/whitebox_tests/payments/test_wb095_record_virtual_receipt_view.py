import pytest
from rest_framework.test import force_authenticate
from rest_framework.exceptions import NotAuthenticated, ValidationError
from payments.views import RecordVirtualReceiptView
from payments.models import Payment
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_wb095_tc01_record_virtual_receipt_household_not_found(rf, owner):
    view = RecordVirtualReceiptView()
    django_request = rf.post('/', {'virtual_user_id': owner.id, 'amount': 1000})
    request = view.initialize_request(django_request)
    force_authenticate(request, user=owner)
    request.user = owner
    view.request = request
    view.kwargs = {'household_id': "00000000-0000-0000-0000-000000000000"}
    response = view.post(request, household_id="00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert 'Không tìm thấy nhóm' in response.data['detail']

@pytest.mark.django_db
def test_wb095_tc02_record_virtual_receipt_not_virtual_user(rf, owner, member, household):
    view = RecordVirtualReceiptView()
    django_request = rf.post('/', {'virtual_user_id': member.id, 'amount': 1000})
    request = view.initialize_request(django_request)
    force_authenticate(request, user=owner)
    request.user = owner
    view.request = request
    view.kwargs = {'household_id': household.id}
    response = view.post(request, household_id=household.id)
    assert response.status_code == 400
    assert 'không phải thành viên ảo' in response.data['detail']

@pytest.mark.django_db
def test_wb095_tc03_record_virtual_receipt_virtual_member_not_found(rf, owner, household):
    view = RecordVirtualReceiptView()
    django_request = rf.post('/', {'virtual_user_id': 9999, 'amount': 1000})
    request = view.initialize_request(django_request)
    force_authenticate(request, user=owner)
    request.user = owner
    view.request = request
    view.kwargs = {'household_id': household.id}
    response = view.post(request, household_id=household.id)
    assert response.status_code == 404
    assert 'Thành viên ảo không thuộc nhóm' in response.data['detail']

@pytest.mark.django_db
def test_wb095_tc04_record_virtual_receipt_no_debt_or_too_large(rf, owner, virtual_user, virtual_debt_instance, household):
    # virtual owes owner 100000 (virtual_debt_instance)
    view = RecordVirtualReceiptView()
    django_request = rf.post('/', {'virtual_user_id': virtual_user.id, 'amount': 150000})
    request = view.initialize_request(django_request)
    force_authenticate(request, user=owner)
    request.user = owner
    view.request = request
    view.kwargs = {'household_id': household.id}
    response = view.post(request, household_id=household.id)
    assert response.status_code == 400
    assert 'không được lớn hơn số nợ' in response.data['detail']

@pytest.mark.django_db
def test_wb095_tc05_record_virtual_receipt_custom_amount_null(rf, owner, virtual_user, household):
    view = RecordVirtualReceiptView()
    django_request = rf.post(
        '/',
        {'virtual_user_id': virtual_user.id, 'payment_mode': Payment.Mode.CUSTOM_AMOUNT, 'amount': None},
        content_type='application/json'
    )
    request = view.initialize_request(django_request)
    force_authenticate(request, user=owner)
    request.user = owner
    view.request = request
    view.kwargs = {'household_id': household.id}
    with pytest.raises(ValidationError):
        view.post(request, household_id=household.id)

@pytest.mark.django_db
def test_wb095_tc06_record_virtual_receipt_selected_items_empty(rf, owner, virtual_user, household):
    view = RecordVirtualReceiptView()
    django_request = rf.post('/', {'virtual_user_id': virtual_user.id, 'payment_mode': Payment.Mode.SELECTED_ITEMS, 'debt_ids': []})
    request = view.initialize_request(django_request)
    force_authenticate(request, user=owner)
    request.user = owner
    view.request = request
    view.kwargs = {'household_id': household.id}
    with pytest.raises(ValidationError):
        view.post(request, household_id=household.id)

@pytest.mark.django_db
def test_wb095_tc07_record_virtual_receipt_unauthenticated(rf, household):
    view = RecordVirtualReceiptView()
    django_request = rf.post('/', {'virtual_user_id': 1, 'amount': 1000})
    request = view.initialize_request(django_request)
    view.request = request
    view.kwargs = {'household_id': household.id}
    with pytest.raises(NotAuthenticated):
        view.check_permissions(request)
