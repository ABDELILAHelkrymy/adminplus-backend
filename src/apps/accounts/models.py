from django.db import models
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid
import boto3
from django.conf import settings
from botocore.config import Config

from apps.common.models import BaseModel
from apps.users.models import User

# Configure boto3 client with longer timeout
s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME,
    config=Config(
        connect_timeout=5,
        read_timeout=10,
        retries={'max_attempts': 2}
    )
)

# --------------------------
#  BUSINESS ACCOUNT MODEL
# --------------------------
class BusinessAccount(BaseModel):
    business_name = models.CharField(max_length=100)
    tax_number = models.CharField(max_length=50, blank=True, null=True)
    business_address = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)

    ice_number = models.CharField(max_length=50, blank=True, null=True)
    commercial_register = models.CharField(max_length=50, blank=True, null=True)

    country = models.CharField(max_length=100, blank=True, null=True)
    street = models.CharField(max_length=255, blank=True, null=True)
    street_number = models.CharField(max_length=20, blank=True, null=True)
    po_box = models.CharField(max_length=20, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    town_city = models.CharField(max_length=100, blank=True, null=True)

    # S3 key for the business logo
    logo_key = models.CharField(max_length=500, blank=True, null=True, help_text="S3 key path to logo")
    created_at = models.DateTimeField(auto_now_add=True)
    
    primary_user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='owned_business')
    internal_users = models.ManyToManyField(User, related_name='business_accounts')

    def __str__(self):
        return self.business_name
    
    def upload_logo(self, file_data, file_name=None):
        """
        Upload logo to S3 and store the file key
        """
        ext = file_data.name.split('.')[-1]
        # Organize logos in business/ID/logo/ directory
        file_name = file_name or f"business/{self.id}_{self.business_name}/logo/{uuid.uuid4()}.{ext}"
        saved_key = default_storage.save(file_name, ContentFile(file_data.read()))
        self.logo_key = saved_key
        self.save()
        return self.get_logo_url()

    def get_logo_url(self, expires_in=3600):
        """
        Return signed S3 URL from stored key
        """
        if not self.logo_key:
            return None

        return s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': self.logo_key,
                'ResponseContentDisposition': 'inline'
            },
            ExpiresIn=expires_in
        )

    def delete_logo(self):
        """
        Delete logo from S3 and clear key
        """
        if self.logo_key:
            try:
                default_storage.delete(self.logo_key)
                self.logo_key = None
                self.save()
                return True
            except Exception:
                return False
        return False
    
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

    def fill_business_email_from_user(self):
        """
        Fill business email from the primary user
        """
        if self.primary_user and not self.email:
            self.email = self.primary_user.email
            self.save()
            return True
        return False

    def get_email_for_communication(self):
        """
        Get the best email for business communication
        Returns the business email if set, otherwise the primary user's email
        """
        if self.email:
            return self.email
        elif self.primary_user:
            # If business email isn't set but primary user exists, update and return
            self.email = self.primary_user.email
            self.save()
            return self.email
        return None

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
        ('nl', 'Dutch'),
    ]
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    primary_language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    primary_color = models.CharField(max_length=7, default='#000000')  # Hex color code
    secondary_color = models.CharField(max_length=7, default='#FFFFFF')  # Hex color code
    
    # S3 key for the settings logo
    logo_key = models.CharField(max_length=500, blank=True, null=True, help_text="S3 key path to logo")
    notification_emails = models.BooleanField(default=True)
    two_factor_auth = models.BooleanField(default=False)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    def __str__(self):
        return f"Settings for {self.business_account.business_name}"
    
    def upload_logo(self, file_data, file_name=None):
        """
        Upload logo to S3 and store the file key
        """
        ext = file_data.name.split('.')[-1]
        # Organize logos in business/ID/settings/logo/ directory
        file_name = file_name or f"business/{self.business_account.id}_{self.business_account.business_name}/settings/logo/{uuid.uuid4()}.{ext}"
        saved_key = default_storage.save(file_name, ContentFile(file_data.read()))
        self.logo_key = saved_key
        self.save()
        return self.get_logo_url()

    def get_logo_url(self, expires_in=3600):
        """
        Return signed S3 URL from stored key
        """
        if not self.logo_key:
            return None

        return s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': self.logo_key,
                'ResponseContentDisposition': 'inline'
            },
            ExpiresIn=expires_in
        )

    def delete_logo(self):
        """
        Delete logo from S3 and clear key
        """
        if self.logo_key:
            try:
                default_storage.delete(self.logo_key)
                self.logo_key = None
                self.save()
                return True
            except Exception:
                return False
        return False
    
    def update_settings(self, **kwargs):
        """
        Update account settings
        :param kwargs: Settings to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save()
