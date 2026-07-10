import pytest
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import force_authenticate
from payments.views import MarkDebtPaidView
from payments.models import Payment
from expenses.models import Debt
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_wb093_tc01_mark_debt_paid_not_found(rf, owner):
    view = MarkDebtPaidView()
    django_request = rf.post('/', {})
    request = view.initialize_request(django_request)
    force_authenticate(request, user=owner)
    request.user = owner
    view.request = request
    view.kwargs = {'debt_id': "00000000-0000-0000-0000-000000000000"}
    response = view.post(request, debt_id="00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.data['detail'] == 'Không tìm thấy công nợ.'

@pytest.mark.django_db
def test_wb093_tc02_mark_debt_paid_not_from_user(rf, owner, debt_instance):
    view = MarkDebtPaidView()
    django_request = rf.post('/', {})
    request = view.initialize_request(django_request)
    force_authenticate(request, user=owner)
    request.user = owner
    view.request = request
    view.kwargs = {'debt_id': debt_instance.id}
    with pytest.raises(PermissionDenied):
        view.post(request, debt_id=debt_instance.id)

@pytest.mark.django_db
def test_wb093_tc03_mark_debt_paid_virtual_member(rf, owner, virtual_debt_instance):
    view = MarkDebtPaidView()
    django_request = rf.post('/', {})
    request = view.initialize_request(django_request)
    force_authenticate(request, user=owner)
    request.user = owner
    view.request = request
    view.kwargs = {'debt_id': virtual_debt_instance.id}
    response = view.post(request, debt_id=virtual_debt_instance.id)
    assert response.status_code == 200
    assert response.data['virtual_settlement'] is True
    virtual_debt_instance.refresh_from_db()
    assert virtual_debt_instance.is_paid is True

@pytest.mark.django_db
def test_wb093_tc04_mark_debt_paid_happy_path(rf, owner, debtor, debt_instance):
    view = MarkDebtPaidView()
    django_request = rf.post('/', {'note': 'paid my debt'})
    request = view.initialize_request(django_request)
    force_authenticate(request, user=debtor)
    request.user = debtor
    view.request = request
    view.kwargs = {'debt_id': debt_instance.id}
    response = view.post(request, debt_id=debt_instance.id)
    assert response.status_code == 201
    assert response.data['message'] == 'Đã gửi yêu cầu xác nhận thanh toán.'
    assert Payment.objects.filter(debt=debt_instance, status=Payment.Status.PENDING).exists()
