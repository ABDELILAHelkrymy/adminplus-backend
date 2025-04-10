# views.py
from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Q
from .models import AccountantInvitation, User, Role, ExternalAccountantAccount, InvitationStatus, ClientAccountantConnection, ConnectionAccessLevel, ConnectionActivity, PhoneOTP, SystemRole, UserRole, AccountSettings
from .serializers import (
    AccountantInvitationSerializer,
    RoleSerializer,
    ClientAccountantConnectionSerializer,
    DataSharingPreferenceSerializer,
    EmailVerificationConfirmSerializer,
    EmailVerificationRequestSerializer,
    PasswordChangeSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer
)
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from .serializers import LoginSerializer, TokenSerializer, TokenRefreshSerializer, UserSerializer, AdminRegistrationSerializer, ExternalAccountantRegistrationSerializer, AccountSettingsSerializer, InternalUserCreateSerializer
from django.contrib.auth import login
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from .permissions import IsBusinessOwner  # Add this import at the top
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.conf import settings
from .utils import send_password_reset_email, send_verification_email, send_otp_via_sms

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from functools import wraps

def email_verification_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_verified:
            return Response({
                'status': 'error',
                'message': 'Email verification required to access this feature'
            }, status=status.HTTP_403_FORBIDDEN)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

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
                    'is_verified': user.is_verified,
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

            # Send verification email
            send_verification_email(user)

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                'status': 'success',
                'message': 'Admin user created successfully. Please check your email to verify your account.',
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_verified': user.is_verified,
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

            # Send verification email
            send_verification_email(user)

            refresh = RefreshToken.for_user(user)

            return Response({
                'status': 'success',
                'message': 'External accountant account created successfully. Please check your email to verify your account.',
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_verified': user.is_verified,
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
        # Extract accountant email from request data
        accountant_email = request.data.get('accountant_email')
        
        # Check if invitation already exists
        existing_invitation = None
        if hasattr(request.user, 'owned_business') and accountant_email:
            existing_invitation = AccountantInvitation.objects.filter(
                sender=request.user.owned_business,
                accountant_email=accountant_email,
                status=InvitationStatus.PENDING
            ).first()
        
        if existing_invitation:
            serializer = self.get_serializer(existing_invitation)
            return Response({
                'status': 'info',
                'message': 'An invitation has already been sent to this accountant',
                'invitation': serializer.data
            }, status=status.HTTP_200_OK)
        
        # If no existing invitation, create a new one
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation = serializer.save()
        
        # Here you might want to send an email to the accountant
        # send_invitation_email(invitation)
        
        return Response({
            'status': 'success',
            'message': 'Invitation sent successfully',
            'invitation': serializer.data
        }, status=status.HTTP_201_CREATED)

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

@swagger_auto_schema(tags=['Connections'])
class ClientAccountantConnectionViewSet(viewsets.ModelViewSet):
    serializer_class = ClientAccountantConnectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'owned_business'):
            # Business owners see their connections
            return ClientAccountantConnection.objects.filter(client=user.owned_business)
        elif hasattr(user, 'accountant_account'):
            # Accountants see connections where they are the accountant
            return ClientAccountantConnection.objects.filter(accountant=user.accountant_account)
        return ClientAccountantConnection.objects.none()

    @swagger_auto_schema(
        operation_summary="Update connection access level",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'access_level': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=[level[0] for level in ConnectionAccessLevel.choices]
                ),
            }
        ),
        responses={
            200: ClientAccountantConnectionSerializer,
            400: "Invalid access level",
            404: "Connection not found"
        }
    )
    @action(detail=True, methods=['patch'])
    def update_access(self, request, pk=None):
        connection = self.get_object()
        access_level = request.data.get('access_level')
        
        if access_level not in dict(ConnectionAccessLevel.choices):
            return Response({
                'status': 'error',
                'message': 'Invalid access level'
            }, status=status.HTTP_400_BAD_REQUEST)

        connection.update_access_level(access_level)
        serializer = self.get_serializer(connection)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Update data sharing preferences",
        request_body=DataSharingPreferenceSerializer,
        responses={
            200: ClientAccountantConnectionSerializer,
            400: "Invalid data",
            404: "Connection not found"
        }
    )
    @action(detail=True, methods=['patch'])
    def update_sharing(self, request, pk=None):
        connection = self.get_object()
        serializer = DataSharingPreferenceSerializer(
            connection.data_sharing,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            connection_serializer = self.get_serializer(connection)
            return Response(connection_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Deactivate connection",
        responses={
            200: "Connection deactivated successfully",
            404: "Connection not found"
        }
    )
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        connection = self.get_object()
        connection.manage_connection_status(False)
        
        # Log the activity
        ConnectionActivity.log_activity(
            connection=connection,
            user=request.user,
            action_type='connection_deactivated',
            description='Connection deactivated by user'
        )
        
        return Response({
            'status': 'success',
            'message': 'Connection deactivated successfully'
        })

    @swagger_auto_schema(
        operation_summary="Reactivate connection",
        responses={
            200: "Connection reactivated successfully",
            404: "Connection not found"
        }
    )
    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        connection = self.get_object()
        connection.manage_connection_status(True)
        
        # Log the activity
        ConnectionActivity.log_activity(
            connection=connection,
            user=request.user,
            action_type='connection_reactivated',
            description='Connection reactivated by user'
        )
        
        return Response({
            'status': 'success',
            'message': 'Connection reactivated successfully'
        })

@swagger_auto_schema(tags=['Authentication'])
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer

    @swagger_auto_schema(
        operation_summary="Request password reset email",
        request_body=PasswordResetRequestSerializer,
        responses={
            200: openapi.Response(
                description="Reset email sent",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            )
        }
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
                send_password_reset_email(user)
            except User.DoesNotExist:
                pass  # Don't reveal that email doesn't exist
            
            return Response({
                'status': 'success',
                'message': 'If an account exists with this email, a password reset link has been sent.'
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(tags=['Authentication'])
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    @swagger_auto_schema(
        operation_summary="Confirm password reset",
        request_body=PasswordResetConfirmSerializer,
        responses={
            200: openapi.Response(
                description="Password reset successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            )
        }
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            try:
                uid = urlsafe_base64_decode(serializer.validated_data['uidb64']).decode()
                user = User.objects.get(pk=uid)
                token = serializer.validated_data['token']

                if default_token_generator.check_token(user, token):
                    user.set_password(serializer.validated_data['new_password'])
                    user.save()
                    return Response({
                        'status': 'success',
                        'message': 'Password has been reset successfully'
                    })
                else:
                    return Response({
                        'status': 'error',
                        'message': 'Invalid or expired reset link'
                    }, status=status.HTTP_400_BAD_REQUEST)

            except (TypeError, ValueError, User.DoesNotExist):
                return Response({
                    'status': 'error',
                    'message': 'Invalid reset link'
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(tags=['Authentication'])
class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordChangeSerializer

    @swagger_auto_schema(
        operation_summary="Change password",
        request_body=PasswordChangeSerializer,
        responses={
            200: "Password changed successfully",
            400: "Invalid password"
        }
    )
    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, 
            context={'request': request}
        )
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            return Response({
                'status': 'success',
                'message': 'Password changed successfully'
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(tags=['Authentication'])
class OTPRequestView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OTPRequestSerializer

    @swagger_auto_schema(
        operation_summary="Request phone verification OTP via SMS",
        request_body=OTPRequestSerializer,
        responses={
            200: openapi.Response(
                description="OTP sent successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: "Invalid phone number",
            500: "SMS sending failed"
        }
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            user = request.user
            
            # Generate and save OTP
            phone_otp = PhoneOTP.create_otp_for_user(user, phone_number)
            
            # Send OTP via SMS
            sms_result = send_otp_via_sms(phone_number, phone_otp.otp)
            
            if sms_result['success']:
                return Response({
                    'status': 'success',
                    'message': 'Verification code sent successfully to your phone'
                })
            else:
                # If SMS sending failed, delete the OTP and return error
                phone_otp.delete()
                return Response({
                    'status': 'error',
                    'message': 'Failed to send verification code',
                    'details': sms_result['error']
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        return Response({
            'status': 'error',
            'message': 'Invalid phone number',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(tags=['Authentication'])
class OTPVerifyView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OTPVerifySerializer

    @swagger_auto_schema(
        operation_summary="Verify phone number with OTP",
        request_body=OTPVerifySerializer,
        responses={
            200: openapi.Response(
                description="Phone number verified successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: "Invalid or expired OTP",
            404: "OTP not found"
        }
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            otp_code = serializer.validated_data['otp']
            user = request.user
            
            try:
                # Find matching OTP
                phone_otp = PhoneOTP.objects.get(
                    user=user,
                    phone_number=phone_number,
                    is_verified=False
                )
                
                # Check if OTP is expired
                if phone_otp.is_expired():
                    # Delete expired OTP
                    phone_otp.delete()
                    return Response({
                        'status': 'error',
                        'message': 'Verification code has expired. Please request a new one.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Verify OTP
                if phone_otp.otp == otp_code:
                    # Mark OTP as verified
                    phone_otp.is_verified = True
                    phone_otp.save()
                    
                    # Update user's verified phone number
                    user.phone_number = phone_number
                    user.save()
                    
                    return Response({
                        'status': 'success',
                        'message': 'Phone number verified successfully'
                    })
                else:
                    return Response({
                        'status': 'error',
                        'message': 'Invalid verification code'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
            except PhoneOTP.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': 'No verification code found for this phone number'
                }, status=status.HTTP_404_NOT_FOUND)
                
        return Response({
            'status': 'error',
            'message': 'Invalid data',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(tags=['Authentication'])
class EmailVerificationRequestView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmailVerificationRequestSerializer

    @swagger_auto_schema(
        operation_summary="Request email verification",
        responses={ 
            200: "Verification email sent",
            400: "Invalid request"
        }
    )
    def post(self, request):
        user = request.user
        if user.is_verified:
            return Response({
                'status': 'error',
                'message': 'Email already verified'
            }, status=status.HTTP_400_BAD_REQUEST)

        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Send verification email
        verify_url = f"{settings.FRONTEND_URL}/authentication/email-verification/{uid}/{token}"
        send_mail(
            'Verify Your Email',
            f'Click here to verify your email: {verify_url}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email]
        )
        
        return Response({
            'status': 'success',
            'message': 'Verification email sent'
        })

@swagger_auto_schema(tags=['Authentication'])
class EmailVerificationConfirmView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Confirm email verification",
        responses={
            200: "Email verified successfully",
            400: "Invalid verification link"
        }
    )
    def get(self, request, uidb64, token):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, User.DoesNotExist):
            user = None

        if user and default_token_generator.check_token(user, token):
            user.is_verified = True
            user.save()
            return Response({
                'status': 'success',
                'message': 'Email verified successfully'
            })
        
        return Response({
            'status': 'error',
            'message': 'Invalid verification link'
        }, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(tags=['Business'])
class BusinessAccountInfoView(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
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
        admin_role = Role.objects.get(name=SystemRole.ADMIN)
        is_admin = UserRole.objects.filter(user=request.user, role=admin_role).exists()
        
        if not is_admin:
            return Response({
                'status': 'error',
                'message': 'Only admin users can access business information'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            business_account = request.user.owned_business
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
        except (AttributeError, AccountSettings.DoesNotExist):
            return Response({
                'status': 'error',
                'message': 'Business account not found'
            }, status=status.HTTP_404_NOT_FOUND)