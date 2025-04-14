from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Integration, IntegrationEvent
from .serializers import IntegrationSerializer, IntegrationEventSerializer
from apps.accounts.models import BusinessAccount
from apps.users.permissions import IsBusinessOwner


@swagger_auto_schema(tags=['Integrations - General'])
class IntegrationViewSet(viewsets.ModelViewSet):
    serializer_class = IntegrationSerializer
    permission_classes = [IsAuthenticated, IsBusinessOwner]
    
    def get_queryset(self):
        # Check if this is a schema generation request
        if getattr(self, 'swagger_fake_view', False):
            return Integration.objects.none()
            
        # Check if user is authenticated
        if not self.request.user.is_authenticated:
            return Integration.objects.none()
            
        try:
            business_account = BusinessAccount.objects.get(primary_user=self.request.user)
            return Integration.objects.filter(business_account=business_account)
        except BusinessAccount.DoesNotExist:
            return Integration.objects.none()
    
    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            return Response({
                'status': 'error',
                'message': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
            
        try:
            business_account = BusinessAccount.objects.get(primary_user=self.request.user)
            serializer.save(business_account=business_account)
        except BusinessAccount.DoesNotExist:
            return Response({
                'status': 'error', 
                'message': 'Business account not found'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_id="integration_sync",
        operation_summary="Sync integration data",
        responses={
            200: "Integration synced successfully",
            404: "Integration not found"
        }
    )
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        integration = self.get_object()
        
        # In a real application, this would trigger the integration's sync process
        # For now, we just update the last_sync timestamp
        integration.update_sync_status()
        
        return Response({
            'status': 'success',
            'message': 'Integration synced successfully'
        })
    
    @swagger_auto_schema(
        operation_id="integration_toggle_status",
        operation_summary="Toggle integration status",
        responses={
            200: "Integration status updated",
            404: "Integration not found"
        }
    )
    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        integration = self.get_object()
        integration.is_active = not integration.is_active
        integration.save()
        
        return Response({
            'status': 'success',
            'message': f'Integration {"activated" if integration.is_active else "deactivated"} successfully',
            'is_active': integration.is_active
        })


@swagger_auto_schema(tags=['Integrations - Events'])
class IntegrationEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IntegrationEventSerializer
    permission_classes = [IsAuthenticated, IsBusinessOwner]
    
    def get_queryset(self):
        # Check if this is a schema generation request
        if getattr(self, 'swagger_fake_view', False):
            return IntegrationEvent.objects.none()
            
        # Check if user is authenticated
        if not self.request.user.is_authenticated:
            return IntegrationEvent.objects.none()
            
        try:
            business_account = BusinessAccount.objects.get(primary_user=self.request.user)
            return IntegrationEvent.objects.filter(
                integration__business_account=business_account
            ).order_by('-timestamp')
        except BusinessAccount.DoesNotExist:
            return IntegrationEvent.objects.none()
    
    @swagger_auto_schema(
        operation_id="integration_event_mark_processed",
        operation_summary="Mark event as processed",
        responses={
            200: "Event marked as processed",
            404: "Event not found"
        }
    )
    @action(detail=True, methods=['post'])
    def mark_processed(self, request, pk=None):
        event = self.get_object()
        event.mark_as_processed()
        
        return Response({
            'status': 'success',
            'message': 'Event marked as processed'
        })
