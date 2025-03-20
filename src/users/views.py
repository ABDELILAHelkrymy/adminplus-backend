# views.py
from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Q
from .models import User, Role, AccountantClientRelationship
from .serializers import (
    UserSerializer, AccountantClientRelationshipSerializer,
    RoleSerializer
)
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from .serializers import LoginSerializer, TokenSerializer, TokenRefreshSerializer, ClientProfileUpdateSerializer, UserClientRegistrationSerializer

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class RoleNames:
    ADMIN = 'admin'
    ACCOUNTANT = 'accountant'
    CLIENT = 'client'

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role and request.user.role.name == RoleNames.ADMIN


class IsAccountant(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role and request.user.role.name == RoleNames.ACCOUNTANT


class IsClient(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role and request.user.role.name == RoleNames.CLIENT


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
        print(request.data)
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
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        refresh = RefreshToken(serializer.validated_data['refresh'])
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        })
    
# class UserRegistrationView(generics.CreateAPIView):
#     queryset = User.objects.all()
#     serializer_class = UserRegistrationSerializer
#     permission_classes = [IsAdmin | IsAccountant]

#     def perform_create(self, serializer):
#         user = serializer.save()
#         if self.request.user.role.name == RoleNames.ACCOUNTANT:
#             # Automatically associate the client with the accountant
#             AccountantClientRelationship.objects.create(
#                 accountant=self.request.user,
#                 client=user,
#                 status='pending'
#             )

#     @swagger_auto_schema(
#         operation_description="Register a new user",
#         responses={
#             201: UserSerializer,
#             400: "Bad Request - Invalid data"
#         },
#         security=[],
#         tags=['Authentication']
#     )
#     def post(self, request, *args, **kwargs):
#         return super().post(request, *args, **kwargs)


# --------------------------
#  USER REGISTRATION VIEWSET
# --------------------------
@swagger_auto_schema(tags=['Users'])
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserClientRegistrationSerializer
    http_method_names = ['post']

    @action(detail=False, methods=['post'], url_path='register')
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"message": "User registered successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# @swagger_auto_schema(tags=['Users'])
# class UserViewSet(viewsets.ModelViewSet):
#     serializer_class = UserSerializer

#     def get_queryset(self):
#         # Handle schema generation for Swagger
#         if getattr(self, 'swagger_fake_view', False):
#             return User.objects.none()

#         user = self.request.user
        
#         # Safely check if the user has a role
#         if not getattr(user, 'role', None):
#             return User.objects.none()
        
#         # Filter users based on user role
#         if user.role.name == RoleNames.ACCOUNTANT:
#             return User.objects.filter(
#                 Q(id=user.id) | Q(accountantclientrelationship__accountant=user, accountantclientrelationship__status='active'))
#         elif user.role.name == RoleNames.CLIENT:
#             return User.objects.filter(
#             Q(id=user.id) | Q(accountantclientrelationship__client=user, accountantclientrelationship__status='active'))
#         else:
#             return User.objects.all()

    
#     def get_permissions(self):
#         if self.action == 'create':
#             permission_classes = [IsAdmin | IsAccountant]
#         elif self.action in ['update', 'partial_update', 'destroy']:
#             permission_classes = [IsAdmin]
#         else:
#             permission_classes = [permissions.IsAuthenticated]
#         return [permission() for permission in permission_classes]


# --------------------------
#  CLIENT PROFILE UPDATE VIEW
# --------------------------
@swagger_auto_schema(tags=['Users'])
class ClientProfileUpdateView(generics.UpdateAPIView):
    serializer_class = ClientProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.profile
    

# --------------------------
#  ACCOUNTANT-CLIENT RELATIONSHIP VIEWSET
# --------------------------
@swagger_auto_schema(tags=['Client-Accountant Relationships'])
class AccountantClientRelationshipViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """List pending client requests for the logged-in accountant."""
        requests = AccountantClientRelationship.objects.filter(accountant=request.user, status='pending')
        serializer = AccountantClientRelationshipSerializer(requests, many=True)
        return Response(serializer.data)

    def update(self, request, pk=None):
        """Accept or reject a client request."""
        try:
            relationship = AccountantClientRelationship.objects.get(id=pk, accountant=request.user, status='pending')
        except AccountantClientRelationship.DoesNotExist:
            return Response({"error": "Request not found or already processed"}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action')
        if action not in ['accept', 'reject']:
            return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

        relationship.status = 'active' if action == 'accept' else 'rejected'
        relationship.save()
        return Response({"message": f"Request {action}ed successfully"})
    

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
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        relationship = self.get_object()
        
        # Only clients can accept invitations from accountants
        if not request.user.role or request.user.role.name != 'client' or request.user.id != relationship.client.id:
            return Response({"detail": "Only clients can accept accountant invitations"},
                        status=status.HTTP_403_FORBIDDEN)
        
        # Check if the relationship is already active
        if relationship.status == 'active':
            return Response({"detail": "This relationship is already active."},
                        status=status.HTTP_400_BAD_REQUEST)
        
        # Check if the relationship is in a valid state to be accepted
        if relationship.status != 'pending':
            return Response({"detail": "Only pending relationships can be accepted."},
                        status=status.HTTP_400_BAD_REQUEST)
        
        # Update the relationship status to 'active'
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
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        relationship = self.get_object()
        
        # Only clients can reject invitations from accountants
        if not request.user.role or request.user.role.name != 'client' or request.user.id != relationship.client.id:
            return Response({"detail": "Only clients can reject accountant invitations"},
                        status=status.HTTP_403_FORBIDDEN)
        
        # Check if the relationship is already rejected
        if relationship.status == 'rejected':
            return Response({"detail": "This relationship is already rejected."},
                        status=status.HTTP_400_BAD_REQUEST)
        
        # Check if the relationship is in a valid state to be rejected
        if relationship.status != 'pending':
            return Response({"detail": "Only pending relationships can be rejected."},
                        status=status.HTTP_400_BAD_REQUEST)
        
        # Update the relationship status to 'rejected'
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
    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        relationship = self.get_object()
        
        # Only clients can set primary accountants
        if not request.user.role or request.user.role.name != 'client' or request.user.id != relationship.client.id:
            return Response({"detail": "Only clients can set their primary accountant"},
                        status=status.HTTP_403_FORBIDDEN)
        
        # Check if the relationship is already primary
        if relationship.is_primary:
            return Response({"detail": "This accountant is already your primary accountant."},
                        status=status.HTTP_400_BAD_REQUEST)
        
        # Check if the relationship is active
        if relationship.status != 'active':
            return Response({"detail": "Only active relationships can be set as primary."},
                        status=status.HTTP_400_BAD_REQUEST)
        
        # Clear other primary relationships
        AccountantClientRelationship.objects.filter(
            client=relationship.client, is_primary=True
        ).update(is_primary=False)
        
        # Set the current relationship as primary
        relationship.is_primary = True
        relationship.save()
        
        serializer = self.get_serializer(relationship)
        return Response(serializer.data)