from django.contrib import admin
from .models import ClientAccountantConnection, ConnectionActivity, DataSharingPreference


class ClientAccountantConnectionAdmin(admin.ModelAdmin):
    list_display = ('client', 'accountant', 'access_level', 'is_active', 'connection_date', 'last_access')
    list_filter = ('is_active', 'access_level', 'connection_date')
    search_fields = ('client__business_name', 'accountant__accountant_name', 'notes')
    readonly_fields = ('connection_date', 'last_access', 'created_at', 'updated_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('client', 'accountant', 'created_by')


class ConnectionActivityAdmin(admin.ModelAdmin):
    list_display = ('connection', 'user', 'action_type', 'timestamp')
    list_filter = ('action_type', 'timestamp')
    search_fields = ('connection__client__business_name', 'user__email', 'description')
    readonly_fields = ('timestamp', 'created_at', 'updated_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('connection', 'user')


class DataSharingPreferenceAdmin(admin.ModelAdmin):
    list_display = ('connection', 'share_invoices', 'share_expenses', 'share_bank_data', 
                   'share_tax_documents', 'share_reports')
    list_filter = ('share_invoices', 'share_expenses', 'share_bank_data', 
                  'share_tax_documents', 'share_reports')
    search_fields = ('connection__client__business_name',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('connection', 'connection__client', 'connection__accountant')


# Register models
admin.site.register(ClientAccountantConnection, ClientAccountantConnectionAdmin)
admin.site.register(ConnectionActivity, ConnectionActivityAdmin)
admin.site.register(DataSharingPreference, DataSharingPreferenceAdmin)
