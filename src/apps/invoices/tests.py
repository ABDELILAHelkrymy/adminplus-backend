from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import datetime, date
from decimal import Decimal

from apps.accounts.models import BusinessAccount
from apps.invoices.models import Invoice, Supplier, Customer, Category, PaymentMethod, Project

User = get_user_model()


class InvoiceNumberGenerationTestCase(TestCase):
    """Test cases for automatic invoice number generation"""

    def setUp(self):
        """Set up test data"""
        # Create a user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Create a business account
        self.business_account = BusinessAccount.objects.create(
            primary_user=self.user,
            business_name='Test Business',
            email='business@example.com'
        )
        
        # Create a second business account for multi-tenant testing
        self.user2 = User.objects.create_user(
            email='test2@example.com',
            password='testpass123',
            first_name='Test2',
            last_name='User2'
        )
        self.business_account2 = BusinessAccount.objects.create(
            primary_user=self.user2,
            business_name='Test Business 2',
            email='business2@example.com'
        )
        
        # Create a customer
        self.customer = Customer.objects.create(
            business_account=self.business_account,
            corporate_name='Test Customer',
            email='customer@example.com'
        )
        
        # Create a supplier
        self.supplier = Supplier.objects.create(
            business_account=self.business_account,
            corporate_name='Test Supplier',
            email='supplier@example.com'
        )

    def test_income_invoice_auto_generation(self):
        """Test that income invoices generate FAC-YYYYMM-NNNN format"""
        invoice = Invoice.objects.create(
            business_account=self.business_account,
            invoice_type='invoice',
            customer=self.customer,
            date=date.today(),
            currency='MAD'
        )
        
        # Check format FAC-YYYYMM-0001
        current_year = datetime.now().year
        current_month = datetime.now().month
        expected_prefix = f"FAC-{current_year}{current_month:02d}"
        
        self.assertTrue(invoice.invoice_number.startswith(expected_prefix))
        self.assertEqual(invoice.invoice_number, f"{expected_prefix}-0001")

    def test_purchase_invoice_auto_generation(self):
        """Test that purchase invoices generate ACH-YYYYMM-NNNN format"""
        # Purchase invoice without invoice_number should auto-generate
        invoice = Invoice.objects.create(
            business_account=self.business_account,
            invoice_type='purchase',
            supplier=self.supplier,
            date=date.today(),
            currency='MAD'
        )
        
        current_year = datetime.now().year
        current_month = datetime.now().month
        expected_prefix = f"ACH-{current_year}{current_month:02d}"
        
        self.assertTrue(invoice.invoice_number.startswith(expected_prefix))
        self.assertEqual(invoice.invoice_number, f"{expected_prefix}-0001")

    def test_sequential_numbering(self):
        """Test that invoice numbers increment sequentially"""
        # Create first invoice
        invoice1 = Invoice.objects.create(
            business_account=self.business_account,
            invoice_type='invoice',
            customer=self.customer,
            date=date.today(),
            currency='MAD'
        )
        
        # Create second invoice
        invoice2 = Invoice.objects.create(
            business_account=self.business_account,
            invoice_type='invoice',
            customer=self.customer,
            date=date.today(),
            currency='MAD'
        )
        
        # Create third invoice
        invoice3 = Invoice.objects.create(
            business_account=self.business_account,
            invoice_type='invoice',
            customer=self.customer,
            date=date.today(),
            currency='MAD'
        )
        
        current_year = datetime.now().year
        current_month = datetime.now().month
        expected_prefix = f"FAC-{current_year}{current_month:02d}"
        
        self.assertEqual(invoice1.invoice_number, f"{expected_prefix}-0001")
        self.assertEqual(invoice2.invoice_number, f"{expected_prefix}-0002")
        self.assertEqual(invoice3.invoice_number, f"{expected_prefix}-0003")

    def test_different_invoice_types_separate_sequences(self):
        """Test that different invoice types have separate numbering sequences"""
        # Create invoice
        invoice = Invoice.objects.create(
            business_account=self.business_account,
            invoice_type='invoice',
            customer=self.customer,
            date=date.today(),
            currency='MAD'
        )
        
        # Create sale invoice
        sale = Invoice.objects.create(
            business_account=self.business_account,
            invoice_type='sale',
            customer=self.customer,
            date=date.today(),
            currency='MAD'
        )
        
        # Create credit note
        credit_note = Invoice.objects.create(
            business_account=self.business_account,
            invoice_type='credit_note',
            customer=self.customer,
            date=date.today(),
            currency='MAD'
        )
        
        # Create purchase invoice
        purchase = Invoice.objects.create(
            business_account=self.business_account,
            invoice_type='purchase',
            supplier=self.supplier,
            date=date.today(),
            currency='MAD'
        )
        
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # Each type should start at 0001
        self.assertEqual(invoice.invoice_number, f"FAC-{current_year}{current_month:02d}-0001")
        self.assertEqual(sale.invoice_number, f"VENTE-{current_year}{current_month:02d}-0001")
        self.assertEqual(credit_note.invoice_number, f"AV-{current_year}{current_month:02d}-0001")
        self.assertEqual(purchase.invoice_number, f"ACH-{current_year}{current_month:02d}-0001")

    def test_multi_tenant_isolation(self):
        """Test that different business accounts have separate numbering sequences"""
        # Create invoice for business 1
        invoice1 = Invoice.objects.create(
            business_account=self.business_account,
            invoice_type='invoice',
            customer=self.customer,
            date=date.today(),
            currency='MAD'
        )
        
        # Create customer for business 2 with explicit number to avoid unique constraint
        customer2 = Customer.objects.create(
            business_account=self.business_account2,
            number=100,  # Set explicit number to avoid conflict with customer 1
            corporate_name='Test Customer 2',
            email='customer2@example.com'
        )
        
        # Create invoice for business 2
        invoice2 = Invoice.objects.create(
            business_account=self.business_account2,
            invoice_type='invoice',
            customer=customer2,
            date=date.today(),
            currency='MAD'
        )
        
        current_year = datetime.now().year
        current_month = datetime.now().month
        expected_number = f"FAC-{current_year}{current_month:02d}-0001"
        
        # Both should have the same number since they're in different business accounts
        self.assertEqual(invoice1.invoice_number, expected_number)
        self.assertEqual(invoice2.invoice_number, expected_number)

    def test_manual_invoice_number_not_overwritten(self):
        """Test that manually provided invoice numbers are not overwritten"""
        # Purchase invoices can have manual numbers (supplier's invoice number)
        manual_number = "SUPPLIER-INV-2024-123"
        
        invoice = Invoice.objects.create(
            business_account=self.business_account,
            invoice_type='purchase',
            invoice_number=manual_number,
            supplier=self.supplier,
            date=date.today(),
            currency='MAD'
        )
        
        # Should keep the manual number
        self.assertEqual(invoice.invoice_number, manual_number)

    def test_invoice_number_not_changed_on_update(self):
        """Test that invoice number doesn't change when updating other fields"""
        invoice = Invoice.objects.create(
            business_account=self.business_account,
            invoice_type='invoice',
            customer=self.customer,
            date=date.today(),
            currency='MAD'
        )
        
        original_number = invoice.invoice_number
        
        # Update some fields
        invoice.comments = "Updated comments"
        invoice.total = Decimal('1000.00')
        invoice.save()
        
        # Refresh from database
        invoice.refresh_from_db()
        
        # Number should remain the same
        self.assertEqual(invoice.invoice_number, original_number)

    def test_zero_padding(self):
        """Test that invoice numbers have proper zero padding (4 digits)"""
        # Create 10 invoices to test padding
        invoices = []
        for i in range(10):
            invoice = Invoice.objects.create(
                business_account=self.business_account,
                invoice_type='invoice',
                customer=self.customer,
                date=date.today(),
                currency='MAD'
            )
            invoices.append(invoice)
        
        current_year = datetime.now().year
        current_month = datetime.now().month
        expected_prefix = f"FAC-{current_year}{current_month:02d}"
        
        # Check first invoice has 4-digit padding
        self.assertEqual(invoices[0].invoice_number, f"{expected_prefix}-0001")
        
        # Check 10th invoice
        self.assertEqual(invoices[9].invoice_number, f"{expected_prefix}-0010")

    def test_calculation_totals(self):
        """Test the calculate_totals method"""
        from apps.invoices.models import InvoiceLineItem
        
        invoice = Invoice.objects.create(
            business_account=self.business_account,
            invoice_type='invoice',
            customer=self.customer,
            date=date.today(),
            currency='MAD',
            vat_rate=Decimal('20.00')
        )
        
        # Create line items
        InvoiceLineItem.objects.create(
            invoice=invoice,
            description='Item 1',
            quantity=2,
            price=Decimal('100.00')
        )
        
        InvoiceLineItem.objects.create(
            invoice=invoice,
            description='Item 2',
            quantity=1,
            price=Decimal('50.00')
        )
        
        # Calculate totals
        invoice.calculate_totals()
        invoice.refresh_from_db()
        
        # subtotal = 2*100 + 1*50 = 250
        self.assertEqual(invoice.subtotal, Decimal('250.00'))
        
        # vat_amount = 250 * 0.20 = 50
        self.assertEqual(invoice.vat_amount, Decimal('50.00'))
        
        # total = 250 + 50 = 300
        self.assertEqual(invoice.total, Decimal('300.00'))

    def test_mark_as_paid(self):
        """Test the mark_as_paid method"""
        invoice = Invoice.objects.create(
            business_account=self.business_account,
            invoice_type='invoice',
            customer=self.customer,
            date=date.today(),
            currency='MAD',
            is_paid=False
        )
        
        # Mark as paid
        test_date = date(2025, 11, 20)
        invoice.mark_as_paid(paid_date=test_date)
        invoice.refresh_from_db()
        
        self.assertTrue(invoice.is_paid)
        self.assertEqual(invoice.paid_date, test_date)

    def test_invoice_str_representation(self):
        """Test the string representation of an invoice"""
        invoice = Invoice.objects.create(
            business_account=self.business_account,
            invoice_type='invoice',
            customer=self.customer,
            date=date.today(),
            currency='MAD'
        )
        
        expected_str = f"{invoice.invoice_number} - Invoice"
        self.assertEqual(str(invoice), expected_str)


class InvoiceAPITestCase(TestCase):
    """Test cases for invoice API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        from rest_framework.test import APIClient
        from rest_framework.authtoken.models import Token
        
        # Create a user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Create a business account
        self.business_account = BusinessAccount.objects.create(
            primary_user=self.user,
            business_name='Test Business',
            email='business@example.com'
        )
        
        # Create authentication token
        self.token = Token.objects.create(user=self.user)
        
        # Set up API client
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        # Create a customer
        self.customer = Customer.objects.create(
            business_account=self.business_account,
            corporate_name='Test Customer',
            email='customer@example.com'
        )
    
    def test_create_income_invoice_without_number(self):
        """Test creating income invoice via API without providing invoice_number"""
        data = {
            'invoice_type': 'invoice',
            'customer': self.customer.id,
            'date': date.today().isoformat(),
            'currency': 'MAD',
            'vat_rate': '20.00'
        }
        
        response = self.client.post('/api/v1/invoices/', data, format='json')
        
        self.assertEqual(response.status_code, 201)
        self.assertIn('invoice_number', response.data)
        
        # Check that invoice number was auto-generated
        current_year = datetime.now().year
        current_month = datetime.now().month
        expected_prefix = f"FAC-{current_year}{current_month:02d}"
        
        self.assertTrue(response.data['invoice_number'].startswith(expected_prefix))
    
    def test_create_income_invoice_with_number_ignored(self):
        """Test that providing invoice_number for income invoice is ignored (read-only)"""
        data = {
            'invoice_type': 'invoice',
            'invoice_number': 'CUSTOM-NUMBER-123',  # Should be ignored
            'customer': self.customer.id,
            'date': date.today().isoformat(),
            'currency': 'MAD',
            'vat_rate': '20.00'
        }
        
        response = self.client.post('/api/v1/invoices/', data, format='json')
        
        self.assertEqual(response.status_code, 201)
        
        # Invoice number should be auto-generated, not the custom one
        self.assertNotEqual(response.data['invoice_number'], 'CUSTOM-NUMBER-123')
        
        current_year = datetime.now().year
        current_month = datetime.now().month
        expected_prefix = f"FAC-{current_year}{current_month:02d}"
        
        self.assertTrue(response.data['invoice_number'].startswith(expected_prefix))
