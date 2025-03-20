# serializers.py
from rest_framework import serializers
from .models import User, Role, AccountantClientRelationship, UserProfile
from django.db import transaction
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.password_validation import validate_password

class RoleNames:
    ADMIN = 'admin'
    ACCOUNTANT = 'accountant'
    CLIENT = 'client'

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ('id', 'name')


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('profile_picture', 'tax_number', 'business_type', 'currency', 'language')

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(style={'input_type': 'password'})

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if email and password:
            from django.contrib.auth import authenticate
            user = authenticate(request=self.context.get('request'),
                                email=email, password=password)
            if not user:
                msg = 'Unable to log in with provided credentials.'
                raise serializers.ValidationError(msg, code='authorization')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
        else:
            msg = 'Must include "email" and "password".'
            raise serializers.ValidationError(msg, code='authorization')

        data['user'] = user
        return data

class TokenSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()

class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    
class UserSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.name', read_only=True)
    profile = UserProfileSerializer(required=False)
    
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'role', 'role_name', 
                  'phone_number', 'address', 'company_name', 'is_verified', 
                  'profile', 'created_at')
        read_only_fields = ('id', 'is_verified', 'created_at')

def validate_password(self, value):
    validate_password(value)
    return value

# --------------------------
#  USER REGISTRATION SERIALIZER
# --------------------------
class UserClientRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password', 'confirm_password', 'phone_number', 'address', 'company_name']

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords must match."})
        return data

    @transaction.atomic
    def create(self, validated_data):
        role = Role.objects.get(name=RoleNames.CLIENT)
        validated_data.pop('confirm_password')  # Remove confirm_password before saving
        user = User.objects.create_user(role=role, **validated_data)
        return user


class ClientProfileUpdateSerializer(serializers.ModelSerializer):
    accountant_email = serializers.EmailField(write_only=True, required=False)

    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'tax_number', 'business_type', 'currency', 'language', 'accountant_email']

    def update(self, instance, validated_data):
        accountant_email = validated_data.pop('accountant_email', None)
        user = instance.user  # The client user

        # Update profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If the client provided an accountant email, create a relationship request
        if accountant_email:
            try:
                accountant = User.objects.get(email=accountant_email)
                AccountantClientRelationship.objects.get_or_create(
                    accountant=accountant, 
                    client=user,
                    defaults={'status': 'pending'}
                )
            except User.DoesNotExist:
                raise serializers.ValidationError({"accountant_email": "No accountant found with this email."})

        return instance


class AccountantClientRelationshipSerializer(serializers.ModelSerializer):
    client_email = serializers.EmailField(write_only=True, required=False)
    client = UserSerializer(read_only=True)
    accountant = UserSerializer(read_only=True)
    
    class Meta:
        model = AccountantClientRelationship
        fields = ('id', 'accountant', 'client', 'client_email', 'is_primary', 'status', 'created_at')
        read_only_fields = ('id', 'created_at')
    
    def validate(self, data):
        client_email = data.get('client_email')
        accountant = self.context['request'].user
        
        if not accountant.role or accountant.role.name != RoleNames.ACCOUNTANT:
            raise serializers.ValidationError({"accountant": "Only accountants can create relationships"})
        
        try:
            client_role = Role.objects.get(name=RoleNames.CLIENT)
            client = User.objects.get(email=client_email, role=client_role)
        except (User.DoesNotExist, Role.DoesNotExist):
            raise serializers.ValidationError({"client_email": "Client with this email does not exist"})
        
        if client.id == accountant.id:
            raise serializers.ValidationError({"client_email": "An accountant cannot create a relationship with themselves"})
        
        return data
    
    def create(self, validated_data):
        client_email = validated_data.pop('client_email')
        accountant = self.context['request'].user
        
        try:
            client_role = Role.objects.get(name=RoleNames.CLIENT)
            client = User.objects.get(email=client_email, role=client_role)
        except (User.DoesNotExist, Role.DoesNotExist):
            raise serializers.ValidationError({"client_email": "Client with this email does not exist"})
        
        # Check if relationship already exists
        existing = AccountantClientRelationship.objects.filter(accountant=accountant, client=client).first()
        if existing:
            if existing.status == 'rejected':
                existing.status = 'pending'
                existing.save()
                return existing
            return existing
        
        # If this is marked as primary, clear other primary relationships
        if validated_data.get('is_primary', False):
            AccountantClientRelationship.objects.filter(client=client, is_primary=True).update(is_primary=False)
        
        relationship = AccountantClientRelationship.objects.create(
            accountant=accountant,
            client=client,
            **validated_data
        )
        
        return relationship
    client_email = serializers.EmailField(write_only=True, required=False)
    client = UserSerializer(read_only=True)
    accountant = UserSerializer(read_only=True)
    
    class Meta:
        model = AccountantClientRelationship
        fields = ('id', 'accountant', 'client', 'client_email', 'is_primary', 'status', 'created_at')
        read_only_fields = ('id', 'created_at')
    
    def create(self, validated_data):
        client_email = validated_data.pop('client_email', None)
        accountant = self.context['request'].user
        
        if not accountant.role or accountant.role.name != 'accountant':
            raise serializers.ValidationError("Only accountants can create relationships")
        
        try:
            client_role = Role.objects.get(name='client')
            client = User.objects.get(email=client_email, role=client_role)
        except (User.DoesNotExist, Role.DoesNotExist):
            raise serializers.ValidationError("Client with this email does not exist")
        
        # Check if relationship already exists
        existing = AccountantClientRelationship.objects.filter(accountant=accountant, client=client).first()
        if existing:
            if existing.status == 'rejected':
                existing.status = 'pending'
                existing.save()
                return existing
            return existing
        
        # If this is marked as primary, clear other primary relationships
        if validated_data.get('is_primary', False):
            AccountantClientRelationship.objects.filter(client=client, is_primary=True).update(is_primary=False)
        
        relationship = AccountantClientRelationship.objects.create(
            accountant=accountant,
            client=client,
            **validated_data
        )
        
        return relationship