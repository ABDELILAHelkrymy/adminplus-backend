# ComptaGo Backend Testing Plan

This document outlines the testing strategy for the ComptaGo backend to ensure code quality and system stability.

## 🎯 Testing Goals

1. **Code Coverage**: Achieve minimum 80% coverage for critical modules
2. **Regression Prevention**: Catch bugs before they reach production
3. **API Contract**: Ensure API responses match expected schemas
4. **Business Logic**: Verify complex calculations and workflows

---

## 🧪 Test Categories

### 1. Unit Tests

Test individual components in isolation.

**Target Areas:**
- Model methods (`calculate_totals`, `is_overdue`, `mark_as_paid`)
- Serializer validation
- Utility functions (`invoice_parser.py`, `statement_parser.py`)
- Permission classes

**Example - Model Test:**
```python
# apps/invoices/tests.py

from django.test import TestCase
from decimal import Decimal
from apps.invoices.models import Invoice, InvoiceLineItem
from apps.accounts.models import BusinessAccount

class InvoiceModelTest(TestCase):
    def setUp(self):
        self.business = BusinessAccount.objects.create(
            business_name="Test Company"
        )
        self.invoice = Invoice.objects.create(
            business_account=self.business,
            invoice_type='sale',
            status='draft'
        )

    def test_calculate_totals(self):
        """Test that invoice totals are calculated correctly"""
        InvoiceLineItem.objects.create(
            invoice=self.invoice,
            description="Service",
            quantity=2,
            unit_price=Decimal('100.00'),
            vat_rate=Decimal('20.00')
        )
        self.invoice.calculate_totals()
        
        self.assertEqual(self.invoice.subtotal, Decimal('200.00'))
        self.assertEqual(self.invoice.vat_amount, Decimal('40.00'))
        self.assertEqual(self.invoice.total, Decimal('240.00'))

    def test_is_overdue(self):
        """Test overdue detection"""
        from datetime import date, timedelta
        
        self.invoice.status = 'unpaid'
        self.invoice.due_date = date.today() - timedelta(days=1)
        self.invoice.save()
        
        self.assertTrue(self.invoice.is_overdue())
```

---

### 2. API/Integration Tests

Test API endpoints with full request/response cycle.

**Target Areas:**
- CRUD operations for all ViewSets
- Authentication flow (login, token refresh)
- Business account isolation (multi-tenancy)
- File upload endpoints

**Example - API Test:**
```python
# apps/invoices/tests.py

from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from apps.users.models import User
from apps.accounts.models import BusinessAccount

class InvoiceAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.business = BusinessAccount.objects.create(
            business_name="Test Company"
        )
        self.user.active_business_account = self.business
        self.user.save()
        self.client.force_authenticate(user=self.user)

    def test_create_invoice(self):
        """Test creating an invoice via API"""
        url = reverse('invoice-list')
        data = {
            'invoice_type': 'sale',
            'status': 'draft',
            'issue_date': '2024-01-15'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['invoice_type'], 'sale')

    def test_list_invoices_filtered_by_business(self):
        """Test that users only see their business's invoices"""
        # Create invoice for different business
        other_business = BusinessAccount.objects.create(
            business_name="Other Company"
        )
        Invoice.objects.create(
            business_account=other_business,
            invoice_type='sale'
        )
        
        url = reverse('invoice-list')
        response = self.client.get(url)
        
        # Should not see other business's invoices
        self.assertEqual(len(response.data), 0)

    def test_unauthorized_access(self):
        """Test that unauthenticated requests are rejected"""
        self.client.force_authenticate(user=None)
        url = reverse('invoice-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

---

### 3. Parser Tests

Test OCR and file parsing functionality.

**Target Areas:**
- Invoice PDF parsing
- Bank statement parsing
- Data extraction accuracy

**Example - Parser Test:**
```python
# apps/bank_statements/tests.py

from django.test import TestCase
from unittest.mock import patch, MagicMock
from apps.bank_statements.statement_parser import StatementParser

class StatementParserTest(TestCase):
    def test_parse_attijariwafa_format(self):
        """Test parsing Attijariwafa bank statement format"""
        # Mock PDF content
        mock_text = """
        Date: 01/01/2024
        Libellé: VIREMENT RECU
        Débit: 
        Crédit: 5000.00
        Solde: 15000.00
        """
        
        with patch.object(StatementParser, '_extract_text', return_value=mock_text):
            parser = StatementParser('ATTIJARIWAFA')
            result = parser.parse(MagicMock())
            
            self.assertEqual(len(result['transactions']), 1)
            self.assertEqual(result['transactions'][0]['credit'], 5000.00)

    def test_parse_invalid_format(self):
        """Test handling of invalid file format"""
        parser = StatementParser('ATTIJARIWAFA')
        
        with self.assertRaises(ValueError):
            parser.parse(None)
```

---

## 📋 Test Configuration

### Running Tests

```bash
# Run all tests
python src/manage.py test

# Run specific app tests
python src/manage.py test apps.invoices
python src/manage.py test apps.bank_statements
python src/manage.py test apps.users

# Run with verbosity
python src/manage.py test --verbosity=2

# Run specific test class
python src/manage.py test apps.invoices.tests.InvoiceModelTest

# Run specific test method
python src/manage.py test apps.invoices.tests.InvoiceModelTest.test_calculate_totals
```

### Coverage Report

```bash
# Install coverage
pip install coverage

# Run tests with coverage
coverage run --source='apps' src/manage.py test

# Generate report
coverage report

# Generate HTML report
coverage html
# View at htmlcov/index.html
```

---

## 📊 Coverage Requirements

| Module | Minimum Coverage |
|--------|------------------|
| `apps.invoices.models` | 90% |
| `apps.invoices.views` | 80% |
| `apps.bank_statements.models` | 90% |
| `apps.bank_statements.views` | 80% |
| `apps.users.views` | 85% |
| `apps.accounts.views` | 80% |
| Utility modules | 90% |
| Parser modules | 85% |

---

## 🔧 Test Data & Fixtures

### Factory Pattern (Recommended)

Use `factory_boy` for test data generation:

```bash
pip install factory_boy
```

```python
# apps/invoices/factories.py

import factory
from apps.invoices.models import Invoice, Supplier
from apps.accounts.models import BusinessAccount

class BusinessAccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BusinessAccount
    
    business_name = factory.Sequence(lambda n: f'Company {n}')
    tax_number = factory.Faker('bothify', text='######???')

class SupplierFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Supplier
    
    business_account = factory.SubFactory(BusinessAccountFactory)
    name = factory.Faker('company')
    email = factory.Faker('company_email')

class InvoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invoice
    
    business_account = factory.SubFactory(BusinessAccountFactory)
    invoice_type = 'sale'
    status = 'draft'
    issue_date = factory.Faker('date_this_year')
```

### Using Factories in Tests

```python
from apps.invoices.factories import InvoiceFactory, SupplierFactory

class InvoiceTest(TestCase):
    def test_with_factory(self):
        invoice = InvoiceFactory(status='unpaid')
        self.assertEqual(invoice.status, 'unpaid')
```

---

## ✅ Test Checklist for New Features

When adding a new feature, include tests for:

- [ ] **Model Creation**: Object can be created with valid data
- [ ] **Model Validation**: Invalid data is rejected
- [ ] **Model Methods**: All custom methods work correctly
- [ ] **API CRUD**: Create, Read, Update, Delete work via API
- [ ] **Permissions**: Only authorized users can access
- [ ] **Multi-tenancy**: Data is isolated by business account
- [ ] **Edge Cases**: Empty data, large data, special characters

---

## 🚨 CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml

name: Django Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install coverage
    
    - name: Run tests
      env:
        DATABASE_URL: postgres://postgres:postgres@localhost/test_db
      run: |
        coverage run --source='apps' src/manage.py test
        coverage report --fail-under=80
```

---

## 📝 Test Naming Conventions

Follow these naming patterns for consistency:

```python
def test_<action>_<scenario>_<expected_result>(self):
    """Description of what is being tested"""
    pass

# Examples:
def test_create_invoice_with_valid_data_succeeds(self):
def test_create_invoice_without_date_fails(self):
def test_calculate_totals_with_multiple_items_correct(self):
def test_list_invoices_returns_only_own_business(self):
```
