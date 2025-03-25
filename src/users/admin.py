from django.contrib import admin
from .models import User, Role, Permission, BusinessAccount, ExternalAccountantAccount, UserRole, AccountantInvitation, ClientAccountantConnection, AccountSettings, Integration
# Register your models here.

admin.site.register(User)
admin.site.register(Role)
admin.site.register(Permission)
admin.site.register(BusinessAccount)
admin.site.register(ExternalAccountantAccount)
admin.site.register(UserRole)
admin.site.register(AccountantInvitation)
admin.site.register(ClientAccountantConnection)
admin.site.register(AccountSettings)
admin.site.register(Integration)