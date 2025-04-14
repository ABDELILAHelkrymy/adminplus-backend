from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.utils import timezone
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging

from .models import ExternalAccountantAccount, AccountantInvitation, InvitationStatus
from .serializers import (
    ExternalAccountantRegistrationSerializer,
    AccountantInvitationSerializer
)
from apps.accounts.models import BusinessAccount
from apps.users.permissions import IsBusinessOwner
from apps.users.models import User, Role, SystemRole, UserRole
from apps.users.utils import send_verification_email

# Set up logger
email_logger = logging.getLogger('apps.email')

@swagger_auto_schema(tags=['Auth - Registration'])
class ExternalAccountantRegistrationView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ExternalAccountantRegistrationSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            # Create user and external accountant account
            result = serializer.save()
            user = result['user']
            external_accountant = result['external_accountant']
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Send verification email without terminal logs
            send_verification_email(user)
            
            return Response({
                'status': 'success',
                'message': 'External accountant registered successfully. Please verify your email.',
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                },
                'external_accountant': {
                    'id': str(external_accountant.id),
                    'accountant_name': external_accountant.accountant_name,
                    'company_name': external_accountant.company_name,
                    'tax_number': external_accountant.tax_number,
                    'contact_phone': external_accountant.contact_phone,
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'status': 'error',
            'message': 'Invalid data provided.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)


@swagger_auto_schema(tags=['Accountants - Invitations'])
class AccountantInvitationViewSet(viewsets.ModelViewSet):
    serializer_class = AccountantInvitationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Check if this is a schema generation request
        if getattr(self, 'swagger_fake_view', False):
            return AccountantInvitation.objects.none()
            
        # Check if user is authenticated
        if not self.request.user.is_authenticated:
            return AccountantInvitation.objects.none()
            
        user = self.request.user
        
        # For business account owners, show sent invitations
        try:
            business_account = BusinessAccount.objects.get(primary_user=user)
            return AccountantInvitation.objects.filter(sender=business_account)
        except BusinessAccount.DoesNotExist:
            # For accountants, show received invitations by email
            return AccountantInvitation.objects.filter(accountant_email=user.email)
    
    @swagger_auto_schema(
        operation_id="accountant_invitation_create",
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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if the user has a business account
        try:
            business_account = BusinessAccount.objects.get(primary_user=request.user)
        except BusinessAccount.DoesNotExist:
            return Response(
                {'status': 'error', 'message': 'You must have a business account to send invitations.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if an invitation already exists for this accountant
        accountant_email = serializer.validated_data['accountant_email']
        existing_invitation = AccountantInvitation.objects.filter(
            sender=business_account,
            accountant_email=accountant_email,
            status=InvitationStatus.PENDING
        ).first()
        
        if existing_invitation:
            return Response(
                {'status': 'error', 'message': 'An invitation has already been sent to this accountant.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add the sender and created_by to the validated data
        invitation = business_account.prepare_accountant_invitation(
            email=accountant_email,
            created_by=request.user
        )
        
        if serializer.validated_data.get('invitation_message'):
            invitation.invitation_message = serializer.validated_data['invitation_message']
            invitation.save()
        
        # Return the invitation
        return Response(
            self.get_serializer(invitation).data,
            status=status.HTTP_201_CREATED
        )
    
    @swagger_auto_schema(
        operation_id="accountant_invitation_accept",
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
        try:
            invitation = self.get_object()
            
            # Check if the invitation is for the current user
            if invitation.accountant_email != request.user.email:
                return Response(
                    {'status': 'error', 'message': 'This invitation is not for you.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if the invitation is pending and not expired
            if invitation.status != InvitationStatus.PENDING:
                return Response(
                    {'status': 'error', 'message': f'Invitation is already {invitation.get_status_display().lower()}.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if invitation.is_expired():
                return Response(
                    {'status': 'error', 'message': 'Invitation has expired.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get or create an external accountant account for the user
            try:
                accountant_account = ExternalAccountantAccount.objects.get(user=request.user)
            except ExternalAccountantAccount.DoesNotExist:
                # Create an accountant account if it doesn't exist
                accountant_account = ExternalAccountantAccount.create_account(
                    user=request.user,
                    accountant_name=f"{request.user.first_name} {request.user.last_name}"
                )
            
            # Accept the invitation
            connection = invitation.accept_invitation(accountant_account)
            
            return Response({
                'status': 'success',
                'message': 'Invitation accepted successfully.',
                'invitation': self.get_serializer(invitation).data
            })
        except AccountantInvitation.DoesNotExist:
            return Response(
                {'status': 'error', 'message': 'Invitation not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @swagger_auto_schema(
        operation_id="accountant_invitation_reject",
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
        try:
            invitation = self.get_object()
            
            # Check if the invitation is for the current user
            if invitation.accountant_email != request.user.email:
                return Response(
                    {'status': 'error', 'message': 'This invitation is not for you.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if the invitation is pending
            if invitation.status != InvitationStatus.PENDING:
                return Response(
                    {'status': 'error', 'message': f'Invitation is already {invitation.get_status_display().lower()}.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Reject the invitation
            invitation.reject_invitation()
            
            return Response({
                'status': 'success',
                'message': 'Invitation rejected successfully.'
            })
        except AccountantInvitation.DoesNotExist:
            return Response(
                {'status': 'error', 'message': 'Invitation not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @swagger_auto_schema(
        operation_id="accountant_invitation_cancel",
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
        try:
            invitation = self.get_object()
            
            # Check if the invitation was sent by the current user's business
            try:
                business_account = BusinessAccount.objects.get(primary_user=request.user)
                if invitation.sender != business_account:
                    return Response(
                        {'status': 'error', 'message': 'You can only cancel invitations sent by your business.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except BusinessAccount.DoesNotExist:
                return Response(
                    {'status': 'error', 'message': 'You must have a business account to cancel invitations.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if the invitation is pending
            if invitation.status != InvitationStatus.PENDING:
                return Response(
                    {'status': 'error', 'message': f'Invitation is already {invitation.get_status_display().lower()}.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Cancel the invitation
            invitation.cancel_invitation(cancelled_by=request.user)
            
            return Response({
                'status': 'success',
                'message': 'Invitation cancelled successfully.'
            })
        except AccountantInvitation.DoesNotExist:
            return Response(
                {'status': 'error', 'message': 'Invitation not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @swagger_auto_schema(
        operation_id="accountant_invitation_resend",
        operation_summary="Resend invitation",
        responses={
            200: "Invitation resent successfully",
            404: "Invitation not found",
            403: "Permission denied"
        }
    )
    @action(detail=True, methods=['post'])
    def resend(self, request, pk=None):
        try:
            invitation = self.get_object()
            
            # Check if the invitation was sent by the current user's business
            try:
                business_account = BusinessAccount.objects.get(primary_user=request.user)
                if invitation.sender != business_account:
                    return Response(
                        {'status': 'error', 'message': 'You can only resend invitations sent by your business.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except BusinessAccount.DoesNotExist:
                return Response(
                    {'status': 'error', 'message': 'You must have a business account to resend invitations.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if the invitation is pending
            if invitation.status != InvitationStatus.PENDING:
                return Response(
                    {'status': 'error', 'message': f'Cannot resend invitation that is {invitation.get_status_display().lower()}.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Reset the expiry date and sent date
            invitation.sent_date = timezone.now()
            invitation.expiry_date = timezone.now() + timezone.timedelta(days=7)
            invitation.save()
            
            # TODO: Send the invitation email again
            
            return Response({
                'status': 'success',
                'message': 'Invitation resent successfully.',
                'invitation': self.get_serializer(invitation).data
            })
        except AccountantInvitation.DoesNotExist:
            return Response(
                {'status': 'error', 'message': 'Invitation not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
