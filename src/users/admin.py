from django.contrib import admin
from .models import User
from django.contrib.auth.admin import UserAdmin
# Register your models here.

class CustomUserAdmin(UserAdmin):
     # Fields to display in the admin list view
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active')
    
    # Fields to filter by in the admin
    list_filter = ('is_staff', 'is_active')
    
    # Fields to search by in the admin
    search_fields = ('email', 'first_name', 'last_name')
    
    # Fieldsets for the add/edit user page
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'created_at')}),
    )
    
    # Fieldsets for the add user page
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )
    
    # Order users by email in the admin
    ordering = ('email',)

    # Handle UUID fields in the admin
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'id':
            kwargs['form_class'] = forms.UUIDField  # Use UUIDField for the 'id' field
        return super().formfield_for_dbfield(db_field, **kwargs)

admin.site.register(User, CustomUserAdmin)