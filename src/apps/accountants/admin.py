from django.contrib import admin
from .models import AccountantInvitation, ExternalAccountantAccount


class AccountantInvitationAdmin(admin.ModelAdmin):
    list_display = ('accountant_email', 'sender', 'status', 'expiry_date', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('accountant_email', 'sender__business_name')
    readonly_fields = ('sent_date', 'created_at', 'updated_at')
    
    def get_queryset(self, request):
        # Get the default queryset
        qs = super().get_queryset(request)
        # Include related business accounts to avoid N+1 queries
        return qs.select_related('sender', 'recipient', 'created_by')


class ExternalAccountantAccountAdmin(admin.ModelAdmin):
    list_display = ('accountant_name', 'user', 'company_name', 'tax_number', 'contact_phone')
    search_fields = ('accountant_name', 'company_name', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')


# Register models
admin.site.register(AccountantInvitation, AccountantInvitationAdmin)
admin.site.register(ExternalAccountantAccount, ExternalAccountantAccountAdmin)
