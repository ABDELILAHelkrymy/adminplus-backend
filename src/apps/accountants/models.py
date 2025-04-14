from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel
from apps.users.models import User
from apps.accounts.models import BusinessAccount


# --------------------------
#  INVITATION STATUS CHOICES
# --------------------------
class InvitationStatus(models.TextChoices):
    PENDING = 'pending', _('Pending')
    ACCEPTED = 'accepted', _('Accepted')
    REJECTED = 'rejected', _('Rejected')
    EXPIRED = 'expired', _('Expired')
    CANCELLED = 'cancelled', _('Cancelled')


# --------------------------
#  EXTERNAL ACCOUNTANT ACCOUNT MODEL
# --------------------------
class ExternalAccountantAccount(BaseModel):
    accountant_name = models.CharField(max_length=100)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    tax_number = models.CharField(max_length=50, blank=True, null=True)
    contact_phone = models.CharField(max_length=15, blank=True, null=True)
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='accountant_account')
    
    def __str__(self):
        return self.accountant_name
    
    @classmethod
    def create_account(cls, user, accountant_name, **kwargs):
        """
        Create a new accountant account
        :param user: User to associate the account with
        :param accountant_name: Name of the accountant
        :param kwargs: Additional fields
        :return: ExternalAccountantAccount instance
        """
        return cls.objects.create(
            user=user,
            accountant_name=accountant_name,
            **kwargs
        )
    
    def manage_invitations(self):
        """
        Get all invitations for this accountant
        :return: QuerySet of invitations
        """
        # Queries both pending and past invitations
        return AccountantInvitation.objects.filter(
            accountant_email=self.user.email
        ).order_by('-created_at')


# --------------------------
#  ACCOUNTANT INVITATION MODEL
# --------------------------
class AccountantInvitation(BaseModel):
    sender = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name='sent_invitations')
    accountant_email = models.EmailField()
    recipient = models.ForeignKey(ExternalAccountantAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_invitations')
    
    sent_date = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateTimeField()
    response_date = models.DateTimeField(null=True, blank=True)
    invitation_message = models.TextField(blank=True, null=True)
    
    status = models.CharField(
        max_length=10,
        choices=InvitationStatus.choices,
        default=InvitationStatus.PENDING
    )
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_invitations')
    
    def __str__(self):
        return f"Invitation from {self.sender.business_name} to {self.accountant_email}"
    
    def update_status(self, new_status):
        """
        Update the invitation status
        :param new_status: New status from InvitationStatus
        """
        self.status = new_status
        if new_status in [InvitationStatus.ACCEPTED, InvitationStatus.REJECTED]:
            self.response_date = timezone.now()
        self.save()
    
    def accept_invitation(self, accountant_account):
        """
        Accept the invitation and create a connection
        :param accountant_account: ExternalAccountantAccount accepting the invitation
        :return: ClientAccountantConnection instance
        """
        from apps.connections.models import ClientAccountantConnection, ConnectionAccessLevel
        
        # Update invitation status
        self.recipient = accountant_account
        self.update_status(InvitationStatus.ACCEPTED)
        
        # Create a connection
        connection = ClientAccountantConnection.objects.create(
            client=self.sender,
            accountant=accountant_account,
            access_level=ConnectionAccessLevel.READ_ONLY,
            created_by=self.created_by
        )
        
        return connection
    
    def reject_invitation(self):
        """Reject the invitation"""
        self.update_status(InvitationStatus.REJECTED)
    
    def cancel_invitation(self, cancelled_by):
        """
        Cancel the invitation
        :param cancelled_by: User cancelling the invitation
        """
        self.update_status(InvitationStatus.CANCELLED)
        # Log cancellation (could add an activity log here)
    
    def is_expired(self):
        """
        Check if the invitation is expired
        :return: Boolean indicating if expired
        """
        if timezone.now() > self.expiry_date and self.status == InvitationStatus.PENDING:
            self.update_status(InvitationStatus.EXPIRED)
            return True
        return self.status == InvitationStatus.EXPIRED
