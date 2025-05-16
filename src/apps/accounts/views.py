from django.shortcuts import render
from rest_framework import viewsets, status, permissions
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
from django.core.files.storage import default_storage
from django.http import HttpResponse
import mimetypes
import os
import boto3
from django.conf import settings

from .models import BusinessAccount, AccountSettings
from .serializers import (
    AccountSettingsSerializer,
    BusinessAccountSerializer,
    AdminRegistrationSerializer
)
from apps.users.permissions import IsBusinessOwner
from apps.users.models import User, Role, SystemRole, UserRole
from apps.users.serializers import UserSerializer
from apps.users.utils import send_verification_email
from core.swagger_utils import get_serializer_schema

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
class AccountSettingsViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter settings to only show those related to the user's business account
        """
        user = self.request.user
        if user.user_roles.filter(system_role='admin').exists():
            # Admin users can see their own business settings
            return AccountSettings.objects.filter(business_account__primary_user=user)
        else:
            # Other users can see settings of business accounts they belong to
            return AccountSettings.objects.filter(business_account__internal_users=user)

    def get_object(self):
        """
        Get the settings object for the current user's business account
        """
        user = self.request.user
        try:
            if user.user_roles.filter(system_role='admin').exists():
                # Admin users get their own business settings
                business_account = BusinessAccount.objects.get(primary_user=user)
            else:
                # Other users get settings of their first business account
                business_account = user.business_accounts.first()
                if not business_account:
                    raise AccountSettings.DoesNotExist

            return AccountSettings.objects.get(business_account=business_account)
        except (BusinessAccount.DoesNotExist, AccountSettings.DoesNotExist):
            return None

    def list(self, request, *args, **kwargs):
        """
        List settings for the user's business account
        """
        settings = self.get_object()
        if not settings:
            return Response({
                'status': 'error',
                'message': 'No settings found for your business account.'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(settings)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve settings for the user's business account
        """
        # Handle 'me' as a special case for backward compatibility
        if kwargs.get('pk') == 'me':
            settings = self.get_object()
        else:
            settings = self.get_object_or_404(self.get_queryset(), pk=kwargs.get('pk'))
            
        if not settings:
            return Response({
                'status': 'error',
                'message': 'No settings found for your business account.'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(settings)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """
        Update settings for the user's business account
        """
        # Handle 'me' as a special case for backward compatibility
        if kwargs.get('pk') == 'me':
            settings = self.get_object()
        else:
            settings = self.get_object_or_404(self.get_queryset(), pk=kwargs.get('pk'))
            
        if not settings:
            return Response({
                'status': 'error',
                'message': 'No settings found for your business account.'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def upload_logo(self, request):
        """
        Upload a logo for the account settings
        """
        settings = self.get_object()
        if not settings:
            return Response({
                'status': 'error',
                'message': 'No settings found for your business account.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        file = request.FILES['file']
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif']
        if file.content_type not in allowed_types:
            return Response(
                {'error': 'Invalid file type. Only JPEG, PNG and GIF are allowed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            url = settings.upload_logo(file)
            return Response({'url': url}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['delete'])
    def delete_logo(self, request):
        """
        Delete the account settings logo
        """
        settings = self.get_object()
        if not settings:
            return Response({
                'status': 'error',
                'message': 'No settings found for your business account.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if settings.delete_logo():
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'error': 'Failed to delete logo'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    @action(detail=False, methods=['get'])
    def download_logo(self, request):
        """
        Download the account settings logo
        """
        settings = self.get_object()
        if not settings:
            return Response({
                'status': 'error',
                'message': 'No settings found for your business account.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if not settings.logo:
            return Response(
                {'error': 'No logo found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
            
        try:
            # Extract the path from the URL
            path = settings.logo.split('/')[-1]
            file_path = f"settings_logos/{settings.business_account.id}/{path}"
            
            if not default_storage.exists(file_path):
                return Response(
                    {'error': 'File not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
                
            file = default_storage.open(file_path)
            content_type, _ = mimetypes.guess_type(file_path)
            
            response = HttpResponse(file.read(), content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def proxy_logo(self, request):
        """Proxy endpoint to serve S3 logo images"""
        try:
            # Get the S3 key from the request
            s3_key = request.query_params.get('key')
            if not s3_key:
                return Response({'error': 'No S3 key provided'}, status=400)

            # Initialize S3 client
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )

            # Get the object from S3
            response = s3_client.get_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=s3_key
            )

            # Get the content type
            content_type = response['ContentType']

            # Create the response
            http_response = HttpResponse(
                response['Body'].read(),
                content_type=content_type
            )

            # Add cache headers
            http_response['Cache-Control'] = 'public, max-age=3600'
            http_response['Access-Control-Allow-Origin'] = '*'

            return http_response

        except Exception as e:
            return Response({'error': str(e)}, status=500)


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
                        'business_account': get_serializer_schema(BusinessAccountSerializer),
                        'settings': get_serializer_schema(AccountSettingsSerializer),
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
                        
            # Use serializers to format the response data
            business_serializer = BusinessAccountSerializer(business_account)
            
            return Response({
                'status': 'success',
                'business_account': business_serializer.data,
            })
        except (BusinessAccount.DoesNotExist, AccountSettings.DoesNotExist):
            return Response({
                'status': 'error',
                'message': 'Business account not found.'
            }, status=status.HTTP_404_NOT_FOUND)


class BusinessAccountViewSet(viewsets.ModelViewSet):
    queryset = BusinessAccount.objects.all()
    serializer_class = BusinessAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['post'])
    def upload_logo(self, request, pk=None):
        """
        Upload a logo for the business account
        """
        business = self.get_object()
        
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        file = request.FILES['file']
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif']
        if file.content_type not in allowed_types:
            return Response(
                {'error': 'Invalid file type. Only JPEG, PNG and GIF are allowed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            url = business.upload_logo(file)
            return Response({'url': url}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['delete'])
    def delete_logo(self, request, pk=None):
        """
        Delete the business account logo
        """
        business = self.get_object()
        
        if business.delete_logo():
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'error': 'Failed to delete logo'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    @action(detail=True, methods=['get'])
    def download_logo(self, request, pk=None):
        """
        Download the business account logo
        """
        business = self.get_object()
        
        if not business.logo:
            return Response(
                {'error': 'No logo found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
            
        try:
            # Extract the path from the URL
            path = business.logo.split('/')[-1]
            file_path = f"business_logos/{business.id}/{path}"
            
            if not default_storage.exists(file_path):
                return Response(
                    {'error': 'File not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
                
            file = default_storage.open(file_path)
            content_type, _ = mimetypes.guess_type(file_path)
            
            response = HttpResponse(file.read(), content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
