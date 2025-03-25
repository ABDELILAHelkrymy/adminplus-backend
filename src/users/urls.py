from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RoleViewSet, CustomTokenRefreshView, LoginView, AdminRegistrationView, ExternalAccountantRegistrationView, AccountSettingsViewSet, InternalUserViewSet
)

router = DefaultRouter()
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'account-settings', AccountSettingsViewSet, basename='account-settings')
router.register(r'Users', InternalUserViewSet, basename='internal-user')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('register/client', AdminRegistrationView.as_view(), name='register'),
    path('register/accountant/', ExternalAccountantRegistrationView.as_view(), name='register_accountant'),
]
