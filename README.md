# AdminPlus Accounting Backend

This is the backend for the AdminPlus Accounting application, a comprehensive accounting and business management system.

## Project Structure

The project is organized in a modular way:

```
adminplus-backend/
├── src/                       # Main source code
│   ├── manage.py              # Django management script
│   ├── core/                  # Project configuration
│   │   ├── settings/          # Split settings for different environments
│   ├── apps/                  # All application modules
│   │   ├── users/             # Authentication & user management
│   │   ├── accounts/          # Business accounts
│   │   ├── accountants/       # Accountant management
│   │   ├── connections/       # Client-accountant connections
│   │   ├── integrations/      # Third-party integrations
│   │   ├── financials/        # Financial features
│   │   ├── notifications/     # Notification system
│   │   └── common/            # Shared utilities
│   └── api/                   # API versioning
└── docs/                      # Documentation
```

## Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Set up environment variables in `.env`
6. Apply migrations: `python src/manage.py migrate`
7. Run the development server: `python src/manage.py runserver`

## API Documentation

API documentation is available at `/api/docs/` when the server is running.
