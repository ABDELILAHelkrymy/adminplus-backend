from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password

from .models import User, Role, SystemRole, UserRole, PhoneOTP


class RoleNames:
    ADMIN = 'admin'
    ACCOUNTANT = 'accountant'
    CLIENT = 'client'


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ('id', 'name')


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    system_roles = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'is_active', 'roles', 'system_roles', 'created_at', 'is_verified')
    
    def get_roles(self, obj):
        return [role.name for role in obj.get_roles()]
    
    def get_system_roles(self, obj):
        # Dictionary to map system roles to their display names
        display_names = {
            SystemRole.ADMIN: "Administrator",
            SystemRole.INTERNAL_ACCOUNTANT: "Internal Accountant",
            SystemRole.EXTERNAL_ACCOUNTANT: "External Accountant",
            SystemRole.EMPLOYEE: "Employee",
            SystemRole.VIEWER: "Viewer"
        }
        
        return [
            {
                "name": user_role.system_role,
                "displayName": display_names.get(user_role.system_role, user_role.system_role.title())
            } 
            for user_role in obj.user_roles.all()
        ]


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
            is_verified=False
        )
        
        # Get role based on system_role
        role = Role.objects.get(name=system_role)
        
        # Assign role to user
        UserRole.objects.create(
            user=user,
            role=role,
            system_role=system_role
        )
        
        return user


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
        user = self.context.get('user')
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect.')
        return value


class EmailVerificationRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)


class EmailVerificationConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()


class OTPRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)


class OTPVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    otp = serializers.CharField(min_length=6, max_length=6)


class RegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone_number = serializers.CharField(required=False)
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return value
    
    def validate_password(self, value):
        validate_password(value)
        return value
    
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            phone_number=validated_data.get('phone_number'),
            is_active=True,
            is_verified=False
        )
        
        # Create business account for the user
        from apps.accounts.models import BusinessAccount
        BusinessAccount.objects.create(
            primary_user=user,
            name=f"{user.first_name}'s Business",
            email=user.email
        )
        
        # Assign the ADMIN role to the user
        admin_role = Role.objects.get(name=SystemRole.ADMIN)
        UserRole.objects.create(
            user=user,
            role=admin_role,
            system_role=SystemRole.ADMIN
        )
        
        return user 