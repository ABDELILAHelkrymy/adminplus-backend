from django.contrib import admin
from .models import User, AccountantClientRelationship, Role, UserProfile
# Register your models here.

admin.site.register(User)
admin.site.register(AccountantClientRelationship)
admin.site.register(Role)
admin.site.register(UserProfile)