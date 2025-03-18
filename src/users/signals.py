from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.apps import apps
from django.core.serializers.json import DjangoJSONEncoder
import json


class CustomJSONEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)

@receiver(post_save)
def log_save(sender, instance, created, **kwargs):
    AuditLog = apps.get_model('users', 'AuditLog')
    action = 'create' if created else 'update'

    # Serialize the instance using the custom encoder
    details = json.loads(json.dumps(instance.__dict__, cls=CustomJSONEncoder))

    AuditLog.objects.create(
        user=instance.last_modified_by if hasattr(instance, 'last_modified_by') else None,
        action=action,
        model=sender.__name__,
        object_id=instance.id,
        details=details
    )

@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    AuditLog = apps.get_model('users', 'AuditLog')

    # Serialize the instance using the custom encoder
    details = json.loads(json.dumps(instance.__dict__, cls=CustomJSONEncoder))

    AuditLog.objects.create(
        user=instance.last_modified_by if hasattr(instance, 'last_modified_by') else None,
        action='delete',
        model=sender.__name__,
        object_id=instance.id,
        details=details
    )