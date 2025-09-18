from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AdminRegistrationView,
    AccountSettingsViewSet,
    BusinessAccountInfoView,
    BusinessAccountViewSet
)

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'business-accounts', BusinessAccountViewSet, basename='business-account')
router.register(r'account-settings', AccountSettingsViewSet, basename='account-settings')

# API URLs
urlpatterns = [
    # Include the router URLs
    path('', include(router.urls)),
    
    # Registration
    path('register/admin/', AdminRegistrationView.as_view(), name='register-admin'),
    
    # Business Account Info
    path('business-info/', BusinessAccountInfoView.as_view(), name='business-info'),
] 