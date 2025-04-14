from rest_framework import serializers
from .models import ClientAccountantConnection, DataSharingPreference, ConnectionAccessLevel
from apps.accounts.serializers import BusinessAccountMinimalSerializer


class DataSharingPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSharingPreference
        fields = [
            'share_invoices', 'share_expenses', 'share_bank_data',
            'share_tax_documents', 'share_reports'
        ]


class ClientAccountantConnectionSerializer(serializers.ModelSerializer):
    client_details = BusinessAccountMinimalSerializer(source='client', read_only=True)
    accountant_details = serializers.SerializerMethodField()
    data_sharing = DataSharingPreferenceSerializer(read_only=True)
    
    class Meta:
        model = ClientAccountantConnection
        fields = [
            'id', 'client_details', 'accountant_details', 'connection_date',
            'is_active', 'last_access', 'access_level', 'notes', 'data_sharing'
        ]
        read_only_fields = ['connection_date', 'last_access']

    def get_accountant_details(self, obj):
        return {
            'id': str(obj.accountant.id),
            'accountant_name': obj.accountant.accountant_name,
            'company_name': obj.accountant.company_name,
            'contact_phone': obj.accountant.contact_phone
        } 