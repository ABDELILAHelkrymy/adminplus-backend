from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    IntegrationViewSet,
    IntegrationEventViewSet
)

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'integrations', IntegrationViewSet, basename='integration')
router.register(r'events', IntegrationEventViewSet, basename='integration-event')

app_name = 'integrations'

urlpatterns = [
    # Include the router URLs
    path('', include(router.urls)),
] 