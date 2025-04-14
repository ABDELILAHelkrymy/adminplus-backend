from django.contrib import admin
from .models import BusinessAccount, AccountSettings


class BusinessAccountAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'primary_user', 'tax_number', 'phone_number', 'created_at')
    search_fields = ('business_name', 'tax_number', 'primary_user__email')
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        # Get the default queryset
        qs = super().get_queryset(request)
        # Include related users to avoid N+1 queries
        return qs.select_related('primary_user')


class AccountSettingsAdmin(admin.ModelAdmin):
    list_display = ('business_account', 'currency', 'language', 'notification_emails', 'two_factor_auth')
    list_filter = ('currency', 'language', 'notification_emails', 'two_factor_auth')
    search_fields = ('business_account__business_name',)
    
    def get_queryset(self, request):
        # Get the default queryset
        qs = super().get_queryset(request)
        # Include related business accounts to avoid N+1 queries
        return qs.select_related('business_account')


# Register models
admin.site.register(BusinessAccount, BusinessAccountAdmin)
admin.site.register(AccountSettings, AccountSettingsAdmin)
