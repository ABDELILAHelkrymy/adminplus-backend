import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


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
class Permission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    resource = models.CharField(max_length=100)
    action = models.CharField(max_length=50)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.action} {self.resource}"


# --------------------------
#  ROLE MODEL
# --------------------------
class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    permissions = models.ManyToManyField(Permission, related_name='roles')
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
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
class UserRole(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles')
    assigned_date = models.DateTimeField(default=timezone.now)
    
    system_role = models.CharField(
        max_length=20,
        choices=SystemRole.choices,
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'role')
    
    def __str__(self):
        return f"{self.user.email} - {self.role.name}"


# --------------------------
#  BUSINESS ACCOUNT MODEL
# --------------------------
class BusinessAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business_name = models.CharField(max_length=100)
    tax_number = models.CharField(max_length=50, blank=True, null=True)
    business_address = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    
    primary_user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='owned_business')
    internal_users = models.ManyToManyField(User, related_name='business_accounts')
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.business_name
    
    def manage_users(self, user, add=True):
        """
        Centralized method to add or remove internal users
        :param user: User to add or remove
        :param add: Boolean to determine whether to add or remove
        """
        if add:
            self.internal_users.add(user)
        else:
            self.internal_users.remove(user)
    
    def prepare_accountant_invitation(self, email, created_by):
        """
        Prepare an accountant invitation
        :param email: Email of the accountant
        :param created_by: User creating the invitation
        :return: AccountantInvitation instance
        """
        return AccountantInvitation.objects.create(
            sender=self,
            accountant_email=email,
            expiry_date=timezone.now() + timezone.timedelta(days=7),
            status=InvitationStatus.PENDING,
            created_by=created_by
        )


# --------------------------
#  EXTERNAL ACCOUNTANT ACCOUNT MODEL
# --------------------------
class ExternalAccountantAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    accountant_name = models.CharField(max_length=100)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    tax_number = models.CharField(max_length=50, blank=True, null=True)
    contact_phone = models.CharField(max_length=15, blank=True, null=True)
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='accountant_account')
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.accountant_name
    
    @classmethod
    def create_account(cls, user, accountant_name, **kwargs):
        """
        Create an external accountant account
        :param user: User associated with the account
        :param accountant_name: Name of the accountant
        :param kwargs: Additional fields
        :return: ExternalAccountantAccount instance
        """
        return cls.objects.create(
            user=user,
            accountant_name=accountant_name,
            **kwargs
        )
    
    def manage_invitations(self):
        """
        Retrieve pending invitations for this accountant
        :return: Queryset of pending invitations
        """
        return AccountantInvitation.objects.filter(
            accountant_email=self.user.email,
            status=InvitationStatus.PENDING
        )


# --------------------------
#  INVITATION STATUS CHOICES
# --------------------------
class InvitationStatus(models.TextChoices):
    PENDING = 'pending', _('Pending')
    ACCEPTED = 'accepted', _('Accepted')
    REJECTED = 'rejected', _('Rejected')
    EXPIRED = 'expired', _('Expired')
    CANCELLED = 'cancelled', _('Cancelled')


# --------------------------
#  ACCOUNTANT INVITATION MODEL
# --------------------------
class AccountantInvitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name='sent_invitations')
    accountant_email = models.EmailField()
    recipient = models.ForeignKey(ExternalAccountantAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_invitations')
    
    sent_date = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateTimeField()
    response_date = models.DateTimeField(null=True, blank=True)
    invitation_message = models.TextField(blank=True, null=True)
    
    status = models.CharField(
        max_length=10,
        choices=InvitationStatus.choices,
        default=InvitationStatus.PENDING
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_invitations')

    def __str__(self):
        return f"Invitation from {self.sender.business_name} to {self.accountant_email}"
    
    def update_status(self, new_status):
        """
        Update invitation status with timestamp
        :param new_status: New status to set
        """
        self.status = new_status
        self.response_date = timezone.now()
        self.save()
    
    def is_expired(self):
        """
        Check if invitation is expired
        :return: Boolean indicating expiration status
        """
        return timezone.now() > self.expiry_date


# --------------------------
#  CONNECTION ACCESS LEVEL CHOICES
# --------------------------
class ConnectionAccessLevel(models.TextChoices):
    FULL_ACCESS = 'full_access', _('Full Access')
    READ_ONLY = 'read_only', _('Read Only')
    REPORTS_ONLY = 'reports_only', _('Reports Only')
    CUSTOM = 'custom', _('Custom')


# --------------------------
#  CLIENT-ACCOUNTANT CONNECTION
# --------------------------
class ClientAccountantConnection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name='accountant_connections')
    accountant = models.ForeignKey(ExternalAccountantAccount, on_delete=models.CASCADE, related_name='client_connections')
    
    connection_date = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    last_access = models.DateTimeField(null=True, blank=True)
    
    access_level = models.CharField(
        max_length=20,
        choices=ConnectionAccessLevel.choices,
        default=ConnectionAccessLevel.READ_ONLY
    )
    
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_connections')

    class Meta:
        unique_together = ('client', 'accountant')

    def __str__(self):
        return f"{self.client.business_name} - {self.accountant.accountant_name}"
    
    def manage_connection_status(self, status=None):
        """
        Manage connection status (active/inactive)
        :param status: Optional boolean to set connection status
        """
        if status is not None:
            self.is_active = status
        self.save()
    
    def update_access_level(self, level):
        """
        Update connection access level
        :param level: New access level to set
        """
        self.access_level = level
        self.save()
    
    def record_access(self):
        """
        Record the last access time
        """
        self.last_access = timezone.now()
        self.save()


# --------------------------
#  CONNECTION ACTIVITY MODEL
# --------------------------
class ConnectionActivity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(ClientAccountantConnection, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='connection_activities')
    
    timestamp = models.DateTimeField(default=timezone.now)
    action_type = models.CharField(max_length=50)
    description = models.TextField()

    def __str__(self):
        return f"{self.connection} - {self.action_type} by {self.user.email}"
    
    @classmethod
    def log_activity(cls, connection, user, action_type, description):
        """
        Log an activity for a connection
        :param connection: ClientAccountantConnection instance
        :param user: User performing the action
        :param action_type: Type of action
        :param description: Description of the action
        :return: Created ConnectionActivity instance
        """
        return cls.objects.create(
            connection=connection,
            user=user,
            action_type=action_type,
            description=description
        )


# --------------------------
#  DATA SHARING PREFERENCE MODEL
# --------------------------
class DataSharingPreference(models.Model):
    connection = models.OneToOneField(ClientAccountantConnection, on_delete=models.CASCADE, related_name='data_sharing')
    
    share_invoices = models.BooleanField(default=False)
    share_expenses = models.BooleanField(default=False)
    share_bank_data = models.BooleanField(default=False)
    share_tax_documents = models.BooleanField(default=False)
    share_reports = models.BooleanField(default=False)
    
    last_updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='updated_sharing_preferences')

    def __str__(self):
        return f"Sharing preferences for {self.connection}"
    
    def update_preferences(self, **kwargs):
        """
        Update data sharing preferences
        :param kwargs: Dictionary of preferences to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save()


# --------------------------
#  ACCOUNT SETTINGS MODEL
# --------------------------
class AccountSettings(models.Model):
    business_account = models.OneToOneField(BusinessAccount, on_delete=models.CASCADE, related_name='settings')
    
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('MAD', 'Moroccan Dirham'),
    ]
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('fr', 'French'),
        ('ar', 'Arabic'),
    ]
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    
    notification_emails = models.BooleanField(default=True)
    two_factor_auth = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Settings for {self.business_account.business_name}"
    
    def update_settings(self, **kwargs):
        """
        Update account settings
        :param kwargs: Dictionary of settings to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save()


# --------------------------
#  INTEGRATION MODEL
# --------------------------
class Integration(models.Model):
    business_account = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name='integrations')
    
    name = models.CharField(max_length=100)
    integration_type = models.CharField(max_length=50)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    auth_data = models.JSONField(blank=True, null=True)
    settings = models.JSONField(blank=True, null=True)
    
    last_sync = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} integration for {self.business_account.business_name}"
    
    def update_sync_status(self):
        """
        Update the last sync timestamp
        """
        self.last_sync = timezone.now()
        self.save()


# --------------------------
#  AUDIT LOG MODEL
# --------------------------
# class AuditLog(models.Model):
#     user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
#     action = models.CharField(max_length=100)
#     model = models.CharField(max_length=100)
#     object_id = models.CharField(max_length=100)
#     timestamp = models.DateTimeField(default=timezone.now)
#     details = models.JSONField()

#     def __str__(self):
#         return f"{self.user.email if self.user else 'System'} - {self.action} on {self.model}"


# --------------------------
#  SIGNAL RECEIVERS
# --------------------------
# @receiver(post_save, sender=ClientAccountantConnection)
# def create_data_sharing_preferences(sender, instance, created, **kwargs):
#     """
#     Automatically create data sharing preferences when a connection is created
#     """
#     if created:
#         DataSharingPreference.objects.create(connection=instance)


# @receiver(post_save)
# def log_model_creation(sender, instance, created, **kwargs):
#     """
#     Automatically log model creation in audit log
#     """
#     # Skip logging for AuditLog itself to avoid recursion
#     if sender == AuditLog:
#         return
    
#     # Skip for certain model types if needed
#     excluded_models = (ConnectionActivity,)
#     if isinstance(instance, excluded_models):
#         return
    
#     if created:
#         # Try to get the user from the instance if available
#         user = None
#         if hasattr(instance, 'created_by') and instance.created_by:
#             user = instance.created_by
        
#         AuditLog.objects.create(
#             user=user,
#             action='create',
#             model=sender.__name__,
#             object_id=str(instance.pk),
#             details={'created': True}
#         )