from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import ClientAccountantConnection, DataSharingPreference, ConnectionAccessLevel, ConnectionActivity
from .serializers import ClientAccountantConnectionSerializer, DataSharingPreferenceSerializer


@swagger_auto_schema(tags=['Connections - Accountant'])
class ClientAccountantConnectionViewSet(viewsets.ModelViewSet):
    serializer_class = ClientAccountantConnectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Check if this is a schema generation request
        if getattr(self, 'swagger_fake_view', False):
            return ClientAccountantConnection.objects.none()
            
        # Check if user is authenticated
        if not self.request.user.is_authenticated:
            return ClientAccountantConnection.objects.none()
            
        user = self.request.user
        if hasattr(user, 'owned_business'):
            # Business owners see their connections
            return ClientAccountantConnection.objects.filter(client=user.owned_business)
        elif hasattr(user, 'accountant_account'):
            # Accountants see connections where they are the accountant
            return ClientAccountantConnection.objects.filter(accountant=user.accountant_account)
        return ClientAccountantConnection.objects.none()

    @swagger_auto_schema(
        operation_id="connection_update_access",
        operation_summary="Update connection access level",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'access_level': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=[level[0] for level in ConnectionAccessLevel.choices]
                ),
            }
        ),
        responses={
            200: ClientAccountantConnectionSerializer,
            400: "Invalid access level",
            404: "Connection not found"
        }
    )
    @action(detail=True, methods=['patch'])
    def update_access(self, request, pk=None):
        connection = self.get_object()
        access_level = request.data.get('access_level')
        
        if access_level not in dict(ConnectionAccessLevel.choices):
            return Response({
                'status': 'error',
                'message': 'Invalid access level'
            }, status=status.HTTP_400_BAD_REQUEST)

        connection.update_access_level(access_level)
        serializer = self.get_serializer(connection)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_id="connection_update_sharing",
        operation_summary="Update data sharing preferences",
        request_body=DataSharingPreferenceSerializer,
        responses={
            200: ClientAccountantConnectionSerializer,
            400: "Invalid data",
            404: "Connection not found"
        }
    )
    @action(detail=True, methods=['patch'])
    def update_sharing(self, request, pk=None):
        connection = self.get_object()
        serializer = DataSharingPreferenceSerializer(
            connection.data_sharing,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            connection_serializer = self.get_serializer(connection)
            return Response(connection_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_id="connection_deactivate",
        operation_summary="Deactivate connection",
        responses={
            200: "Connection deactivated successfully",
            404: "Connection not found"
        }
    )
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        connection = self.get_object()
        connection.manage_connection_status(False)
        
        # Log the activity
        ConnectionActivity.log_activity(
            connection=connection,
            user=request.user,
            action_type='connection_deactivated',
            description='Connection deactivated by user'
        )
        
        return Response({
            'status': 'success',
            'message': 'Connection deactivated successfully'
        })

    @swagger_auto_schema(
        operation_id="connection_reactivate",
        operation_summary="Reactivate connection",
        responses={
            200: "Connection reactivated successfully",
            404: "Connection not found"
        }
    )
    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        connection = self.get_object()
        connection.manage_connection_status(True)
        
        # Log the activity
        ConnectionActivity.log_activity(
            connection=connection,
            user=request.user,
            action_type='connection_reactivated',
            description='Connection reactivated by user'
        )
        
        return Response({
            'status': 'success',
            'message': 'Connection reactivated successfully'
        })
