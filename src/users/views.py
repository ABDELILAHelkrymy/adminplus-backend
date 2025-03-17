# views.py
from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Q
from .models import User, Role, AccountantClientRelationship
from .serializers import (
    UserSerializer, UserRegistrationSerializer, AccountantClientRelationshipSerializer,
    RoleSerializer
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from .serializers import LoginSerializer, TokenSerializer, TokenRefreshSerializer

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role and request.user.role.name == 'admin'


class IsAccountant(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role and request.user.role.name == 'accountant'


class IsClient(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role and request.user.role.name == 'client'


class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]

@swagger_auto_schema(tags=['Authentication'])
class LoginView(generics.GenericAPIView):
    """
    Authenticate a user and obtain JWT token.
    
    Returns user details and JWT tokens for authentication.
    Access token should be included in the Authorization header as 'Bearer <token>'
    for subsequent requests.
    """
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        """
        Log in with email and password to receive JWT tokens.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }
        })
@swagger_auto_schema(tags=['Authentication'])
class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = TokenRefreshSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        refresh = RefreshToken(serializer.validated_data['refresh'])
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        })
    
class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_description="Register a new user",
        responses={
            201: UserSerializer,
            400: "Bad Request - Invalid data"
        },
        security=[],
        tags=['Authentication']
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@swagger_auto_schema(tags=['Users'])
class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.role:
            return User.objects.none()
        
        if user.role.name == 'admin':
            return User.objects.all()
        elif user.role.name == 'accountant':
            # Accountants can see themselves and their clients
            client_ids = AccountantClientRelationship.objects.filter(
                accountant=user, status='active'
            ).values_list('client_id', flat=True)
            return User.objects.filter(Q(id=user.id) | Q(id__in=client_ids))
        else:  # client
            # Clients can see themselves and their accountants
            accountant_ids = AccountantClientRelationship.objects.filter(
                client=user, status='active'
            ).values_list('accountant_id', flat=True)
            return User.objects.filter(Q(id=user.id) | Q(id__in=accountant_ids))
    
    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [IsAdmin | IsAccountant]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]


class AccountantClientRelationshipViewSet(viewsets.ModelViewSet):
    serializer_class = AccountantClientRelationshipSerializer

    """
    API endpoints for managing accountant-client relationships.
    
    list:
    Return a list of all relationships visible to the authenticated user.
    
    create:
    Create a new relationship. Only accountants can create relationships.
    
    retrieve:
    Return the details of a specific relationship.
    
    update:
    Update all fields of a relationship. Only accountants and admins can update.
    
    partial_update:
    Update some fields of a relationship. Only accountants and admins can update.
    
    destroy:
    Delete a relationship. Only admins can delete relationships.
    """

    def get_queryset(self):
        # Handle schema generation for Swagger
        if getattr(self, 'swagger_fake_view', False):
            return AccountantClientRelationship.objects.none()

        user = self.request.user
        
        # Safely check if the user has a role
        if not getattr(user, 'role', None):
            return AccountantClientRelationship.objects.none()
        
        # Filter relationships based on user role
        if user.role.name == 'admin':
            return AccountantClientRelationship.objects.all()
        elif user.role.name == 'accountant':
            return AccountantClientRelationship.objects.filter(accountant=user)
        else:  # client
            return AccountantClientRelationship.objects.filter(client=user)
    
    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [IsAccountant]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [IsAccountant | IsAdmin]
        elif self.action == 'destroy':
            permission_classes = [IsAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    @swagger_auto_schema(
        operation_description="Accept an accountant invitation. Only clients can accept invitations.",
        responses={
            200: AccountantClientRelationshipSerializer,
            403: "Forbidden - Not authorized to accept this invitation"
        },
        tags=['Client-Accountant Relationships']
    )
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        relationship = self.get_object()
        
        # Only clients can accept invitations from accountants
        if not request.user.role or request.user.role.name != 'client' or request.user.id != relationship.client.id:
            return Response({"detail": "Only clients can accept accountant invitations"},
                          status=status.HTTP_403_FORBIDDEN)
        
        relationship.status = 'active'
        relationship.save()
        
        serializer = self.get_serializer(relationship)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Reject an accountant invitation. Only clients can reject invitations.",
        responses={
            200: AccountantClientRelationshipSerializer,
            403: "Forbidden - Not authorized to reject this invitation"
        },
        tags=['Client-Accountant Relationships']
    )
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        relationship = self.get_object()
        
        # Only clients can reject invitations from accountants
        if not request.user.role or request.user.role.name != 'client' or request.user.id != relationship.client.id:
            return Response({"detail": "Only clients can reject accountant invitations"},
                          status=status.HTTP_403_FORBIDDEN)
        
        relationship.status = 'rejected'
        relationship.save()
        
        serializer = self.get_serializer(relationship)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Set a primary accountant. Only clients can set their primary accountant.",
        responses={
            200: AccountantClientRelationshipSerializer,
            403: "Forbidden - Not authorized to set primary accountant"
        },
        tags=['Client-Accountant Relationships']
    )
    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        relationship = self.get_object()
        
        # Only clients can set primary accountants
        if not request.user.role or request.user.role.name != 'client' or request.user.id != relationship.client.id:
            return Response({"detail": "Only clients can set their primary accountant"},
                          status=status.HTTP_403_FORBIDDEN)
        
        # Clear other primary relationships
        AccountantClientRelationship.objects.filter(
            client=relationship.client, is_primary=True
        ).update(is_primary=False)
        
        relationship.is_primary = True
        relationship.save()
        
        serializer = self.get_serializer(relationship)
        return Response(serializer.data)