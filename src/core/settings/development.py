"""
Development settings for the project.
"""

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'adminplus-backend-production.up.railway.app',
    'http://localhost:3000',
    'https://comptago.vercel.app/'
]

CSRF_TRUSTED_ORIGINS = [
    'https://adminplus-backend-production.up.railway.app/',
    'https://comptago.vercel.app/',
]

CORS_ALLOWED_ORIGINS = [
    'https://adminplus-backend-production.up.railway.app',
    'http://localhost:3000',
    'https://comptago.vercel.app',
]

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Email
# Uncomment the line below to log emails to the console instead of sending them
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Use SMTP backend for actual email sending with debugging enabled
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_DEBUG = True
EMAIL_TIMEOUT = 30  # Shorter timeout for debugging

# Development logging configuration - overrides specific parts of the base configuration
LOGGING['loggers']['django.mail']['level'] = 'DEBUG'
LOGGING['loggers']['apps.email']['level'] = 'DEBUG'
LOGGING['handlers']['console']['level'] = 'DEBUG'
LOGGING['handlers']['file_email']['level'] = 'DEBUG'

# Development frontend URL
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:3000')
