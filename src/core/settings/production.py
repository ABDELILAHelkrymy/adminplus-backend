"""
Production settings for the project.
"""

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DJANGO_DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = [
    'adminplus-backend-production.up.railway.app',
    'diligent-dream-production.up.railway.app',
    'comptago.vercel.app'
]

CSRF_TRUSTED_ORIGINS = [
    'https://adminplus-backend-production.up.railway.app',
    'https://diligent-dream-production.up.railway.app',
    'https://comptago.vercel.app',
]

CORS_ALLOWED_ORIGINS = [
    'https://adminplus-backend-production.up.railway.app',
    'https://diligent-dream-production.up.railway.app',
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
# CONN_MAX_AGE=0 is required for Railway: Railway's proxy kills long-lived idle
# connections, so persistent connections cause 'server closed the connection
# unexpectedly' errors. Use 0 to open a fresh connection per request.
CONN_MAX_AGE = config('CONN_MAX_AGE', default=0, cast=int)
DATABASE_URL = config('DATABASE_URL', default='', cast=str)
if DATABASE_URL:
    import dj_database_url
    DATABASES['default'] = dj_database_url.config(
        default=DATABASE_URL,
        conn_health_checks=True,
        conn_max_age=CONN_MAX_AGE,
        ssl_require=True,
    )

# Security settings
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# This helps Django determine if it's behind a proxy that terminates SSL
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# Email configuration with timeout handling
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('EMAIL_HOST_USER', default='')
EMAIL_FROM = config('EMAIL_HOST_USER', default='')

# Add email timeout settings
EMAIL_TIMEOUT = 30  # 30 seconds timeout
EMAIL_USE_SSL = False  # Set to True if using port 465

# Gunicorn timeout settings
GUNICORN_TIMEOUT = 120  # Increase worker timeout

# Logging configuration for email debugging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        },
        'file_email': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'email.log',
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.mail': {
            'handlers': ['file_email'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.email': {
            'handlers': ['file_email'],
            'level': 'INFO',
            'propagate': False,
        },
    }
}

# Frontend URL for email links and CORS
FRONTEND_URL = config('FRONTEND_URL', default='https://comptago.vercel.app')
