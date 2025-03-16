from django.contrib import admin
from .models import User, Permission, RolePermission, AccountantClient
# Register your models here.

admin.site.register(User)
admin.site.register(Permission)
admin.site.register(RolePermission)
admin.site.register(AccountantClient)