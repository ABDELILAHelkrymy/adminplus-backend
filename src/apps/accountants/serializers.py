from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from .models import ExternalAccountantAccount, AccountantInvitation, InvitationStatus
from apps.accounts.serializers import BusinessAccountMinimalSerializer
from apps.users.models import Role, SystemRole, UserRole

User = get_user_model()


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

        # Get external accountant role
        external_accountant_role = Role.objects.get(name=SystemRole.EXTERNAL_ACCOUNTANT)
        
        # Assign external accountant role to user
        UserRole.objects.create(
            user=user,
            role=external_accountant_role,
            system_role=SystemRole.EXTERNAL_ACCOUNTANT
        )

        # Create external accountant account
        accountant_data['user'] = user
        external_accountant = ExternalAccountantAccount.objects.create(**accountant_data)
        
        return {
            'user': user,
            'external_accountant': external_accountant
        }


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
            'id', 
            'sent_date', 
            'expiry_date', 
            'status', 
            'status_display',
            'is_expired',
            'created_by_name',
            'recipient_details',
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
                'company_name': obj.recipient.company_name,
            }
        return None
    
    def create(self, validated_data):
        # The sender must be a BusinessAccount
        # The created_by must be the user creating the invitation (authenticated user)
        # The expiry_date will be set automatically by the model method
        
        # These fields are set in the view
        sender = validated_data.pop('sender', None)
        created_by = validated_data.pop('created_by', None)
        
        return AccountantInvitation.objects.create(
            sender=sender,
            created_by=created_by,
            **validated_data
        ) 