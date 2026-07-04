from django.test import TestCase
from expenses.serializers import ExpenseCreateUpdateSerializer

class ExpenseSerializerXSSTestCase(TestCase):
    def test_title_xss_escaping(self):
        serializer = ExpenseCreateUpdateSerializer()
        cleaned_title = serializer.validate_title("<script>alert('xss')</script>")
        self.assertEqual(cleaned_title, "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;")
