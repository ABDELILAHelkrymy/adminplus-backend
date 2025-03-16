import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _



# --------------------------
#  USER MANAGER
# --------------------------
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)
    


# --------------------------
#  ROLE MODEL
# --------------------------
class Role(models.Model):
    name = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


# --------------------------
#  USER MODEL
# --------------------------
class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    username = None  # Remove username field
    email = models.EmailField(_('email address'), unique=True)
    
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, related_name='users')
    
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    company_name = models.CharField(max_length=100, blank=True, null=True)

    is_verified = models.BooleanField(default=False)  # Email verification flag
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    def __str__(self):
        return f"{self.email} ({self.role.name if self.role else 'No Role'})"


# --------------------------
#  ACCOUNTANT-CLIENT RELATIONSHIP
# --------------------------
class AccountantClientRelationship(models.Model):
    accountant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clients')
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accountants')

    is_primary = models.BooleanField(default=False)  # Only one primary accountant per client

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('accountant', 'client')

    def __str__(self):
        return f"{self.accountant.email} - {self.client.email} ({self.status})"


# --------------------------
#  USER PROFILE
# --------------------------
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    tax_number = models.CharField(max_length=50, blank=True, null=True)  
    business_type = models.CharField(max_length=50, blank=True, null=True)
    
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        ('MAD', 'Moroccan Dirham'),
    ]
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('fr', 'French'),
        ('ar', 'Arabic'),
    ]
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')

    def __str__(self):
        return f"Profile for {self.user.email}"
