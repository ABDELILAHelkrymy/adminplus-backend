from django.contrib import admin
from .models import Notification, NotificationPreference


class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'notification_type', 'priority', 'read', 'created_at', 'read_at')
    list_filter = ('notification_type', 'priority', 'read', 'created_at')
    search_fields = ('title', 'message', 'user__email')
    readonly_fields = ('read_at', 'created_at', 'updated_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'business_account')
    
    actions = ['mark_as_read']
    
    def mark_as_read(self, request, queryset):
        for notification in queryset:
            notification.mark_as_read()
        self.message_user(request, f"{queryset.count()} notifications marked as read.")
    mark_as_read.short_description = "Mark selected notifications as read"


class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_account', 'email_transaction', 'app_account', 'app_transaction')
    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Email Notifications', {
            'fields': ('email_account', 'email_invitation', 'email_connection', 
                      'email_transaction', 'email_security', 'email_system')
        }),
        ('In-App Notifications', {
            'fields': ('app_account', 'app_invitation', 'app_connection',
                      'app_transaction', 'app_security', 'app_system')
        }),
    )
    search_fields = ('user__email',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')


# Register models
admin.site.register(Notification, NotificationAdmin)
admin.site.register(NotificationPreference, NotificationPreferenceAdmin)
