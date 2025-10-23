# Bank Statement Extraction Feature - Implementation Guide

## 📋 Overview

Complete bank statement extraction feature implementation following your existing invoice extraction architecture.

## 🏗️ Backend Implementation

### Files Created

1. **`apps/bank_statements/models.py`**

   - `BankStatement`: Main model for bank statements
   - `BankTransaction`: Individual transactions
   - `TransactionCategory`: Custom categorization

2. **`apps/bank_statements/gpt_statement_parser.py`**

   - GPT-4 powered extraction
   - Handles complex statement formats
   - Extracts transactions with categorization

3. **`apps/bank_statements/statement_parser.py`**

   - Unified parser (GPT + traditional fallback)
   - Supports PDF, images, CSV, Excel
   - OCR support for scanned documents

4. **`apps/bank_statements/views.py`**

   - REST API endpoints
   - File upload and parsing
   - Transaction management

5. **`apps/bank_statements/serializers.py`**

   - Data serialization
   - Nested transaction data

6. **`apps/bank_statements/urls.py`**
   - URL routing configuration

### Database Models

#### BankStatement

```python
- account_holder
- account_number
- branch
- period_start / period_end
- opening_balance / closing_balance
- currency
- status (pending, processing, completed, failed, review)
- parser_used (gpt, traditional)
- confidence_score
- transactions (ForeignKey)
```

#### BankTransaction

```python
- operation_date / value_date
- reference
- description
- debit / credit
- category (BANK_FEE, ATM_WITHDRAWAL, etc.)
- merchant, location, beneficiary, depositor
- is_reconciled, is_duplicate, needs_review
```

### API Endpoints

Base URL: `/api/v1/bank-statements/`

#### Statements

- `GET /statements/` - List all statements
- `GET /statements/{id}/` - Get statement details
- `POST /statements/` - Create statement
- `PUT /statements/{id}/` - Update statement
- `DELETE /statements/{id}/` - Delete statement
- `POST /statements/parse_statement/` - Parse file
- `POST /statements/create_from_parsed/` - Create from parsed data
- `POST /statements/{id}/recalculate_totals/` - Recalculate

#### Transactions

- `GET /transactions/` - List transactions
- `GET /transactions/{id}/` - Get transaction
- `PUT /transactions/{id}/` - Update transaction
- `POST /transactions/{id}/reconcile/` - Mark reconciled
- `POST /transactions/{id}/mark_duplicate/` - Mark duplicate

#### Categories

- `GET /categories/` - List categories
- `POST /categories/` - Create category
- `PUT /categories/{id}/` - Update category
- `DELETE /categories/{id}/` - Delete category

## 🎨 Frontend Implementation

### Files Created

1. **`src/api/invoices/bankStatements.js`**

   - All API calls for bank statements
   - File upload with progress
   - Transaction management

2. **`src/hooks/invoices/useBankStatements.js`**

   - React hook for statements
   - State management
   - Error handling

3. **`src/hooks/invoices/useBankTransactions.js`**
   - React hook for transactions
   - Reconciliation actions

### Usage Example

```javascript
import useBankStatements from '../../hooks/invoices/useBankStatements';

function BankStatementUpload() {
  const {
    parseStatement,
    createFromParsed,
    parsedData,
    loading,
    parsingProgress
  } = useBankStatements();

  const handleFileUpload = async (file) => {
    try {
      // Parse the file
      const data = await parseStatement(file, true); // use GPT

      // Review and create statement
      await createFromParsed(data, file);

      console.log('Statement created successfully!');
    } catch (error) {
      console.error('Error:', error);
    }
  };

  return (
    // Your UI component
  );
}
```

## 🔧 Configuration

### 1. Install Dependencies

```bash
cd adminplus-backend
pip install -r requirements.txt
```

Required packages:

- `openai>=1.0.0` - GPT API
- `PyPDF2` - PDF text extraction
- `pytesseract` - OCR
- `pdf2image` - PDF to image conversion
- `Pillow` - Image processing
- `openpyxl` - Excel file support

### 2. System Dependencies

#### Windows

```powershell
# Install Tesseract OCR
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
# Add to PATH

# Install Poppler
# Download from: https://github.com/oschwartz10612/poppler-windows/releases/
# Add bin/ folder to PATH
```

#### macOS

```bash
brew install tesseract
brew install poppler
```

#### Linux

```bash
sudo apt-get install tesseract-ocr
sudo apt-get install poppler-utils
```

### 3. Environment Variables

Add to `.env` file:

```env
# OpenAI API Key (required for GPT parsing)
OPENAI_API_KEY=your_openai_api_key_here
GPT_API_KEY=your_openai_api_key_here

# AWS S3 (for file storage)
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_STORAGE_BUCKET_NAME=your_bucket_name
AWS_S3_REGION_NAME=eu-north-1
```

### 4. Database Migration

```bash
cd src
python manage.py makemigrations bank_statements
python manage.py migrate
```

### 5. Create Superuser (if needed)

```bash
python manage.py createsuperuser
```

## 📤 File Upload Flow

### 1. Upload & Parse

```javascript
const file = event.target.files[0];
const parsedData = await parseStatement(file, true); // GPT parsing
```

### 2. Review Parsed Data

```javascript
console.log(parsedData);
// {
//   "statement": {
//     "account_holder": "...",
//     "account_number": "...",
//     "transactions": [...]
//   }
// }
```

### 3. Create Statement

```javascript
await createFromParsed(parsedData, file);
```

## 🎯 Supported Formats

- **PDF**: Bank statement PDFs (text or scanned)
- **Images**: JPG, PNG (with OCR)
- **CSV**: Comma-separated transaction data
- **Excel**: .xlsx, .xls files

## 🧠 GPT Parser Features

### Extracted Data

- Account information (holder, number, branch)
- Statement period (start/end dates)
- Opening/closing balances
- All transactions with:
  - Dates (operation & value)
  - Amounts (debit/credit)
  - Descriptions
  - Categories (auto-classified)
  - Merchants, locations
  - Payment methods
  - Beneficiaries/depositors

### Transaction Categories

- BANK_FEE
- ATM_WITHDRAWAL
- BILL_PAYMENT
- LOAN_REPAYMENT
- TAX
- TRANSFER_OUT / TRANSFER_IN
- CASH_DEPOSIT
- CARD_PAYMENT
- CHECK_PAYMENT
- SALARY
- INTEREST
- OTHER

## 🔍 Example JSON Output

```json
{
  "statement": {
    "account_holder": "EL KRYMY ABDELILAH",
    "account_number": "164 735 21111 0511617 000 1 89",
    "branch": "6440 TAHRIR",
    "period_start": "2025-08-01",
    "period_end": "2025-08-31",
    "opening_balance": 5709.58,
    "closing_balance": 7053.18,
    "transactions": [
      {
        "operation_date": "2025-08-01",
        "value_date": "2025-07-29",
        "reference": "600007",
        "description": "COMMISSION",
        "category": "BANK_FEE",
        "debit": 6.0,
        "credit": 0,
        "merchant": null,
        "location": null
      }
    ]
  }
}
```

## ⚙️ Advanced Features

### Transaction Reconciliation

Match transactions with invoices for automated accounting.

### Duplicate Detection

Identify and flag duplicate transactions.

### Custom Categories

Create business-specific transaction categories with keywords.

### Batch Processing

Process multiple statements at once.

## 🚀 Next Steps

### 1. Test the Backend

```bash
cd adminplus-backend/src
python manage.py runserver
```

Visit: `http://localhost:8000/api/v1/bank-statements/`

### 2. Test File Parsing

Use Swagger UI or Postman:

- Endpoint: `POST /api/v1/bank-statements/statements/parse_statement/`
- Upload a bank statement file
- Review parsed data

### 3. Build Frontend UI

Create components for:

- File upload with progress
- Statement list view
- Transaction details
- Reconciliation interface
- Reports and analytics

## 📊 Database Schema

```sql
BankStatement (1) ---- (N) BankTransaction
BusinessAccount (1) ---- (N) BankStatement
BusinessAccount (1) ---- (N) TransactionCategory
Invoice (1) ---- (N) BankTransaction (matched_invoice)
```

## 🔐 Security Considerations

- File validation (size, type)
- Authenticated endpoints only
- Business account isolation
- File storage encryption (S3)
- API rate limiting for GPT calls

## 💡 Tips

1. **GPT vs Traditional**: Use GPT for complex formats, traditional for simple CSV/Excel
2. **File Size**: Optimize large PDFs before upload
3. **OCR Quality**: Better image quality = better extraction
4. **Batch Processing**: Group statements by period for efficiency
5. **Error Handling**: Always review parsed data before creating records

## 📝 Maintenance

- Monitor GPT API usage/costs
- Regularly update transaction categories
- Review failed parses for improvements
- Back up statement files

## ✅ Checklist

- [x] Backend models created
- [x] API endpoints implemented
- [x] GPT parser configured
- [x] Traditional parser fallback
- [x] Frontend API calls created
- [x] React hooks implemented
- [x] Database migrations ready
- [x] Documentation complete
- [ ] UI components (next step)
- [ ] Integration testing
- [ ] Deployment configuration

---

**Created**: October 22, 2025
**Version**: 1.0.0
**Architecture**: Django REST + React.js
