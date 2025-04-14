from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role, Permission, UserRole, PhoneOTP


class CustomUserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active', 'is_verified')
    list_filter = ('is_staff', 'is_active', 'is_verified')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone_number', 'address', 'company_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified',
                                       'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )
    readonly_fields = ('created_at', 'updated_at')


class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)


class PermissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'resource', 'action')
    search_fields = ('name', 'resource', 'action')
    list_filter = ('resource',)


class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'system_role', 'assigned_date')
    list_filter = ('system_role',)
    search_fields = ('user__email', 'role__name')


class PhoneOTPAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'is_verified', 'expires_at')
    list_filter = ('is_verified',)
    search_fields = ('user__email', 'phone_number')
    readonly_fields = ('otp', 'expires_at')


# Register models
admin.site.register(User, CustomUserAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(Permission, PermissionAdmin)
admin.site.register(UserRole, UserRoleAdmin)
admin.site.register(PhoneOTP, PhoneOTPAdmin) 