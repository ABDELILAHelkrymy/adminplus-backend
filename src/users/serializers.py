# serializers.py
from rest_framework import serializers
from .models import User, Role, SystemRole, UserRole, BusinessAccount, ExternalAccountantAccount, AccountSettings, AccountantInvitation, DataSharingPreference, ClientAccountantConnection
from django.db import transaction
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate

class RoleNames:
    ADMIN = 'admin'
    ACCOUNTANT = 'accountant'
    CLIENT = 'client'

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ('id', 'name')

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'is_active')

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if email and password:
            user = authenticate(email=email, password=password)
            if user:
                if not user.is_active:
                    raise serializers.ValidationError('User account is disabled.')
                data['user'] = user
                return data
            raise serializers.ValidationError('Unable to log in with provided credentials.')
        raise serializers.ValidationError('Must include "email" and "password".')

class TokenSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()

class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()

class AdminRegistrationSerializer(serializers.Serializer):
    # User fields
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone_number = serializers.CharField(required=False)
    
    # Business Account fields
    business_name = serializers.CharField()
    tax_number = serializers.CharField(required=False)
    business_address = serializers.CharField(required=False)
    business_phone = serializers.CharField(required=False)
    website = serializers.URLField(required=False)

    # Account Settings fields
    currency = serializers.ChoiceField(choices=AccountSettings.CURRENCY_CHOICES, required=False)
    language = serializers.ChoiceField(choices=AccountSettings.LANGUAGE_CHOICES, required=False)
    notification_emails = serializers.BooleanField(default=True)
    two_factor_auth = serializers.BooleanField(default=False)

    def create(self, validated_data):
        # Extract settings data
        settings_data = {
            'currency': validated_data.pop('currency', AccountSettings.DEFAULT_CURRENCY),
            'language': validated_data.pop('language', AccountSettings.DEFAULT_LANGUAGE),
            'notification_emails': validated_data.pop('notification_emails', True),
            'two_factor_auth': validated_data.pop('two_factor_auth', False),
        }

        # Extract business data
        business_data = {
            'business_name': validated_data.pop('business_name'),
            'tax_number': validated_data.pop('tax_number', None),
            'business_address': validated_data.pop('business_address', None),
            'phone_number': validated_data.pop('business_phone', None),
            'website': validated_data.pop('website', None),
        }

        # Create user
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            phone_number=validated_data.get('phone_number'),
            is_active=True,
            is_verified=False  # Requires email verification
        )

        # Get or create admin role
        admin_role = Role.objects.get(name=SystemRole.ADMIN)
        
        # Assign admin role to user
        UserRole.objects.create(
            user=user,
            role=admin_role,
            system_role=SystemRole.ADMIN
        )

        # Create account settings
        account_settings = AccountSettings.objects.create(**settings_data)

        # Create business account with settings
        business_data['primary_user'] = user
        business_data['settings'] = account_settings
        business_account = BusinessAccount.objects.create(**business_data)
        
        return {
            'user': user,
            'business_account': business_account,
            'settings': account_settings
        }

class ExternalAccountantRegistrationSerializer(serializers.Serializer):
    # User fields
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone_number = serializers.CharField(required=False)
    
    # External Accountant fields
    accountant_name = serializers.CharField()
    company_name = serializers.CharField(required=False)
    tax_number = serializers.CharField(required=False)
    contact_phone = serializers.CharField(required=False)

    def create(self, validated_data):
        # Extract accountant data
        accountant_data = {
            'accountant_name': validated_data.pop('accountant_name'),
            'company_name': validated_data.pop('company_name', None),
            'tax_number': validated_data.pop('tax_number', None),
            'contact_phone': validated_data.pop('contact_phone', None),
        }

        # Create user
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            phone_number=validated_data.get('phone_number'),
            is_active=True,
            is_verified=False
        )

        # Get viewer role (external accountants are viewers by default)
        viewer_role = Role.objects.get(name=SystemRole.VIEWER)
        
        # Assign viewer role to user
        UserRole.objects.create(
            user=user,
            role=viewer_role,
            system_role=SystemRole.VIEWER
        )

        # Create external accountant account
        accountant_data['user'] = user
        external_accountant = ExternalAccountantAccount.objects.create(**accountant_data)
        
        return {
            'user': user,
            'external_accountant': external_accountant
        }
    

class AccountSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountSettings
        fields = ['currency', 'language', 'notification_emails', 'two_factor_auth']
        read_only_fields = ['created_at', 'updated_at']

    def validate_currency(self, value):
        valid_currencies = dict(AccountSettings.CURRENCY_CHOICES)
        if value not in valid_currencies:
            raise serializers.ValidationError(f"Invalid currency. Choose from: {', '.join(valid_currencies.keys())}")
        return value

    def validate_language(self, value):
        valid_languages = dict(AccountSettings.LANGUAGE_CHOICES)
        if value not in valid_languages:
            raise serializers.ValidationError(f"Invalid language. Choose from: {', '.join(valid_languages.keys())}")
        return value

class InternalUserCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone_number = serializers.CharField(required=False)
    system_role = serializers.ChoiceField(choices=[
        (SystemRole.INTERNAL_ACCOUNTANT, 'Internal Accountant'),
        (SystemRole.EMPLOYEE, 'Employee'),
        (SystemRole.VIEWER, 'Viewer'),
    ])
    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), write_only=True)

    def create(self, validated_data):
        # Extract and remove system_role from validated_data
        system_role = validated_data.pop('system_role')
        
        # Create user
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            phone_number=validated_data.get('phone_number'),
            is_active=True,
            is_verified=False,
            created_by=self.context['request'].user
        )
        
        # Assign role to user
        UserRole.objects.create(
            user=user,
            role=validated_data['role'],
            system_role=system_role
        )

        # Add user to business account
        business_account = self.context['request'].user.owned_business
        business_account.internal_users.add(user)
        
        return user
    
class BusinessAccountMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessAccount
        fields = ['id', 'business_name', 'phone_number', 'website']

class AccountantInvitationSerializer(serializers.ModelSerializer):
    sender_details = BusinessAccountMinimalSerializer(source='sender', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    recipient_details = serializers.SerializerMethodField()

    class Meta:
        model = AccountantInvitation
        fields = [
            'id', 
            'sender_details',
            'recipient_details',
            'accountant_email', 
            'invitation_message',
            'sent_date',
            'expiry_date',
            'status',
            'status_display',
            'is_expired',
            'created_by_name',
            'response_date'
        ]
        read_only_fields = [
            'sent_date', 
            'expiry_date', 
            'status', 
            'sender_details',
            'recipient_details',
            'created_by_name',
            'response_date'
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}"
        return None

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_is_expired(self, obj):
        return obj.is_expired()

    def get_recipient_details(self, obj):
        if obj.recipient:
            return {
                'id': str(obj.recipient.id),
                'accountant_name': obj.recipient.accountant_name,
                'company_name': obj.recipient.company_name
            }
        return None

    def create(self, validated_data):
        request = self.context.get('request')
        business_account = request.user.owned_business
        
        invitation = business_account.prepare_accountant_invitation(
            email=validated_data['accountant_email'],
            created_by=request.user
        )
        
        if validated_data.get('invitation_message'):
            invitation.invitation_message = validated_data['invitation_message']
            invitation.save()
        
        return invitation

class DataSharingPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSharingPreference
        fields = [
            'share_invoices', 'share_expenses', 'share_bank_data',
            'share_tax_documents', 'share_reports'
        ]

class ClientAccountantConnectionSerializer(serializers.ModelSerializer):
    client_details = BusinessAccountMinimalSerializer(source='client', read_only=True)
    accountant_details = serializers.SerializerMethodField()
    data_sharing = DataSharingPreferenceSerializer(read_only=True)
    
    class Meta:
        model = ClientAccountantConnection
        fields = [
            'id', 'client_details', 'accountant_details', 'connection_date',
            'is_active', 'last_access', 'access_level', 'notes', 'data_sharing'
        ]
        read_only_fields = ['connection_date', 'last_access']

    def get_accountant_details(self, obj):
        return {
            'id': str(obj.accountant.id),
            'accountant_name': obj.accountant.accountant_name,
            'company_name': obj.accountant.company_name,
            'contact_phone': obj.accountant.contact_phone
        }

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    uidb64 = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    
    def validate_new_password(self, value):
        validate_password(value)
        return value

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    
    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

class EmailVerificationRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class EmailVerificationConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()