from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel
from apps.users.models import User
from apps.accounts.models import BusinessAccount


class NotificationType(models.TextChoices):
    """Types of notifications"""
    ACCOUNT = 'account', _('Account')
    INVITATION = 'invitation', _('Invitation')
    CONNECTION = 'connection', _('Connection')
    TRANSACTION = 'transaction', _('Transaction')
    SECURITY = 'security', _('Security')
    SYSTEM = 'system', _('System')


class NotificationPriority(models.TextChoices):
    """Priority levels for notifications"""
    LOW = 'low', _('Low')
    MEDIUM = 'medium', _('Medium')
    HIGH = 'high', _('High')


class Notification(BaseModel):
    """Model for user notifications"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    business_account = models.ForeignKey(BusinessAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices)
    title = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=NotificationPriority.choices, default=NotificationPriority.MEDIUM)
    
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    related_object_id = models.UUIDField(null=True, blank=True)  # For linking to specific objects
    related_object_type = models.CharField(max_length=50, null=True, blank=True)  # Model name of related object
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.read = True
        self.read_at = timezone.now()
        self.save(update_fields=['read', 'read_at'])
    
    @classmethod
    def create_notification(cls, user, notification_type, title, message, **kwargs):
        """
        Create a notification
        :param user: User to notify
        :param notification_type: Type from NotificationType
        :param title: Notification title
        :param message: Notification message
        :param kwargs: Additional fields
        :return: Notification instance
        """
        return cls.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            **kwargs
        )


class NotificationPreference(BaseModel):
    """Model for user notification preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Email notifications
    email_account = models.BooleanField(default=True)
    email_invitation = models.BooleanField(default=True)
    email_connection = models.BooleanField(default=True)
    email_transaction = models.BooleanField(default=True)
    email_security = models.BooleanField(default=True)
    email_system = models.BooleanField(default=True)
    
    # In-app notifications
    app_account = models.BooleanField(default=True)
    app_invitation = models.BooleanField(default=True)
    app_connection = models.BooleanField(default=True)
    app_transaction = models.BooleanField(default=True)
    app_security = models.BooleanField(default=True)
    app_system = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Notification preferences for {self.user.email}"
    
    def update_preferences(self, **kwargs):
        """
        Update notification preferences
        :param kwargs: Preferences to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save()
