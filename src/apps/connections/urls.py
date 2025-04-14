from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ClientAccountantConnectionViewSet
)

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'client-accountant', ClientAccountantConnectionViewSet, basename='client-accountant-connection')

app_name = 'connections'

urlpatterns = [
    # Include the router URLs
    path('', include(router.urls)),
] 