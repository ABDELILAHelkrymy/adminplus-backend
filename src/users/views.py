# views.py
from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Q
from .models import AccountantInvitation, User, Role, ExternalAccountantAccount, InvitationStatus
from .serializers import (
    AccountantInvitationSerializer,
    RoleSerializer
)
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from .serializers import LoginSerializer, TokenSerializer, TokenRefreshSerializer, UserSerializer, AdminRegistrationSerializer, ExternalAccountantRegistrationSerializer, AccountSettingsSerializer, InternalUserCreateSerializer
from django.contrib.auth import login
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from .permissions import IsBusinessOwner  # Add this import at the top

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

@swagger_auto_schema(tags=['Users'])
class InternalUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, IsBusinessOwner]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InternalUserCreateSerializer
        return UserSerializer

    def get_queryset(self):
        # Only return users that belong to the current user's business
        if hasattr(self.request.user, 'owned_business'):
            return self.request.user.owned_business.internal_users.all()
        return User.objects.none()

    @swagger_auto_schema(
        tags=['Users'],
        operation_summary="Create internal user",
        operation_description="Create a new internal user (Internal Accountant, Employee, or Viewer)",
        request_body=InternalUserCreateSerializer,
        responses={
            201: openapi.Response(
                'User created successfully',
                UserSerializer
            ),
            400: 'Invalid data',
            403: 'Permission denied'
        }
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        response_serializer = UserSerializer(user)
        return Response(
            {
                'status': 'success',
                'message': 'User created successfully',
                'user': response_serializer.data
            }, 
            status=status.HTTP_201_CREATED
        )

    @swagger_auto_schema(
        tags=['Users'],
        operation_summary="List internal users",
        operation_description="List all internal users for the current business account",
        responses={
            200: UserSerializer(many=True),
            403: 'Permission denied'
        }
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = UserSerializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        tags=['Users'],
        operation_summary="Delete internal user",
        operation_description="Remove an internal user from the business account",
        responses={
            204: 'User deleted successfully',
            403: 'Permission denied',
            404: 'User not found'
        }
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Remove user from business account
        if hasattr(request.user, 'owned_business'):
            request.user.owned_business.internal_users.remove(instance)
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

@swagger_auto_schema(tags=['Invitations'])
class AccountantInvitationViewSet(viewsets.ModelViewSet):
    serializer_class = AccountantInvitationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'owned_business'):
            # Business owners see invitations they sent
            return AccountantInvitation.objects.filter(sender=user.owned_business)
        elif hasattr(user, 'accountant_account'):
            # Accountants see invitations sent to them
            return AccountantInvitation.objects.filter(
                accountant_email=user.email,
                status=InvitationStatus.PENDING
            )
        return AccountantInvitation.objects.none()

    @swagger_auto_schema(
        operation_summary="Send invitation to accountant",
        request_body=AccountantInvitationSerializer,
        responses={
            201: AccountantInvitationSerializer,
            400: 'Invalid data',
            403: 'Permission denied'
        }
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation = serializer.save()
        
        # Here you might want to send an email to the accountant
        # send_invitation_email(invitation)
        
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    @swagger_auto_schema(
        operation_summary="Accept invitation",
        responses={
            200: AccountantInvitationSerializer,
            400: "Invalid request or expired invitation",
            403: "Permission denied",
            404: "Invitation not found"
        }
    )
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        invitation = self.get_object()
        try:
            accountant_account = request.user.accountant_account
            connection = invitation.accept_invitation(accountant_account)
            
            serializer = self.get_serializer(invitation)
            return Response({
                'status': 'success',
                'message': 'Invitation accepted successfully',
                'invitation': serializer.data,
                'connection': {
                    'id': str(connection.id),
                    'client': connection.client.business_name,
                    'access_level': connection.access_level,
                }
            })
        except (ExternalAccountantAccount.DoesNotExist, ValueError) as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Reject invitation",
        responses={
            200: "Invitation rejected successfully",
            400: "Invalid request",
            403: "Permission denied",
            404: "Invitation not found"
        }
    )
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        invitation = self.get_object()
        try:
            invitation.reject_invitation()
            return Response({
                'status': 'success',
                'message': 'Invitation rejected successfully'
            })
        except ValueError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Cancel invitation",
        responses={
            200: "Invitation cancelled successfully",
            400: "Invalid request",
            403: "Permission denied",
            404: "Invitation not found"
        }
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        invitation = self.get_object()
        try:
            invitation.cancel_invitation(request.user)
            return Response({
                'status': 'success',
                'message': 'Invitation cancelled successfully'
            })
        except ValueError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Resend invitation",
        responses={
            200: "Invitation resent successfully",
            404: "Invitation not found",
            403: "Permission denied"
        }
    )
    @action(detail=True, methods=['post'])
    def resend(self, request, pk=None):
        invitation = self.get_object()
        if invitation.status == InvitationStatus.PENDING:
            invitation.expiry_date = timezone.now() + timezone.timedelta(days=7)
            invitation.sent_date = timezone.now()
            invitation.save()
            
            # Here you might want to resend the email
            # send_invitation_email(invitation)
            
            serializer = self.get_serializer(invitation)
            return Response(serializer.data)
        return Response({
            'status': 'error',
            'message': 'Only pending invitations can be resent'
        }, status=status.HTTP_400_BAD_REQUEST)