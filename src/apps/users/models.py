import uuid
import random
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from apps.common.models import BaseModel


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
#  PERMISSION MODEL
# --------------------------
class Permission(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    resource = models.CharField(max_length=100)
    action = models.CharField(max_length=50)
    
    def __str__(self):
        return f"{self.action} {self.resource}"


# --------------------------
#  ROLE MODEL
# --------------------------
class Role(BaseModel):
    name = models.CharField(max_length=50, unique=True)
    permissions = models.ManyToManyField(Permission, related_name='roles')
    
    def __str__(self):
        return self.name
    
    def manage_permissions(self, permission, add=True):
        """
        Centralized method to add or remove permissions
        :param permission: Permission object to add/remove
        :param add: Boolean to determine whether to add or remove
        """
        if add:
            self.permissions.add(permission)
        else:
            self.permissions.remove(permission)


# --------------------------
#  SYSTEM ROLE CHOICES
# --------------------------
class SystemRole(models.TextChoices):
    ADMIN = 'admin', _('Admin')
    INTERNAL_ACCOUNTANT = 'internal_accountant', _('Internal Accountant')
    EXTERNAL_ACCOUNTANT = 'external_accountant', _('External Accountant')
    EMPLOYEE = 'employee', _('Employee')
    VIEWER = 'viewer', _('Viewer')


# --------------------------
#  USER MODEL
# --------------------------
class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)    
    username = None  # Remove username field
    email = models.EmailField(_('email address'), unique=True, db_index=True)
    
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    company_name = models.CharField(max_length=100, blank=True, null=True)

    is_verified = models.BooleanField(default=False)  # Email verification flag
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, related_name='created_users')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    def __str__(self):
        return self.email
    
    def get_roles(self):
        """Retrieve all roles associated with the user"""
        return [ur.role for ur in self.user_roles.all()]
    
    def assign_role(self, role, system_role=None):
        """
        Assign a role to the user
        :param role: Role object to assign
        :param system_role: Optional system role to assign
        """
        UserRole.objects.create(
            user=self, 
            role=role, 
            system_role=system_role
        )


# --------------------------
#  USER ROLE MODEL
# --------------------------
class UserRole(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles')
    assigned_date = models.DateTimeField(default=timezone.now)
    
    system_role = models.CharField(
        max_length=20,
        choices=SystemRole.choices,
        null=True,
        blank=True
    )
    
    class Meta:
        unique_together = ('user', 'role')
    
    def __str__(self):
        return f"{self.user.email} - {self.role.name}"


# --------------------------
#  PHONE OTP MODEL
# --------------------------
class PhoneOTP(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    phone_number = models.CharField(max_length=15)
    otp = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    def __str__(self):
        return f"{self.phone_number} - {self.otp}"
    
    @staticmethod
    def generate_otp():
        """Generate a 6-digit OTP"""
        return ''.join(random.choices('0123456789', k=6))
    
    @classmethod
    def create_otp_for_user(cls, user, phone_number):
        """
        Create a new OTP for the user
        :param user: User to create OTP for
        :param phone_number: Phone number to send OTP to
        :return: PhoneOTP instance
        """
        otp = cls.generate_otp()
        expires_at = timezone.now() + timezone.timedelta(minutes=10)
        return cls.objects.create(
            user=user,
            phone_number=phone_number,
            otp=otp,
            expires_at=expires_at
        )
    
    def is_expired(self):
        """Check if OTP is expired"""
        return timezone.now() > self.expires_at 