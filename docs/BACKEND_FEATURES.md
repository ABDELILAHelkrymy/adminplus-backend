# ComptaGo Backend Features Documentation

This document provides comprehensive documentation for the ComptaGo (AdminPlus) backend, enabling developers and AI agents to understand and contribute to the project.

## 📁 Project Structure

```
adminplus-backend/
├── src/
│   ├── api/
│   │   └── v1/
│   │       └── urls.py          # Main API routing
│   ├── apps/
│   │   ├── accounts/            # Business account management
│   │   ├── accountants/         # Accountant invitation system
│   │   ├── accounting/          # Financial accounting logic
│   │   ├── bank_statements/     # Bank statement processing
│   │   ├── common/              # Shared base models
│   │   ├── connections/         # External connections
│   │   ├── financials/          # Financial transactions
│   │   ├── integrations/        # Third-party integrations
│   │   ├── invoices/            # Invoice management
│   │   ├── notifications/       # Notification system
│   │   └── users/               # User authentication
│   ├── core/                    # Django settings
│   └── manage.py
├── docs/                        # Documentation files
├── requirements.txt
└── README.md
```

---

## 🔧 Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | Django 4.x, Django REST Framework 3.15+ |
| Database | PostgreSQL (Production), SQLite (Dev) |
| Authentication | JWT via `djangorestframework-simplejwt` |
| File Storage | AWS S3 (`django-storages`, `boto3`) |
| PDF Engine | ReportLab, PyPDF2, pdf2image |
| OCR | Pytesseract, OpenCV |
| API Docs | Swagger via `drf-yasg` |

---

## 📱 Django Apps Reference

### 1. Users App (`apps.users`)

Handles user authentication, registration, and profile management.

**Models:**
- `User` - Custom user model with email authentication
- `Role` - Custom roles for permissions
- `SystemRole` - System-defined roles (Owner, Accountant, Viewer)
- `UserRole` - User-role assignments
- `PhoneOTP` - OTP for phone verification

**Key Endpoints:**
```
POST   /api/v1/users/login/                    # User login
POST   /api/v1/users/token/refresh/            # Refresh JWT
POST   /api/v1/users/password/reset/request/   # Request password reset
POST   /api/v1/users/password/reset/confirm/   # Confirm password reset
POST   /api/v1/users/password/change/          # Change password
GET    /api/v1/users/system-roles/             # List system roles
CRUD   /api/v1/users/internal-users/           # Manage internal users
POST   /api/v1/users/email/verification/       # Email verification
POST   /api/v1/users/phone/verify/request/     # Request OTP
POST   /api/v1/users/phone/verify/confirm/     # Verify OTP
```

---

### 2. Accounts App (`apps.accounts`)

Manages business accounts and settings.

**Models:**
- `BusinessAccount` - Company/business information
- `AccountSettings` - Business-specific settings (currency, invoice prefix)

**Key Endpoints:**
```
POST   /api/v1/accounts/register/admin/        # Register new business admin
GET    /api/v1/accounts/business-info/         # Get current business info
CRUD   /api/v1/accounts/business-accounts/     # Manage business accounts
CRUD   /api/v1/accounts/account-settings/      # Manage settings
POST   /api/v1/accounts/business-accounts/{id}/upload_logo/  # Upload logo
```

**Key Features:**
- Multi-tenant support (users can manage multiple businesses)
- Logo upload to S3
- Customizable invoice numbering with prefixes

---

### 3. Invoices App (`apps.invoices`)

Core invoicing functionality.

**Models:**
- `Invoice` - Main invoice (Purchase/Sale)
- `InvoiceLineItem` - Line items with quantity, price, VAT
- `InvoiceAttachment` - File attachments
- `Supplier` - Supplier/vendor entities
- `Customer` - Client entities
- `Category` - Invoice categories
- `PaymentMethod` - Payment methods
- `Project` - Project management with time tracking
- `Article` - Product/service catalog
- `TimeEntry` - Time tracking for projects

**Key Endpoints:**
```
# Partners
CRUD   /api/v1/invoices/suppliers/             # Manage suppliers
CRUD   /api/v1/invoices/customers/             # Manage customers

# Invoices
CRUD   /api/v1/invoices/invoices/              # Manage invoices
GET    /api/v1/invoices/invoices/{id}/pdf/     # Generate PDF
POST   /api/v1/invoices/invoices/upload/       # Upload & OCR parse
POST   /api/v1/invoices/invoices/{id}/send_email/  # Email invoice
POST   /api/v1/invoices/invoices/{id}/mark_paid/   # Mark as paid
POST   /api/v1/invoices/invoices/{id}/duplicate/   # Duplicate invoice

# Nested Resources
CRUD   /api/v1/invoices/invoices/{id}/line-items/
CRUD   /api/v1/invoices/invoices/{id}/attachments/

# Other
CRUD   /api/v1/invoices/categories/            # Invoice categories
CRUD   /api/v1/invoices/payment-methods/       # Payment methods
CRUD   /api/v1/invoices/projects/              # Project management
CRUD   /api/v1/invoices/articles/              # Article catalog
CRUD   /api/v1/invoices/time-entries/          # Time tracking
```

**Invoice Types:**
- `purchase` - Incoming invoices (from suppliers)
- `sale` - Outgoing invoices (to customers)

**Invoice Status Flow:**
```
draft → unpaid → overdue → paid → cancelled
```

---

### 4. Bank Statements App (`apps.bank_statements`)

Bank statement processing and reconciliation.

**Models:**
- `BankStatement` - Uploaded bank statement
- `BankTransaction` - Individual transactions
- `TransactionCategory` - Transaction categories with keywords

**Key Endpoints:**
```
CRUD   /api/v1/bank-statements/statements/     # Manage statements
POST   /api/v1/bank-statements/statements/parse_statement/      # Parse PDF
POST   /api/v1/bank-statements/statements/create_from_parsed/   # Create from parsed data
GET    /api/v1/bank-statements/statements/moroccan_banks/       # List banks

CRUD   /api/v1/bank-statements/transactions/   # Manage transactions
POST   /api/v1/bank-statements/transactions/{id}/reconcile/     # Reconcile
POST   /api/v1/bank-statements/transactions/{id}/reconcile_with_invoice/
GET    /api/v1/bank-statements/transactions/{id}/suggested_matches/
GET    /api/v1/bank-statements/transactions/export/             # Export CSV/Excel

CRUD   /api/v1/bank-statements/categories/     # Transaction categories
```

**Supported Moroccan Banks:**
- Attijariwafa Bank
- BCP (Banque Centrale Populaire)
- BMCE Bank of Africa
- BMCI
- CIH Bank
- Crédit du Maroc
- Crédit Agricole du Maroc
- Société Générale Maroc
- Al Barid Bank
- CFG Bank, Umnia Bank

---

### 5. Integrations App (`apps.integrations`)

External service integrations.

**Key Features:**
- **Company Lookup**: Scraper for `welipro.com` to fetch company details by ICE/RC
- **Email Integration**: SMTP/SendGrid for transactional emails

**Endpoints:**
```
GET    /api/v1/integrations/company-lookup/    # Lookup company by ICE
```

---

### 6. Other Apps

| App | Purpose |
|-----|---------|
| `financials` | Financial transactions, accounts, categories |
| `accountants` | Accountant invitation and assignment system |
| `connections` | External integrations management |
| `notifications` | In-app notification system |
| `accounting` | Core accounting operations |
| `common` | Shared `BaseModel` with timestamps |

---

## 🔐 Authentication & Permissions

### JWT Authentication

All protected endpoints require a valid JWT token:
```http
Authorization: Bearer <access_token>
```

**Token Refresh:**
```python
POST /api/v1/users/token/refresh/
Body: { "refresh": "<refresh_token>" }
```

### Role-Based Access Control (RBAC)

**System Roles:**
| Role | Permissions |
|------|-------------|
| `business_owner` | Full access to all business resources |
| `accountant` | Access to financial data (assigned businesses only) |
| `viewer` | Read-only access |
| `internal_user` | Limited access defined by business owner |

**Custom Permission Classes:**
- `IsAuthenticated` - Must be logged in
- `IsBusinessOwner` - Must be the business owner

---

## 🧪 OCR Invoice Processing

The system can extract data from PDF/image invoices:

1. **Upload**: Client uploads a PDF/image file
2. **Parse**: `InvoiceParser` extracts text using OCR (Tesseract)
3. **Extract**: Regex patterns extract:
   - Invoice number
   - Date
   - Total amount
   - VAT amount
   - Supplier/Customer info (ICE, Name, Address)
4. **Return**: Extracted data for user review

**Usage:**
```python
POST /api/v1/invoices/invoices/upload/
Content-Type: multipart/form-data
Body: { "file": <binary> }
```

---

## 📄 PDF Generation

Invoices can be generated as PDFs using ReportLab:

```python
GET /api/v1/invoices/invoices/{id}/pdf/
Response: application/pdf
```

---

## 🛠 Adding New Features

### Creating a New Django App

1. Create the app:
   ```bash
   cd src
   python manage.py startapp new_feature
   mv new_feature apps/
   ```

2. Add to `INSTALLED_APPS` in `core/settings.py`:
   ```python
   INSTALLED_APPS = [
       ...
       'apps.new_feature',
   ]
   ```

3. Create standard files:
   - `models.py` - Data models
   - `serializers.py` - DRF serializers
   - `views.py` - ViewSets or APIViews
   - `urls.py` - URL patterns

4. Register URLs in `api/v1/urls.py`:
   ```python
   path('new-feature/', include('apps.new_feature.urls')),
   ```

### Model Pattern

Extend `BaseModel` for automatic timestamps:
```python
from apps.common.models import BaseModel

class MyModel(BaseModel):
    business_account = models.ForeignKey(
        'accounts.BusinessAccount',
        on_delete=models.CASCADE,
        related_name='my_models'
    )
    name = models.CharField(max_length=100)
```

### ViewSet Pattern

Standard ViewSet with business account filtering:
```python
class MyModelViewSet(viewsets.ModelViewSet):
    serializer_class = MyModelSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        business_account = user.active_business_account
        return MyModel.objects.filter(business_account=business_account)

    def perform_create(self, serializer):
        user = self.request.user
        business_account = user.active_business_account
        serializer.save(business_account=business_account)
```

---

## 🌐 API Documentation

Access interactive API docs when server is running:
- **Swagger UI**: `http://localhost:8000/api/docs/`
- **ReDoc**: `http://localhost:8000/api/redoc/`

---

## 📂 File Structure Conventions

| File | Purpose |
|------|---------|
| `models.py` | Django models (database schema) |
| `serializers.py` | DRF serializers for API I/O |
| `views.py` | ViewSets and APIViews |
| `urls.py` | URL routing for the app |
| `admin.py` | Django admin configuration |
| `signals.py` | Django signals (post_save, etc.) |
| `utils.py` | Helper functions |
| `permissions.py` | Custom DRF permissions |
| `tests.py` | Unit and integration tests |

---

## 🚀 Development Commands

```bash
# Start development server
python src/manage.py runserver

# Create migrations
python src/manage.py makemigrations

# Apply migrations
python src/manage.py migrate

# Run tests
python src/manage.py test

# Create superuser
python src/manage.py createsuperuser
```
