from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Notification, NotificationPreference, NotificationType
from .serializers import NotificationSerializer, NotificationPreferenceSerializer


@swagger_auto_schema(tags=['Notifications'])
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Notification.objects.filter(user=self.request.user).order_by('-created_at')
        return Notification.objects.none()
    
    @swagger_auto_schema(
        operation_summary="Mark notification as read",
        responses={
            200: "Notification marked as read",
            404: "Notification not found"
        }
    )
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_as_read()
        return Response({
            'status': 'success',
            'message': 'Notification marked as read'
        })
    
    @swagger_auto_schema(
        operation_summary="Mark all notifications as read",
        responses={
            200: "All notifications marked as read"
        }
    )
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        unread_notifications = Notification.objects.filter(
            user=request.user,
            read=False
        )
        for notification in unread_notifications:
            notification.mark_as_read()
        
        return Response({
            'status': 'success',
            'message': f'{unread_notifications.count()} notifications marked as read'
        })


@swagger_auto_schema(tags=['Notifications'])
class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Check if user is authenticated before filtering
        if self.request.user.is_authenticated:
            return NotificationPreference.objects.filter(user=self.request.user)
        return NotificationPreference.objects.none()
    
    def list(self, request):
        if not request.user.is_authenticated:
            return Response({'detail': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        preference, created = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(preference)
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({'detail': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
            
        preference, created = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(preference, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
