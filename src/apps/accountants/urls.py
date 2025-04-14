from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ExternalAccountantRegistrationView,
    AccountantInvitationViewSet
)

router = DefaultRouter()
router.register(r'invitations', AccountantInvitationViewSet, basename='accountant-invitation')

app_name = 'accountants'

urlpatterns = [
    # Authentication endpoints
    path('register/external-accountant/', ExternalAccountantRegistrationView.as_view(), name='register-external-accountant'),
    
    # Invitation management endpoints handled by the router
    path('', include(router.urls)),
] 