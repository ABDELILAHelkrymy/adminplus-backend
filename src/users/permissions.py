from rest_framework import permissions

class IsBusinessOwner(permissions.BasePermission):
    """
    Custom permission to only allow business owners to create/manage internal users.
    """
    def has_permission(self, request, view):
        return hasattr(request.user, 'owned_business')

    def has_object_permission(self, request, view, obj):
        if not hasattr(request.user, 'owned_business'):
            return False
        return obj in request.user.owned_business.internal_users.all()