import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver



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
    email = models.EmailField(_('email address'), unique=True, db_index=True)
    
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, related_name='users')
    
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    company_name = models.CharField(max_length=100, blank=True, null=True)

    is_verified = models.BooleanField(default=False)  # Email verification flag
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, related_name='created_users')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    def __str__(self):
        return f"{self.email} ({self.role.name if self.role else 'No Role'})"


# --------------------------
#  ACCOUNTANT-CLIENT RELATIONSHIP
# --------------------------
class AccountantClientRelationship(models.Model):
    accountant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clients', db_index=True)
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accountants', db_index=True)

    is_primary = models.BooleanField(default=False)  # Only one primary accountant per client

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_relationships')

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
    
class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField()

    def __str__(self):
        return f"{self.user.email} - {self.action} on {self.model}"
    
@receiver(post_save)
def log_save(sender, instance, created, **kwargs):
    action = 'create' if created else 'update'
    AuditLog.objects.create(
        user=instance.last_modified_by if hasattr(instance, 'last_modified_by') else None,
        action=action,
        model=sender.__name__,
        object_id=instance.id,
        details=instance.__dict__
    )

@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    AuditLog.objects.create(
        user=instance.last_modified_by if hasattr(instance, 'last_modified_by') else None,
        action='delete',
        model=sender.__name__,
        object_id=instance.id,
        details=instance.__dict__
    )
