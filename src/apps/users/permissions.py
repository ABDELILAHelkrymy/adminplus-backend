from rest_framework import permissions
from apps.accounts.models import BusinessAccount


class IsBusinessOwner(permissions.BasePermission):
    """
    Permission to only allow owners of a business to perform certain actions.
    """
    
    def has_permission(self, request, view):
        """
        Check if the user is the owner of a business account.
        """
        try:
            # Check if the user is the primary user of any business account
            return BusinessAccount.objects.filter(primary_user=request.user).exists()
        except:
            return False 