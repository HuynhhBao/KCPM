from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory
from households.models import Household, HouseholdMember
from expenses.serializers import ExpenseCreateUpdateSerializer

User = get_user_model()

class ExpenseCreateUpdateSerializerTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='password123',
            email_verified=True
        )
        self.other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='password123',
            email_verified=True
        )
        self.household = Household.objects.create(
            name='Test Household',
            owner=self.user
        )
        HouseholdMember.objects.create(
            household=self.household,
            user=self.user,
            role=HouseholdMember.Role.OWNER
        )
        HouseholdMember.objects.create(
            household=self.household,
            user=self.other_user,
            role=HouseholdMember.Role.MEMBER
        )
        self.factory = APIRequestFactory()

    def test_create_expense_returns_participants_in_representation(self):
        request = self.factory.post('/api/expenses/')
        request.user = self.user

        data = {
            'household': self.household.id,
            'title': 'Test Expense',
            'amount': 300000,
            'split_type': 'equal',
            'participants': [
                {'user_id': self.user.id},
                {'user_id': self.other_user.id}
            ]
        }

        serializer = ExpenseCreateUpdateSerializer(
            data=data,
            context={'request': request}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        expense = serializer.save()

        # The representation should include the fields defined in ExpenseDetailSerializer,
        # especially 'participants' with their share_amounts.
        rep = serializer.data
        self.assertIn('participants', rep)
        self.assertEqual(len(rep['participants']), 2)
        
        participant_emails = [p['user_email'] for p in rep['participants']]
        self.assertIn('user@example.com', participant_emails)
        self.assertIn('other@example.com', participant_emails)
        
        for p in rep['participants']:
            self.assertEqual(Decimal(p['share_amount']), Decimal('150000'))

    def test_title_too_long_returns_vietnamese_validation_error(self):
        request = self.factory.post('/api/expenses/')
        request.user = self.user

        data = {
            'household': self.household.id,
            'title': 'a' * 256,  # 256 characters is longer than max_length=255
            'amount': 300000,
            'split_type': 'equal',
            'participants': [
                {'user_id': self.user.id}
            ]
        }

        serializer = ExpenseCreateUpdateSerializer(
            data=data,
            context={'request': request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('title', serializer.errors)
        self.assertEqual(
            str(serializer.errors['title'][0]),
            'Tiêu đề quá dài, không được vượt quá 255 ký tự.'
        )

    def test_create_expense_escapes_xss_in_title(self):
        request = self.factory.post('/api/expenses/')
        request.user = self.user

        data = {
            'household': self.household.id,
            'title': "<script>alert('xss')</script>",
            'amount': 300000,
            'split_type': 'equal',
            'participants': [
                {'user_id': self.user.id}
            ]
        }

        serializer = ExpenseCreateUpdateSerializer(
            data=data,
            context={'request': request}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        expense = serializer.save()

        # The saved title should be escaped to safe HTML entities
        self.assertEqual(expense.title, "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;")
        
        # Verify the representation also contains the escaped title
        rep = serializer.data
        self.assertEqual(rep['title'], "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;")

    def test_amount_too_large_returns_vietnamese_validation_error(self):
        request = self.factory.post('/api/expenses/')
        request.user = self.user

        data = {
            'household': self.household.id,
            'title': 'Test Amount',
            'amount': 9999999999999,  # 13 digits, exceeds max_digits=12
            'split_type': 'equal',
            'participants': [
                {'user_id': self.user.id}
            ]
        }

        serializer = ExpenseCreateUpdateSerializer(
            data=data,
            context={'request': request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)
        self.assertIn(
            'Số tiền quá lớn, tối đa chỉ được 12 chữ số.',
            [str(e) for e in serializer.errors['amount']]
        )

    def test_amount_invalid_type_returns_vietnamese_validation_error(self):
        request = self.factory.post('/api/expenses/')
        request.user = self.user

        data = {
            'household': self.household.id,
            'title': 'Test Amount',
            'amount': [100000],  # Array instead of number
            'split_type': 'equal',
            'participants': [
                {'user_id': self.user.id}
            ]
        }

        serializer = ExpenseCreateUpdateSerializer(
            data=data,
            context={'request': request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)
        self.assertIn(
            'Số tiền không hợp lệ, vui lòng nhập một số.',
            [str(e) for e in serializer.errors['amount']]
        )
