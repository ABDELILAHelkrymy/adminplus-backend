from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import AuditLog

# --------------------------
#  SIGNALS
# --------------------------


# add docstring to the function

@receiver(post_save)
def log_save(sender, instance, created, **kwargs):
    """
    Log the create, update, delete actions of the models
    """
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
    """
    Log the create, update, delete actions of the models
    """
    AuditLog.objects.create(
        user=instance.last_modified_by if hasattr(instance, 'last_modified_by') else None,
        action='delete',
        model=sender.__name__,
        object_id=instance.id,
        details=instance.__dict__
    )