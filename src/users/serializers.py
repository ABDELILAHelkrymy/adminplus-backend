from rest_framework import serializers
from .models import User, Permission, RolePermission, AccountantClient

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Permission, RolePermission, AccountantClient

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'role', 'is_active', 'is_staff', 'created_at', 'updated_at']
        read_only_fields = ['id', 'is_staff', 'created_at', 'updated_at']

class UserCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'password', 'first_name', 'last_name', 'role']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User.objects.create_user(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user
    
class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name']

class RolePermissionSerializer(serializers.ModelSerializer):
    permission_name = serializers.CharField(source='permission.name', read_only=True)

    class Meta:
        model = RolePermission
        fields = ['id', 'role', 'permission', 'permission_name']

class AccountantClientSerializer(serializers.ModelSerializer):
    accountant_username = serializers.CharField(source='accountant.username', read_only=True)
    client_username = serializers.CharField(source='client.username', read_only=True)

    class Meta:
        model = AccountantClient
        fields = ['id', 'accountant', 'client', 'accountant_username', 'client_username']
