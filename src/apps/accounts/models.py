from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel
from apps.users.models import User


# --------------------------
#  BUSINESS ACCOUNT MODEL
# --------------------------
class BusinessAccount(BaseModel):
    business_name = models.CharField(max_length=100)
    tax_number = models.CharField(max_length=50, blank=True, null=True)
    business_address = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    ice_number = models.CharField(max_length=50, blank=True, null=True)
    commercial_register = models.CharField(max_length=50, blank=True, null=True)

    country = models.CharField(max_length=100, blank=True, null=True)
    street = models.CharField(max_length=255, blank=True, null=True)
    street_number = models.CharField(max_length=20, blank=True, null=True)
    po_box = models.CharField(max_length=20, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    town_city = models.CharField(max_length=100, blank=True, null=True)


    logo = models.ImageField(upload_to='business_logos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    primary_user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='owned_business')
    internal_users = models.ManyToManyField(User, related_name='business_accounts')

    def __str__(self):
        return self.business_name
    
    def manage_users(self, user, add=True):
        """
        Centralized method to add or remove internal users
        :param user: User to add or remove
        :param add: Boolean to determine whether to add or remove
        """
        if add:
            self.internal_users.add(user)
        else:
            self.internal_users.remove(user)
    
    def prepare_accountant_invitation(self, email, created_by):
        """
        Prepare an accountant invitation
        :param email: Email of the accountant
        :param created_by: User creating the invitation
        :return: AccountantInvitation instance
        """
        from apps.accountants.models import AccountantInvitation, InvitationStatus
        return AccountantInvitation.objects.create(
            sender=self,
            accountant_email=email,
            expiry_date=timezone.now() + timezone.timedelta(days=7),
            status=InvitationStatus.PENDING,
            created_by=created_by
        )


# --------------------------
#  ACCOUNT SETTINGS MODEL
# --------------------------
class AccountSettings(BaseModel):
    business_account = models.OneToOneField(BusinessAccount, on_delete=models.CASCADE, related_name='settings')
    
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('MAD', 'Moroccan Dirham'),
    ]
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('fr', 'French'),
        ('ar', 'Arabic'),
    ]
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    
    notification_emails = models.BooleanField(default=True)
    two_factor_auth = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Settings for {self.business_account.business_name}"
    
    def update_settings(self, **kwargs):
        """
        Update account settings
        :param kwargs: Settings to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save()
