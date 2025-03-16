# serializers.py
from rest_framework import serializers
from .models import User, Role, AccountantClientRelationship, UserProfile
from django.db import transaction
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken


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


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    profile = UserProfileSerializer(required=False)
    accountant_email = serializers.EmailField(required=False, write_only=True)
    role_name = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('email', 'password', 'confirm_password', 'first_name', 'last_name', 
                  'role_name', 'phone_number', 'address', 'company_name', 'profile', 
                  'accountant_email')
    
    def validate(self, data):
        if data['password'] != data.pop('confirm_password'):
            raise serializers.ValidationError("Passwords do not match")
        
        # Get role by name
        role_name = data.pop('role_name')
        try:
            role = Role.objects.get(name=role_name)
            data['role'] = role
        except Role.DoesNotExist:
            raise serializers.ValidationError(f"Role '{role_name}' does not exist")
        
        # Check if accountant exists when a client registers with accountant email
        if role.name == 'client' and 'accountant_email' in data and data['accountant_email']:
            try:
                accountant_role = Role.objects.get(name='accountant')
                accountant = User.objects.get(email=data['accountant_email'], role=accountant_role)
            except (User.DoesNotExist, Role.DoesNotExist):
                raise serializers.ValidationError("Accountant with this email does not exist")
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        accountant_email = validated_data.pop('accountant_email', None)
        profile_data = validated_data.pop('profile', None)
        
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            **{k: v for k, v in validated_data.items() if k != 'password'}
        )
        
        if profile_data:
            UserProfile.objects.create(user=user, **profile_data)
        else:
            UserProfile.objects.create(user=user)
        
        # If client is registering and provided accountant email, create relationship
        if user.role and user.role.name == 'client' and accountant_email:
            try:
                accountant_role = Role.objects.get(name='accountant')
                accountant = User.objects.get(email=accountant_email, role=accountant_role)
                AccountantClientRelationship.objects.create(
                    accountant=accountant,
                    client=user,
                    status='pending'
                )
            except (User.DoesNotExist, Role.DoesNotExist):
                pass  # This was validated earlier
        
        return user


class AccountantClientRelationshipSerializer(serializers.ModelSerializer):
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