from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, AbstractUser
from django.utils import timezone
import uuid

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('account_type', 'ADMIN')  # Set account_type to ADMIN for superusers

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    # Remove the username field
    username = None

    # Account type choices
    ACCOUNT_TYPE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('ACCOUNTANT', 'Accountant'),
        ('CLIENT', 'Client'),
    ]

    # Fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, verbose_name='email address')
    account_type = models.CharField(max_length=50, choices=ACCOUNT_TYPE_CHOICES, default='CLIENT')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    currency_preference = models.CharField(max_length=10, default='MAD')
    language_preference = models.CharField(max_length=10, default='fr')
    timezone = models.CharField(max_length=50, default='Africa/Casablanca')
    last_login = models.DateTimeField(blank=True, null=True)
    failed_login_attempts = models.IntegerField(default=0)
    billing_info = models.JSONField(default=dict, blank=True, null=True)

    # Self-referential foreign key for assigned accountant
    assigned_accountant = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clients'
    )

    # Use email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    # Assign the custom UserManager
    objects = CustomUserManager()

    def __str__(self):
        return self.email