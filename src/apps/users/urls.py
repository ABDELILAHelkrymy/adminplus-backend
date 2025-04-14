from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    RoleViewSet,
    SystemRoleListView,
    LoginView,
    CustomTokenRefreshView,
    InternalUserViewSet,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    PasswordChangeView,
    EmailVerificationRequestView,
    EmailVerificationConfirmView,
    OTPRequestView,
    OTPVerifyView
)

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'roles', RoleViewSet)
router.register(r'internal-users', InternalUserViewSet, basename='internal-users')
router.register(r'email/verification', EmailVerificationRequestView, basename='email-verification')

# API URLs
urlpatterns = [
    # Include the router URLs
    path('', include(router.urls)),
    
    # Authentication endpoints
    path('login/', LoginView.as_view({'post': 'create'}), name='login'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    
    # System roles
    path('system-roles/', SystemRoleListView.as_view(), name='system-roles'),
    
    # Password management
    path('password/reset/request/', PasswordResetRequestView.as_view({'post': 'create'}), name='password-reset-request'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view({'post': 'create'}), name='password-reset-confirm'),
    path('password/change/', PasswordChangeView.as_view(), name='password-change'),
    
    # Email verification - direct views
    path('email/verify/<uidb64>/<token>/', EmailVerificationConfirmView.as_view(), name='email-verify-confirm'),
    path('email/verify/test/', EmailVerificationRequestView.as_view({'get': 'test_email_config'}), name='email-verify-test'),
    
    # Phone verification
    path('phone/verify/request/', OTPRequestView.as_view(), name='phone-verify-request'),
    path('phone/verify/confirm/', OTPVerifyView.as_view(), name='phone-verify-confirm'),
] 