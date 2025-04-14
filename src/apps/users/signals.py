"""
Signal handlers for the users app.
These handle automatic actions when user models are created or modified.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from apps.users.models import User, Role, SystemRole, UserRole

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal handler to perform actions after a user is created.
    """
    if created:
        # Add any initialization tasks here when a user is created
        pass

@receiver(pre_save, sender=User)
def update_user_timestamp(sender, instance, **kwargs):
    """
    Update the updated_at timestamp when a user is updated.
    """
    if instance.pk:  # If this is an update, not a new creation
        instance.updated_at = timezone.now() 