from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from .models import BusinessAccount, AccountSettings
from apps.users.models import Role, SystemRole, UserRole

User = get_user_model()


class AccountSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountSettings
        fields = [
            'id', 'business_account', 'currency', 'language', 
            'primary_language', 'primary_color', 'secondary_color',
            'logo', 'notification_emails', 'two_factor_auth',
        ]
        read_only_fields = ['created_at', 'updated_at', 'business_account']
    
    def validate_currency(self, value):
        # Make sure the currency is valid
        if value not in [choice[0] for choice in AccountSettings.CURRENCY_CHOICES]:
            raise serializers.ValidationError(f"Invalid currency. Choose from {[choice[0] for choice in AccountSettings.CURRENCY_CHOICES]}")
        return value
    
    def validate_language(self, value):
        # Make sure the language is valid
        if value not in [choice[0] for choice in AccountSettings.LANGUAGE_CHOICES]:
            raise serializers.ValidationError(f"Invalid language. Choose from {[choice[0] for choice in AccountSettings.LANGUAGE_CHOICES]}")
        return value

class BusinessAccountSerializer(serializers.ModelSerializer):
    primary_user = serializers.PrimaryKeyRelatedField(read_only=True)
    settings = AccountSettingsSerializer(read_only=True)

    class Meta:
        model = BusinessAccount
        fields = [
            'id', 'business_name', 'tax_number', 'business_address', 
            'phone_number', 'website', 'primary_user',
            'ice_number', 'commercial_register', 'country', 'street',
            'street_number', 'po_box', 'zip_code', 'town_city', 'logo',
            'created_at', 'updated_at', 'settings'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_business_name(self, value):
        # Make sure the business name is unique
        if BusinessAccount.objects.filter(business_name=value).exists():
            raise serializers.ValidationError("Business name already exists.")
        return value

class BusinessAccountMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessAccount
        fields = ['id', 'business_name', 'phone_number', 'website']


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
            'currency': validated_data.pop('currency', 'USD'),
            'language': validated_data.pop('language', 'en'),
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
            is_verified=False
        )

        # Get admin role
        admin_role = Role.objects.get(name=SystemRole.ADMIN)
        
        # Assign admin role to user
        UserRole.objects.create(
            user=user,
            role=admin_role,
            system_role=SystemRole.ADMIN
        )

        # Create business account with the primary user
        business_data['primary_user'] = user
        business_account = BusinessAccount.objects.create(**business_data)
        
        # Create settings for the business account
        settings_data['business_account'] = business_account
        settings = AccountSettings.objects.create(**settings_data)
        
        return {
            'user': user,
            'business_account': business_account,
            'settings': settings
        }