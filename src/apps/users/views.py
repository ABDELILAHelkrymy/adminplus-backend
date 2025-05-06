from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import login, authenticate
from rest_framework.views import APIView
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from functools import wraps
import logging
from django.utils import timezone
from rest_framework.authtoken.models import Token

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import User, Role, SystemRole, UserRole, PhoneOTP
from apps.accounts.models import BusinessAccount, AccountSettings
from .serializers import (
    RoleSerializer,
    UserSerializer,
    LoginSerializer,
    TokenSerializer,
    TokenRefreshSerializer,
    InternalUserCreateSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    PasswordChangeSerializer,
    EmailVerificationRequestSerializer,
    EmailVerificationConfirmSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    RegistrationSerializer
)
from .permissions import IsBusinessOwner
from .utils import send_password_reset_email, send_verification_email, send_otp_via_sms

# Set up loggers
logger = logging.getLogger('apps.users')
email_logger = logging.getLogger('apps.email')

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


@swagger_auto_schema(tags=['Users - System Roles'])
class SystemRoleListView(APIView):
    permission_classes = [IsAuthenticated, IsBusinessOwner]
    
    @swagger_auto_schema(
        operation_id="system_roles_list",
        operation_summary="Get available system roles for internal users",
        responses={
            200: openapi.Response(
                description="List of available system roles for internal users",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'system_roles': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_STRING),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'display_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'description': openapi.Schema(type=openapi.TYPE_STRING),
                                }
                            )
                        )
                    }
                )
            ),
            403: "Permission denied"
        }
    )
    def get(self, request):
        # Return only system roles applicable for internal users
        system_roles = [
            {
                'id': SystemRole.INTERNAL_ACCOUNTANT,
                'name': SystemRole.INTERNAL_ACCOUNTANT,
                'display_name': 'Internal Accountant',
                'description': 'Company accountant with access to financial records'
            },
            {
                'id': SystemRole.EMPLOYEE,
                'name': SystemRole.EMPLOYEE,
                'display_name': 'Employee',
                'description': 'Regular employee with standard access rights'
            },
            {
                'id': SystemRole.VIEWER,
                'name': SystemRole.VIEWER,
                'display_name': 'Viewer',
                'description': 'Read-only access to permitted areas'
            }
        ]
        
        return Response({
            'status': 'success',
            'system_roles': system_roles
        })


@swagger_auto_schema(tags=['Users - Roles'])
class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]


@swagger_auto_schema(tags=['Auth - Token'])
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


@swagger_auto_schema(tags=['Auth - Login & Registration'])
class LoginView(viewsets.ViewSet):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer
    
    @swagger_auto_schema(
        operation_id="user_login",
        operation_summary="Login with email and password",
        request_body=LoginSerializer,
        responses={
            200: openapi.Response(
                'Login successful',
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
                        'user': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            401: 'Invalid credentials or inactive account'
        }
    )
    def create(self, request):
        """
        Login with email and password
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data.get('email')
        password = serializer.validated_data.get('password')
        
        logger.info(f"Login attempt for email: {email}")
        
        try:
            user = authenticate(request, email=email, password=password)
            
            if user is None:
                logger.warning(f"Failed login attempt for email: {email} - Invalid credentials")
                return Response({
                    'status': 'error',
                    'message': 'Invalid credentials'
                }, status=status.HTTP_401_UNAUTHORIZED)
                
            if not user.is_active:
                logger.warning(f"Failed login attempt for email: {email} - User inactive")
                return Response({
                    'status': 'error', 
                    'message': 'This account has been deactivated'
                }, status=status.HTTP_401_UNAUTHORIZED)
                
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Update last login
            user.last_login = timezone.now()
            user.save()
            
            logger.info(f"Successful login for user: {email}", extra={
                'user_id': str(user.id)
            })
            
            return Response({
                'status': 'success',
                'message': 'Successfully logged in.',
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'user': UserSerializer(user).data
            })
        except Exception as e:
            logger.error(f"Error during login process for {email}: {str(e)}", exc_info=True)
            return Response({
                'status': 'error',
                'message': 'An error occurred during login'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(tags=['Users - Management'])
class InternalUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, IsBusinessOwner]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InternalUserCreateSerializer
        return UserSerializer
    
    def get_queryset(self):
        # Check if this is a schema generation request
        if getattr(self, 'swagger_fake_view', False):
            return User.objects.none()
        
        # Check if user is authenticated
        if not self.request.user.is_authenticated:
            return User.objects.none()
        
        # Only return users that belong to the current user's business
        try:
            business = BusinessAccount.objects.get(primary_user=self.request.user)
            return business.internal_users.all()
        except BusinessAccount.DoesNotExist:
            return User.objects.none()
    
    @swagger_auto_schema(
        operation_id="internal_user_create",
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
        
        try:
            # Get the business account of the current user
            business_account = BusinessAccount.objects.get(primary_user=request.user)
            
            # Create the user
            user = serializer.save()
            
            # Add the user to the business account's internal users
            business_account.internal_users.add(user)
            
            # Return the created user
            return Response(
                UserSerializer(user).data,
                status=status.HTTP_201_CREATED
            )
        except BusinessAccount.DoesNotExist:
            return Response(
                {'status': 'error', 'message': 'Business account not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @swagger_auto_schema(
        operation_id="internal_user_list",
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
        operation_id="internal_user_delete",
        operation_summary="Delete internal user",
        operation_description="Remove an internal user from the business account",
        responses={
            204: 'User deleted successfully',
            403: 'Permission denied',
            404: 'User not found'
        }
    )
    def destroy(self, request, *args, **kwargs):
        try:
            user = self.get_object()
            business_account = BusinessAccount.objects.get(primary_user=request.user)
            
            # Remove the user from the business account
            business_account.internal_users.remove(user)
            
            # Deactivate the user
            user.is_active = False
            user.save()
            
            return Response(status=status.HTTP_204_NO_CONTENT)
        except (User.DoesNotExist, BusinessAccount.DoesNotExist):
            return Response(
                {'status': 'error', 'message': 'User or business account not found'},
                status=status.HTTP_404_NOT_FOUND
            )


@swagger_auto_schema(tags=['Auth - Password Recovery'])
class PasswordResetRequestView(viewsets.ViewSet):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer
    
    @swagger_auto_schema(
        operation_id="password_reset_request",
        operation_summary="Request password reset",
        request_body=PasswordResetRequestSerializer,
        responses={
            200: openapi.Response(
                'Password reset email sent',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: 'Invalid data or inactive account'
        }
    )
    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data.get('email')
        logger.info(f"Password reset request received for email: {email}")
        
        try:
            user = User.objects.get(email=email)
            
            if not user.is_active:
                logger.warning(f"Password reset requested for inactive user: {email}")
                return Response({
                    'status': 'error',
                    'message': 'User account is not active.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Add debug information to the response
            email_debug = {
                'host': settings.EMAIL_HOST,
                'port': settings.EMAIL_PORT,
                'use_tls': settings.EMAIL_USE_TLS,
                'from_email': settings.EMAIL_HOST_USER,
                'to_email': user.email
            }
            
            # Send the reset email with error handling
            email_sent = send_password_reset_email(user)
            if not email_sent:
                email_logger.error(f"Failed to send password reset email to {user.email}", extra={
                    'user_id': str(user.id),
                    'to': user.email,
                    'from': settings.EMAIL_HOST_USER,
                    'host': settings.EMAIL_HOST,
                    'port': settings.EMAIL_PORT
                })
                return Response({
                    'status': 'error',
                    'message': 'Failed to send password reset email. Please try again later.',
                    'debug': email_debug
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            email_logger.info(f"Password reset email sent successfully to {user.email}", extra={
                'user_id': str(user.id),
                'to': user.email
            })
            return Response({
                'status': 'success',
                'message': 'Password reset email has been sent if the email is registered.',
                'debug': email_debug
            })
        except User.DoesNotExist:
            logger.warning(f"Password reset requested for non-existent email: {email}")
            # Return the same response to prevent email enumeration
            return Response({
                'status': 'success',
                'message': 'Password reset email has been sent if the email is registered.'
            })


@swagger_auto_schema(tags=['Auth - Password Recovery'])
class PasswordResetConfirmView(viewsets.ViewSet):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer
    
    @swagger_auto_schema(
        operation_id="password_reset_confirm",
        operation_summary="Confirm password reset",
        request_body=PasswordResetConfirmSerializer,
        responses={
            200: openapi.Response(
                'Password reset successful',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: 'Invalid or expired token'
        }
    )
    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        uidb64 = serializer.validated_data.get('uidb64')
        token = serializer.validated_data.get('token')
        new_password = serializer.validated_data.get('new_password')
        
        logger.info("Password reset confirmation request received")
        
        try:
            # Decode the uidb64 to get the user id
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
            
            # Check if the token is valid
            if default_token_generator.check_token(user, token):
                logger.info(f"Valid password reset token for user: {user.email}", extra={
                    'user_id': str(user.id)
                })
                
                # Set the new password
                user.set_password(new_password)
                user.save()
                
                logger.info(f"Password reset successful for user: {user.email}", extra={
                    'user_id': str(user.id)
                })
                
                return Response({
                    'status': 'success',
                    'message': 'Password has been reset successfully.'
                })
            else:
                logger.warning(f"Invalid reset token for user: {user.email}", extra={
                    'user_id': str(user.id),
                    'token': token
                })
                return Response({
                    'status': 'error',
                    'message': 'Invalid or expired token.'
                }, status=status.HTTP_400_BAD_REQUEST)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
            logger.warning(f"Invalid user ID or token in password reset: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Invalid or expired token.'
            }, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(tags=['Auth - Password Management'])
class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordChangeSerializer
    
    @swagger_auto_schema(
        operation_id="password_change",
        operation_summary="Change password",
        request_body=PasswordChangeSerializer,
        responses={
            200: "Password changed successfully",
            400: "Invalid password"
        }
    )
    def post(self, request):
        logger.info(f"Password change request received for user: {request.user.email}", extra={
            'user_id': str(request.user.id)
        })
        
        serializer = self.serializer_class(data=request.data, context={'user': request.user})
        
        if not serializer.is_valid():
            logger.warning(f"Invalid password change data for user: {request.user.email}", extra={
                'user_id': str(request.user.id),
                'errors': serializer.errors
            })
            return Response({
                'status': 'error',
                'message': 'Invalid data provided',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Update password
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            
            logger.info(f"Password changed successfully for user: {request.user.email}", extra={
                'user_id': str(request.user.id)
            })
            
            return Response({
                'status': 'success',
                'message': 'Password has been changed successfully.'
            })
        except Exception as e:
            logger.error(f"Error changing password for user: {request.user.email} - {str(e)}", extra={
                'user_id': str(request.user.id),
                'error': str(e)
            })
            return Response({
                'status': 'error',
                'message': 'Error changing password. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(tags=['Auth - Phone Verification'])
class OTPRequestView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OTPRequestSerializer
    
    @swagger_auto_schema(
        operation_id="otp_request",
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
        logger.info(f"OTP request received for user: {request.user.email}", extra={
            'user_id': str(request.user.id)
        })
        
        serializer = self.serializer_class(data=request.data)
        
        if not serializer.is_valid():
            logger.warning(f"Invalid phone number data for OTP request: {request.user.email}", extra={
                'user_id': str(request.user.id),
                'errors': serializer.errors
            })
            return Response({
                'status': 'error',
                'message': 'Invalid phone number',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        phone_number = serializer.validated_data['phone_number']
        logger.info(f"Processing OTP request for phone: {phone_number}", extra={
            'user_id': str(request.user.id),
            'phone': phone_number
        })
        
        try:
            # Create OTP
            otp_instance = PhoneOTP.create_otp_for_user(
                user=request.user,
                phone_number=phone_number
            )
            
            logger.info(f"OTP generated for phone: {phone_number}", extra={
                'user_id': str(request.user.id),
                'phone': phone_number,
                'otp_id': str(otp_instance.id)
            })
            
            # Send OTP via SMS
            success = send_otp_via_sms(phone_number, otp_instance.otp)
            
            if success:
                logger.info(f"OTP sent successfully to phone: {phone_number}", extra={
                    'user_id': str(request.user.id),
                    'phone': phone_number,
                    'otp_id': str(otp_instance.id)
                })
                return Response({
                    'status': 'success',
                    'message': f'OTP has been sent to {phone_number}.'
                })
            else:
                logger.error(f"Failed to send OTP to phone: {phone_number}", extra={
                    'user_id': str(request.user.id),
                    'phone': phone_number,
                    'otp_id': str(otp_instance.id)
                })
                return Response({
                    'status': 'error',
                    'message': 'Failed to send OTP. Please try again later.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error creating or sending OTP: {str(e)}", extra={
                'user_id': str(request.user.id),
                'phone': phone_number,
                'error': str(e)
            })
            return Response({
                'status': 'error',
                'message': f'Error creating or sending OTP: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(tags=['Auth - Phone Verification'])
class OTPVerifyView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OTPVerifySerializer
    
    @swagger_auto_schema(
        operation_id="otp_verify",
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
        logger.info(f"OTP verification request received for user: {request.user.email}", extra={
            'user_id': str(request.user.id)
        })
        
        serializer = self.serializer_class(data=request.data)
        
        if not serializer.is_valid():
            logger.warning(f"Invalid OTP verification data: {request.user.email}", extra={
                'user_id': str(request.user.id),
                'errors': serializer.errors
            })
            return Response({
                'status': 'error',
                'message': 'Invalid data provided',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        phone_number = serializer.validated_data['phone_number']
        otp = serializer.validated_data['otp']
        
        logger.info(f"Verifying OTP for phone: {phone_number}", extra={
            'user_id': str(request.user.id),
            'phone': phone_number
        })
        
        try:
            # Get the latest OTP for this user and phone number
            otp_obj = PhoneOTP.objects.filter(
                user=request.user,
                phone_number=phone_number
            ).order_by('-created_at').first()
            
            if not otp_obj:
                logger.warning(f"No OTP found for phone: {phone_number}", extra={
                    'user_id': str(request.user.id),
                    'phone': phone_number
                })
                return Response({
                    'status': 'error',
                    'message': 'No OTP found for this phone number.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check if OTP is expired
            if otp_obj.is_expired():
                logger.warning(f"Expired OTP for phone: {phone_number}", extra={
                    'user_id': str(request.user.id),
                    'phone': phone_number,
                    'otp_id': str(otp_obj.id),
                    'created_at': str(otp_obj.created_at)
                })
                return Response({
                    'status': 'error',
                    'message': 'OTP has expired. Please request a new one.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify OTP
            if otp_obj.otp != otp:
                logger.warning(f"Invalid OTP provided for phone: {phone_number}", extra={
                    'user_id': str(request.user.id),
                    'phone': phone_number,
                    'otp_id': str(otp_obj.id),
                    'provided_otp': otp
                })
                return Response({
                    'status': 'error',
                    'message': 'Invalid OTP.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Mark OTP as verified
            otp_obj.is_verified = True
            otp_obj.save()
            
            # Update user's phone number
            request.user.phone_number = phone_number
            request.user.save()
            
            logger.info(f"Phone number verified successfully: {phone_number}", extra={
                'user_id': str(request.user.id),
                'phone': phone_number,
                'otp_id': str(otp_obj.id)
            })
            return Response({
                'status': 'success',
                'message': 'Phone number verified successfully.'
            })
            
        except Exception as e:
            logger.error(f"Error verifying OTP: {str(e)}", extra={
                'user_id': str(request.user.id),
                'phone': phone_number,
                'error': str(e)
            })
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(tags=['Auth - Email Verification'])
class EmailVerificationRequestView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = EmailVerificationRequestSerializer
    
    @swagger_auto_schema(
        operation_id="email_verification_request",
        operation_summary="Request email verification",
        responses={ 
            200: "Verification email sent",
            400: "Invalid request",
            500: "Email sending failed"
        }
    )
    def create(self, request):
        # Send verification email to current user
        user = request.user
        
        email_logger.info(f"Email verification request received for user {user.email}", extra={
            'user_id': str(user.id),
            'to': user.email
        })
        
        if user.is_verified:
            email_logger.info(f"Email already verified for user {user.email}", extra={
                'user_id': str(user.id),
                'to': user.email
            })
            return Response({
                'status': 'error',
                'message': 'Email is already verified.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if email is provided in the serializer    
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            # If email is provided in the request, use that instead of user's email
            email = serializer.validated_data.get('email')
            if email and email != user.email:
                # Update the user's email if different
                old_email = user.email
                user.email = email
                user.save()
                email_logger.info(f"User email updated from {old_email} to {email}", extra={
                    'user_id': str(user.id),
                    'from': old_email,
                    'to': email
                })
        
        # Add debug information to the response
        email_debug = {
            'host': settings.EMAIL_HOST,
            'port': settings.EMAIL_PORT,
            'use_tls': settings.EMAIL_USE_TLS,
            'from_email': settings.EMAIL_HOST_USER,
            'to_email': user.email
        }
        
        # Send the verification email with error handling
        email_sent = send_verification_email(user)
        if not email_sent:
            email_logger.error(f"Failed to send verification email to {user.email}", extra={
                'user_id': str(user.id),
                'to': user.email,
                'from': settings.EMAIL_HOST_USER,
                'host': settings.EMAIL_HOST,
                'port': settings.EMAIL_PORT
            })
            return Response({
                'status': 'error',
                'message': 'Failed to send verification email. Please try again later.',
                'debug': email_debug
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        email_logger.info(f"Verification email sent successfully to {user.email}", extra={
            'user_id': str(user.id),
            'to': user.email
        })
        return Response({
            'status': 'success',
            'message': f'Verification email has been sent to {user.email}.',
            'debug': email_debug
        })
    
    # Original post method as an alias for create
    def post(self, request):
        return self.create(request)

    @swagger_auto_schema(
        operation_id="email_verification_test",
        operation_summary="Test email configuration",
        responses={ 
            200: "Email configuration test results",
        }
    )
    @action(detail=False, methods=['get'])
    def test_email_config(self, request):
        """Test the email configuration by connecting to the SMTP server."""
        import socket
        import smtplib
        
        email_logger.info("Email configuration test initiated", extra={
            'user_id': str(request.user.id),
            'user_email': request.user.email
        })
        
        debug_info = {
            'host': settings.EMAIL_HOST,
            'port': settings.EMAIL_PORT,
            'use_tls': settings.EMAIL_USE_TLS,
            'from_email': settings.EMAIL_HOST_USER,
            'auth_user': settings.EMAIL_HOST_USER,
        }
        
        # Test connection to SMTP server
        try:
            # Check if the SMTP server is reachable
            email_logger.debug(f"Testing connection to {settings.EMAIL_HOST}:{settings.EMAIL_PORT}", extra={
                'host': settings.EMAIL_HOST,
                'port': settings.EMAIL_PORT
            })
            sock = socket.create_connection(
                (settings.EMAIL_HOST, settings.EMAIL_PORT), 
                timeout=5
            )
            sock.close()
            debug_info['connection_test'] = 'Success'
            email_logger.info(f"Successfully connected to {settings.EMAIL_HOST}:{settings.EMAIL_PORT}", extra={
                'host': settings.EMAIL_HOST,
                'port': settings.EMAIL_PORT
            })
        except Exception as e:
            debug_info['connection_test'] = f'Failed: {str(e)}'
            email_logger.error(f"Failed to connect to {settings.EMAIL_HOST}:{settings.EMAIL_PORT}: {str(e)}", extra={
                'host': settings.EMAIL_HOST,
                'port': settings.EMAIL_PORT,
                'error': str(e)
            })
        
        # Test SMTP login
        try:
            # Try to log in to the SMTP server
            smtp = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
            smtp.ehlo()
            if settings.EMAIL_USE_TLS:
                smtp.starttls()
                smtp.ehlo()
            smtp.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            smtp.quit()
            debug_info['smtp_login'] = 'Success'
        except Exception as e:
            debug_info['smtp_login'] = f'Failed: {str(e)}'
        
        # Test sending a test email
        try:
            # Try to send a test email
            subject = 'AdminPlus Email Configuration Test'
            message = 'This is a test email to verify the email configuration.'
            from_email = settings.EMAIL_HOST_USER
            recipient_list = [request.user.email]
            
            send_mail(
                subject,
                message,
                from_email,
                recipient_list,
                fail_silently=False,
            )
            debug_info['send_mail'] = 'Success'
        except Exception as e:
            debug_info['send_mail'] = f'Failed: {str(e)}'
        
        return Response({
            'status': 'success',
            'message': 'Email configuration test completed',
            'debug': debug_info
        })


@swagger_auto_schema(tags=['Auth - Email Verification'])
class EmailVerificationConfirmView(APIView):
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_id="email_verification_confirm",
        operation_summary="Confirm email verification",
        responses={
            200: "Email verified successfully",
            400: "Invalid verification link"
        }
    )
    def get(self, request, uidb64, token):
        email_logger.info(f"Email verification confirmation attempt with token", extra={
            'uidb64': uidb64,
            'token': token
        })
        
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
            
            email_logger.info(f"User found for verification: {user.email}", extra={
                'user_id': str(user.id),
                'user_email': user.email
            })
        except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
            email_logger.error(f"Invalid user ID in verification link: {str(e)}", extra={
                'uidb64': uidb64,
                'error': str(e)
            })
            return Response({
                'status': 'error',
                'message': 'Invalid verification link.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if default_token_generator.check_token(user, token):
            if user.is_verified:
                email_logger.info(f"User already verified: {user.email}", extra={
                    'user_id': str(user.id)
                })
                return Response({
                    'status': 'success',
                    'message': 'Email has already been verified.'
                })
                
            user.is_verified = True
            user.save()
            
            email_logger.info(f"Email verified successfully: {user.email}", extra={
                'user_id': str(user.id)
            })
            
            return Response({
                'status': 'success',
                'message': 'Email has been verified successfully.'
            })
        else:
            email_logger.warning(f"Invalid token for user: {user.email}", extra={
                'user_id': str(user.id),
                'token': token
            })
            return Response({
                'status': 'error',
                'message': 'Invalid verification link.'
            }, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(tags=['Auth - Logout'])
class LogoutView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def create(self, request):
        """
        Logout and delete token
        """
        try:
            user = request.user
            logger.info(f"Logout request for user: {user.email}", extra={
                'user_id': str(user.id)
            })
            
            # Delete the token
            request.auth.delete()
            
            logger.info(f"User logged out successfully: {user.email}", extra={
                'user_id': str(user.id)
            })
            
            return Response({
                'status': 'success',
                'message': 'Logged out successfully'
            })
        except Exception as e:
            logger.error(f"Error during logout process: {str(e)}", exc_info=True, extra={
                'user_id': str(request.user.id) if request.user.is_authenticated else 'unknown'
            })
            return Response({
                'status': 'error',
                'message': 'An error occurred during logout'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(tags=['Auth - Email Verification'])
class EmailVerificationView(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    def retrieve(self, request, uid, token):
        """
        Verify email with uid and token
        """
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
            
            logger.info(f"Email verification attempt for user ID: {user_id}", extra={
                'user_email': user.email
            })
            
            if default_token_generator.check_token(user, token):
                if user.is_verified:
                    logger.info(f"User already verified: {user.email}", extra={
                        'user_id': str(user.id)
                    })
                    return Response({
                        'status': 'success',
                        'message': 'Email already verified.'
                    })
                
                # Update user verification status
                user.is_verified = True
                user.save()
                
                logger.info(f"Email verification successful for user: {user.email}", extra={
                    'user_id': str(user.id)
                })
                
                return Response({
                    'status': 'success',
                    'message': 'Email verification successful.'
                })
            else:
                logger.warning(f"Invalid verification token for user: {user.email}", extra={
                    'user_id': str(user.id),
                    'token': token
                })
                return Response({
                    'status': 'error',
                    'message': 'Invalid verification link.'
                }, status=status.HTTP_400_BAD_REQUEST)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
            logger.error(f"Email verification failed: {str(e)}", exc_info=True, extra={
                'uid': uid,
                'token': token
            })
            return Response({
                'status': 'error',
                'message': 'Invalid verification link.'
            }, status=status.HTTP_400_BAD_REQUEST) 