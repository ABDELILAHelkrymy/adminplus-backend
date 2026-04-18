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
    'diligent-dream-production.up.railway.app',
    'http://localhost:3000',
    'https://comptago.vercel.app/'
]

CSRF_TRUSTED_ORIGINS = [
    'https://adminplus-backend-production.up.railway.app/',
    'https://diligent-dream-production.up.railway.app/',
    'https://comptago.vercel.app/',
]

CORS_ALLOWED_ORIGINS = [
    'https://adminplus-backend-production.up.railway.app',
    'https://diligent-dream-production.up.railway.app',
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
# Use PostgreSQL in production
CONN_MAX_AGE = config('CONN_MAX_AGE', default=600, cast=int)
DATABASE_URL = config('DATABASE_URL', default='', cast=str)
if DATABASE_URL:
    import dj_database_url
    DATABASES['default'] = dj_database_url.config(
        default=DATABASE_URL,
        conn_health_checks=True,
        conn_max_age=CONN_MAX_AGE,
    )

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

# Modern Django Storage Configuration
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3boto3.S3StaticStorage",
    },
}

# AWS Configuration
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default='admin-plus')
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='eu-north-1')
AWS_S3_FILE_OVERWRITE = False
AWS_QUERYSTRING_AUTH = True
AWS_DEFAULT_ACL = None
AWS_S3_SIGNATURE_VERSION = 's3v4'

# URLs
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
