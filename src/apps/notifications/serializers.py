from rest_framework import serializers
from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 'priority',
            'read', 'read_at', 'created_at'
        ]
        read_only_fields = ['id', 'notification_type', 'title', 'message', 'priority', 'created_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            # Email notifications
            'email_account', 'email_invitation', 'email_connection',
            'email_transaction', 'email_security', 'email_system',
            
            # In-app notifications
            'app_account', 'app_invitation', 'app_connection',
            'app_transaction', 'app_security', 'app_system',
        ] 