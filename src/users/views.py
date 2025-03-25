# views.py
from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Q
from .models import User, Role
from .serializers import (
    RoleSerializer
)
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from .serializers import LoginSerializer, TokenSerializer, TokenRefreshSerializer, UserSerializer, AdminRegistrationSerializer, ExternalAccountantRegistrationSerializer, AccountSettingsSerializer
from django.contrib.auth import login
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny


from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

@swagger_auto_schema(tags=['Roles'])
class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]

@swagger_auto_schema(tags=['Authentication'])
class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = TokenRefreshSerializer
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        refresh = RefreshToken(serializer.validated_data['refresh'])
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        })

@swagger_auto_schema(tags=['Authentication'])
class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    @swagger_auto_schema(
        request_body=LoginSerializer,
        responses={
            200: TokenSerializer,
            400: openapi.Response('Invalid credentials.', TokenSerializer),
        }
    )

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'status': 'success',
                'message': 'Successfully logged in.',
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'roles': [role.name for role in user.get_roles()],
                }
            }, status=status.HTTP_200_OK)
        
        return Response({
            'status': 'error',
            'message': 'Invalid credentials.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)
    

@swagger_auto_schema(tags=['Authentication'])
class AdminRegistrationView(APIView):
    permission_classes = [AllowAny]
    serializer_class = AdminRegistrationSerializer

    @swagger_auto_schema(
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
            400: openapi.Response('Invalid data provided.', TokenSerializer),
        }
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            # Create user, business account, and settings
            created_data = serializer.create(serializer.validated_data)
            user = created_data['user']
            business_account = created_data['business_account']
            settings = created_data['settings']

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                'status': 'success',
                'message': 'Admin user and business account created successfully.',
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'roles': [role.name for role in user.get_roles()],
                },
                'business_account': {
                    'id': str(business_account.id),
                    'business_name': business_account.business_name,
                    'tax_number': business_account.tax_number,
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


@swagger_auto_schema(tags=['Authentication'])
class ExternalAccountantRegistrationView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ExternalAccountantRegistrationSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            created_data = serializer.create(serializer.validated_data)
            user = created_data['user']
            external_accountant = created_data['external_accountant']

            refresh = RefreshToken.for_user(user)

            return Response({
                'status': 'success',
                'message': 'External accountant account created successfully.',
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'roles': [role.name for role in user.get_roles()],
                },
                'external_accountant': {
                    'id': str(external_accountant.id),
                    'accountant_name': external_accountant.accountant_name,
                    'company_name': external_accountant.company_name,
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'status': 'error',
            'message': 'Invalid data provided.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)
    
@swagger_auto_schema(tags=['Account Settings'])
class AccountSettingsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AccountSettingsSerializer

    @swagger_auto_schema(
        responses={
            200: AccountSettingsSerializer,
            400: openapi.Response('Invalid data provided.', AccountSettingsSerializer),
        }
    )

    def list(self, request):
        serializer = self.serializer_class(request.user)
        return Response(serializer.data)

    def update(self, request, pk=None):
        serializer = self.serializer_class(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)