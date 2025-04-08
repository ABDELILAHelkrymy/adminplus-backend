from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RoleViewSet, CustomTokenRefreshView, LoginView, AdminRegistrationView, ExternalAccountantRegistrationView, AccountSettingsViewSet, InternalUserViewSet,
    AccountantInvitationViewSet, ClientAccountantConnectionViewSet, PasswordResetRequestView, PasswordResetConfirmView, PasswordChangeView,
    EmailVerificationRequestView, EmailVerificationConfirmView, OTPRequestView, OTPVerifyView
)

router = DefaultRouter()
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'account-settings', AccountSettingsViewSet, basename='account-settings')
router.register(r'Users', InternalUserViewSet, basename='internal-user')
router.register(r'accountant-invitations', AccountantInvitationViewSet, basename='accountant-invitation')
router.register(r'connections', ClientAccountantConnectionViewSet, basename='connection')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('register/client/', AdminRegistrationView.as_view(), name='register'),
    path('register/accountant/', ExternalAccountantRegistrationView.as_view(), name='register_accountant'),
    path('password/reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password/change/', PasswordChangeView.as_view(), name='password_change'),
    path('email/verify/', EmailVerificationRequestView.as_view(), name='email_verification_request'),
    path('email/verify/<str:uidb64>/<str:token>/', EmailVerificationConfirmView.as_view(), name='email_verification_confirm'),
    path('phone/verify/request/', OTPRequestView.as_view(), name='phone_verification_request'),
    path('phone/verify/confirm/', OTPVerifyView.as_view(), name='phone_verification_confirm'),
]
