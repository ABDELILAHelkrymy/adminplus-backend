from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AccountantClientRelationshipViewSet, UserViewSet,
    RoleViewSet, LoginView, CustomTokenRefreshView
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'relationships', AccountantClientRelationshipViewSet, basename='relationship')
router.register(r'roles', RoleViewSet, basename='role')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
]
