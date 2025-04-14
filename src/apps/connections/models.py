from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel
from apps.users.models import User
from apps.accounts.models import BusinessAccount
from apps.accountants.models import ExternalAccountantAccount


# Access level choices
class ConnectionAccessLevel(models.TextChoices):
    FULL_ACCESS = 'full_access', _('Full Access')
    READ_ONLY = 'read_only', _('Read Only')
    REPORTS_ONLY = 'reports_only', _('Reports Only')
    CUSTOM = 'custom', _('Custom')


# Client-accountant connection model
class ClientAccountantConnection(BaseModel):
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
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_connections')
    
    class Meta:
        unique_together = ('client', 'accountant')
    
    def __str__(self):
        return f"Connection: {self.client.business_name} - {self.accountant.accountant_name}"
    
    def manage_connection_status(self, status=None):
        """
        Update the connection status
        :param status: Boolean active status
        """
        if status is not None:
            self.is_active = status
            self.save()
    
    def update_access_level(self, level):
        """
        Update the access level
        :param level: ConnectionAccessLevel value
        """
        self.access_level = level
        self.save()
    
    def record_access(self):
        """Record when the connection was last accessed"""
        self.last_access = timezone.now()
        self.save(update_fields=['last_access'])


# Connection activity model
class ConnectionActivity(BaseModel):
    connection = models.ForeignKey(ClientAccountantConnection, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='connection_activities')
    
    timestamp = models.DateTimeField(default=timezone.now)
    action_type = models.CharField(max_length=50)
    description = models.TextField()
    
    def __str__(self):
        return f"{self.action_type} by {self.user.email if self.user else 'Unknown'}"
    
    @classmethod
    def log_activity(cls, connection, user, action_type, description):
        """
        Log an activity for a connection
        :param connection: ClientAccountantConnection
        :param user: User performing the action
        :param action_type: Type of action
        :param description: Description of the action
        :return: ConnectionActivity instance
        """
        return cls.objects.create(
            connection=connection,
            user=user,
            action_type=action_type,
            description=description
        )


# Data sharing preferences model
class DataSharingPreference(BaseModel):
    connection = models.OneToOneField(ClientAccountantConnection, on_delete=models.CASCADE, related_name='data_sharing')
    
    share_invoices = models.BooleanField(default=False)
    share_expenses = models.BooleanField(default=False)
    share_bank_data = models.BooleanField(default=False)
    share_tax_documents = models.BooleanField(default=False)
    share_reports = models.BooleanField(default=False)
    
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='updated_sharing_preferences')
    
    def __str__(self):
        return f"Sharing preferences for {self.connection}"
    
    def update_preferences(self, **kwargs):
        """
        Update data sharing preferences
        :param kwargs: Preferences to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key) and key.startswith('share_'):
                setattr(self, key, value)
        self.save()
