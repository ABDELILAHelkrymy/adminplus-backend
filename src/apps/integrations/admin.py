from django.contrib import admin
from .models import Integration, IntegrationEvent


class IntegrationAdmin(admin.ModelAdmin):
    list_display = ('name', 'business_account', 'integration_type', 'is_active', 'last_sync')
    list_filter = ('integration_type', 'is_active')
    search_fields = ('name', 'business_account__business_name')
    readonly_fields = ('last_sync', 'created_at', 'updated_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('business_account')


class IntegrationEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'integration', 'timestamp', 'processed')
    list_filter = ('event_type', 'processed', 'timestamp')
    search_fields = ('event_type', 'integration__name')
    readonly_fields = ('timestamp', 'created_at', 'updated_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('integration', 'integration__business_account')


# Register models
admin.site.register(Integration, IntegrationAdmin)
admin.site.register(IntegrationEvent, IntegrationEventAdmin)
