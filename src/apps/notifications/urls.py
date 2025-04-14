from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    NotificationViewSet,
    NotificationPreferenceViewSet
)

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'preferences', NotificationPreferenceViewSet, basename='notification-preference')

app_name = 'notifications'

urlpatterns = [
    # Include the router URLs
    path('', include(router.urls)),
] 