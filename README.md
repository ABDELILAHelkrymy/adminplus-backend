# AdminPlus Accounting Backend

This is the backend for the **ComptaGo (AdminPlus)** application, a comprehensive accounting and business management system. Built with **Django** and **Django Rest Framework (DRF)**, it provides a robust API for the React frontend, handling data persistence, authentication, and complex business logic.

## 🏗 Architecture

The project follows a modular architecture using dedicated Django apps for different domains:

- **`users`**: Authentication, user profiles, and authorization.
- **`accounts`**: Business account management and switching.
- **`financials`**: Core accounting logic, transactions, and ledgers.
- **`invoices`**: Management of outcome (sales) and income (purchase) invoices.
- **`partners`**: Supplier and Customer entity management.
- **`integrations`**: External services (Email, OCR, Company Data Scrapers).

## 🛠 Tech Stack

- **Framework:** Django 4.x, Django Rest Framework (DRF) 3.15+
- **Database:** PostgreSQL (Production), SQLite (Dev)
- **Authentication:** JWT (JSON Web Tokens) via `djangorestframework-simplejwt`
- **Storage:** AWS S3 (via `django-storages` & `boto3`) for file uploads.
- **PDF Engine:** `ReportLab`, `PyPDF2`, `pdf2image` for generation and manipulation.
- **OCR & Parsing:** `pytesseract`, `OpenCV` for invoice data extraction.
- **Task Queue:** (Planned/Implicit in structure for async tasks)
- **Documentation:** Swagger/OpenAPI via `drf-yasg`.

## ✨ Key Features

### 🔐 Authentication & Security
- **JWT Auth:** Secure stateless authentication.
- **Role-Based Access Control (RBAC):** Granular permissions for Business Owners, Accountants, and Viewers.
- **Business Switching:** Support for users managing multiple companies under one login.

### 🧾 Invoice Management API
- **CRUD Operations:** Complete management of Invoice lifecycles.
- **PDF Generation:** Server-side generation of standardized PDF invoices.
- **OCR Pipeline:** 
  1.  **Upload:** API accepts file uploads.
  2.  **Process:** Extracts text and metadata (Date, Total, Tax ID) using OCR.
  3.  **Map:** Associates extracted data with existing Partners or suggests new ones.

### 🏦 Financial Processing
- **Bank Statement Parsing:** specialized parsers for Moroccan bank formats (PDF/CSV).
- **Auto-Reconciliation Logic:** Algorithms to match statement lines with recorded invoices.
- **Reporting Data:** Aggregation endpoints for Dashboard metrics (Revenue, Expenses, P&L).

### 🌐 Integrations
- **Company Lookup:** Scraper integration (`welipro.com`) to fetch firm details by ICE/RC.
- **Email:** Transactional emails (via SMTP/SendGrid) for invoice sending.

## 🚀 Setup & Installation

### Prerequisites
- Python 3.8+
- PostgreSQL (recommended) or SQLite

### Local Development

1.  **Clone the repository** and navigate to `adminplus-backend`.

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    ```

3.  **Activate the environment:**
    - Windows: `venv\Scripts\activate`
    - Linux/Mac: `source venv/bin/activate`

4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Environment Configuration:**
    - Copy `.env.dist` to `.env`:
      ```bash
      cp .env.dist .env
      ```
    - Update `.env` with your database credentials and secret keys.

6.  **Apply Database Migrations:**
    ```bash
    python src/manage.py migrate
    ```

7.  **Run the Server:**
    ```bash
    python src/manage.py runserver
    ```
    The API will be available at `http://127.0.0.1:8000/`.

## 📚 API Documentation

Once the server is running, you can access the interactive API documentation at:
- **Swagger UI:** `http://127.0.0.1:8000/api/docs/`
- **ReDoc:** `http://127.0.0.1:8000/api/redoc/`

## 🧪 Testing

Run the test suite to ensure system stability:
```bash
python src/manage.py test
```
