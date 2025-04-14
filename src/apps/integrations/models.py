from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel
from apps.accounts.models import BusinessAccount


class Integration(BaseModel):
    """Model for third-party service integrations"""
    business_account = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name='integrations')
    
    name = models.CharField(max_length=100)
    integration_type = models.CharField(max_length=50)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    auth_data = models.JSONField(blank=True, null=True)
    settings = models.JSONField(blank=True, null=True)
    
    last_sync = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} integration for {self.business_account.business_name}"
    
    def update_sync_status(self):
        """Update the last sync time"""
        self.last_sync = timezone.now()
        self.save(update_fields=['last_sync'])


class IntegrationEvent(BaseModel):
    """Model for integration events and webhooks"""
    integration = models.ForeignKey(Integration, on_delete=models.CASCADE, related_name='events')
    
    event_type = models.CharField(max_length=100)
    event_data = models.JSONField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
    processed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.event_type} event for {self.integration.name}"
    
    def mark_as_processed(self):
        """Mark the event as processed"""
        self.processed = True
        self.save(update_fields=['processed'])
