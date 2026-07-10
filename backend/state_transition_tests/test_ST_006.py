import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestST006DebtIsPaid:
    
    def test_st_006_01_settle_virtual_member_debt(self, auth_client, test_household, active_user):
        """
        S1 (False - Unpaid) -> E1 (Owner settle debt virtual) -> S2 (True - Paid)
        """
        # Create virtual member
        from households.models import HouseholdMember
        v_user = User.objects.create_user(
            email="virtual@virtual.chungvi.local",
            username="virtual_12345",
            full_name="Virtual User",
            is_active=False,
            auth_provider='virtual'
        )
        HouseholdMember.objects.create(
            household=test_household,
            user=v_user,
            role=HouseholdMember.Role.MEMBER
        )
        
        from expenses.models import Debt, Expense
        from decimal import Decimal
        
        expense = Expense.objects.create(
            household=test_household,
            payer=active_user,
            title="Test Expense",
            amount=Decimal('50000.00')
        )
        
        debt = Debt.objects.create(
            household=test_household,
            expense=expense,
            from_user=active_user,
            to_user=v_user,
            amount=50000,
            is_paid=False
        )
        
        assert debt.is_paid is False
        
        url = f'/api/households/{test_household.id}/virtual-members/{v_user.id}/debts/{active_user.id}/settle/'
        data = {}
        
        response = auth_client.post(url, data, format='json')
        assert response.status_code == 200
        
        debt.refresh_from_db()
        assert debt.is_paid is True
        assert debt.remaining_amount == 0
