from rest_framework import serializers
from .models import Integration, IntegrationEvent


class IntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Integration
        fields = [
            'id', 'name', 'integration_type', 'is_active',
            'settings', 'last_sync', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_sync']
        extra_kwargs = {
            'api_key': {'write_only': True},
            'auth_data': {'write_only': True}
        }


class IntegrationEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationEvent
        fields = [
            'id', 'integration', 'event_type',
            'event_data', 'timestamp', 'processed'
        ]
        read_only_fields = ['id', 'timestamp', 'processed'] 