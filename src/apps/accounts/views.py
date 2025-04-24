from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
import logging

from .models import BusinessAccount, AccountSettings
from .serializers import (
    AccountSettingsSerializer,
    BusinessAccountMinimalSerializer,
    AdminRegistrationSerializer
)
from apps.users.permissions import IsBusinessOwner
from apps.users.models import User, Role, SystemRole, UserRole
from apps.users.serializers import UserSerializer
from apps.users.utils import send_verification_email

# Set up logger
email_logger = logging.getLogger('apps.email')

@swagger_auto_schema(tags=['Auth - Registration'])
class AdminRegistrationView(APIView):
    permission_classes = [AllowAny]
    serializer_class = AdminRegistrationSerializer

    @swagger_auto_schema(
        operation_id="admin_registration",
        request_body=AdminRegistrationSerializer,
        responses={
            201: openapi.Response(
                'Admin user and business account created successfully.',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'tokens': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'refresh': openapi.Schema(type=openapi.TYPE_STRING),
                                'access': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        ),
                        'user': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'business_account': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'settings': openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
            400: openapi.Response('Invalid data provided.'),
        }
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            # Create user, business account, and settings
            result = serializer.save()
            user = result['user']
            business_account = result['business_account']
            settings = result['settings']
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Send verification email without terminal logs
            send_verification_email(user)
            
            # Get user roles
            user_roles = user.user_roles.all()
            system_roles = [
                {
                    "name": role.system_role,
                    "displayName": role.get_system_role_display() if hasattr(role, 'get_system_role_display') else role.system_role.capitalize()
                } 
                for role in user_roles
            ]
            
            return Response({
                'status': 'success',
                'message': 'Admin user and business account created successfully. Please verify your email.',
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_active': user.is_active,
                    'roles': [role.system_role for role in user_roles],
                    'system_roles': system_roles,
                    'created_at': user.created_at.isoformat(),
                    'is_verified': user.is_verified
                },
                'business_account': {
                    'id': str(business_account.id),
                    'business_name': business_account.business_name,
                    'tax_number': business_account.tax_number,
                    'business_address': business_account.business_address,
                },
                'settings': {
                    'currency': settings.currency,
                    'language': settings.language,
                    'notification_emails': settings.notification_emails,
                    'two_factor_auth': settings.two_factor_auth,
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'status': 'error',
            'message': 'Invalid data provided.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)


@swagger_auto_schema(tags=['Accounts - Settings'])
class AccountSettingsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AccountSettingsSerializer

    @swagger_auto_schema(
        operation_id="account_settings_list",
        responses={
            200: AccountSettingsSerializer,
            400: openapi.Response('Invalid data provided.', AccountSettingsSerializer),
        }
    )
    def list(self, request):
        try:
            business_account = BusinessAccount.objects.get(primary_user=request.user)
            settings = AccountSettings.objects.get(business_account=business_account)
            serializer = self.serializer_class(settings)
            return Response(serializer.data)
        except (BusinessAccount.DoesNotExist, AccountSettings.DoesNotExist):
            return Response({'status': 'error', 'message': 'Account settings not found.'}, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, pk=None):
        try:
            business_account = BusinessAccount.objects.get(primary_user=request.user)
            settings = AccountSettings.objects.get(business_account=business_account)
            serializer = self.serializer_class(settings, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except (BusinessAccount.DoesNotExist, AccountSettings.DoesNotExist):
            return Response({'status': 'error', 'message': 'Account settings not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)


@swagger_auto_schema(tags=['Accounts - Business'])
class BusinessAccountInfoView(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_id="business_account_info",
        operation_summary="Get business account info",
        responses={
            200: openapi.Response(
                description="Business account information",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'business_account': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'settings': openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
            403: "Permission denied",
            404: "Business account not found"
        }
    )
    def get(self, request):
        # Check if user has admin role
        user_roles = request.user.user_roles.all().values_list('system_role', flat=True)
        
        try:
            # First try to get business account where user is primary user
            if 'admin' in user_roles:
                business_account = BusinessAccount.objects.get(primary_user=request.user)
            else:
                # For non-admin users, check if they belong to a business account
                business_account = request.user.business_accounts.first()
                
                if not business_account:
                    return Response({
                        'status': 'error',
                        'message': 'You do not have access to any business account.'
                    }, status=status.HTTP_403_FORBIDDEN)
            
            settings = AccountSettings.objects.get(business_account=business_account)
            
            return Response({
                'status': 'success',
                'business_account': {
                    'id': str(business_account.id),
                    'business_name': business_account.business_name,
                    'tax_number': business_account.tax_number,
                    'business_address': business_account.business_address,
                    'phone_number': business_account.phone_number,
                    'website': business_account.website,
                },
                'settings': {
                    'currency': settings.currency,
                    'language': settings.language,
                    'notification_emails': settings.notification_emails,
                    'two_factor_auth': settings.two_factor_auth,
                }
            })
        except (BusinessAccount.DoesNotExist, AccountSettings.DoesNotExist):
            return Response({
                'status': 'error',
                'message': 'Business account not found.'
            }, status=status.HTTP_404_NOT_FOUND)
