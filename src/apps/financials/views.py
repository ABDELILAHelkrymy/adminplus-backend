from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Sum
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import (
    TransactionCategory, FinancialAccount, 
    Transaction, RecurringTransaction,
    TransactionStatus, TransactionType
)
from .serializers import (
    TransactionCategorySerializer, FinancialAccountSerializer,
    TransactionSerializer, RecurringTransactionSerializer
)
from apps.accounts.models import BusinessAccount
from apps.users.permissions import IsBusinessOwner


@swagger_auto_schema(tags=['Financials - Categories'])
class TransactionCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionCategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Check if this is a schema generation request
        if getattr(self, 'swagger_fake_view', False):
            return TransactionCategory.objects.none()
        
        # Check if user is authenticated
        if not self.request.user.is_authenticated:
            return TransactionCategory.objects.none()
        
        # Show system categories to everyone
        queryset = TransactionCategory.objects.filter(is_system=True)
        
        try:
            # Get business-specific categories if the user has a business account
            business_account = BusinessAccount.objects.get(primary_user=self.request.user)
            custom_categories = TransactionCategory.objects.filter(
                business_account=business_account,
                is_system=False
            )
            return queryset.union(custom_categories)
        except BusinessAccount.DoesNotExist:
            return queryset
    
    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            return Response({
                'status': 'error',
                'message': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            business_account = BusinessAccount.objects.get(primary_user=self.request.user)
            serializer.save(
                business_account=business_account,
                is_system=False
            )
        except BusinessAccount.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Business account not found'
            }, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(tags=['Financials - Accounts'])
class FinancialAccountViewSet(viewsets.ModelViewSet):
    serializer_class = FinancialAccountSerializer
    permission_classes = [IsAuthenticated, IsBusinessOwner]
    
    def get_queryset(self):
        # Check if this is a schema generation request
        if getattr(self, 'swagger_fake_view', False):
            return FinancialAccount.objects.none()
        
        # Check if user is authenticated
        if not self.request.user.is_authenticated:
            return FinancialAccount.objects.none()
        
        try:
            business_account = BusinessAccount.objects.get(primary_user=self.request.user)
            return FinancialAccount.objects.filter(business_account=business_account)
        except BusinessAccount.DoesNotExist:
            return FinancialAccount.objects.none()
    
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


@swagger_auto_schema(tags=['Financials - Transactions'])
class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated, IsBusinessOwner]
    
    def get_queryset(self):
        # Check if this is a schema generation request
        if getattr(self, 'swagger_fake_view', False):
            return Transaction.objects.none()
            
        # Check if user is authenticated
        if not self.request.user.is_authenticated:
            return Transaction.objects.none()
            
        try:
            business_account = BusinessAccount.objects.get(primary_user=self.request.user)
            return Transaction.objects.filter(business_account=business_account)
        except BusinessAccount.DoesNotExist:
            return Transaction.objects.none()
    
    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            return Response({
                'status': 'error',
                'message': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
            
        try:
            business_account = BusinessAccount.objects.get(primary_user=self.request.user)
            serializer.save(
                business_account=business_account,
                status=TransactionStatus.PENDING
            )
        except BusinessAccount.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Business account not found'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_id="transaction_update_status",
        operation_summary="Update transaction status",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=[status[0] for status in TransactionStatus.choices]
                ),
            }
        ),
        responses={
            200: TransactionSerializer,
            400: "Invalid status",
            404: "Transaction not found"
        }
    )
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        transaction = self.get_object()
        status_value = request.data.get('status')
        
        if status_value not in dict(TransactionStatus.choices):
            return Response({
                'status': 'error',
                'message': 'Invalid transaction status'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        transaction.status = status_value
        transaction.save()
        
        serializer = self.get_serializer(transaction)
        return Response(serializer.data)


@swagger_auto_schema(tags=['Financials - Recurring Transactions'])
class RecurringTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = RecurringTransactionSerializer
    permission_classes = [IsAuthenticated, IsBusinessOwner]
    
    def get_queryset(self):
        # Check if this is a schema generation request
        if getattr(self, 'swagger_fake_view', False):
            return RecurringTransaction.objects.none()
            
        # Check if user is authenticated
        if not self.request.user.is_authenticated:
            return RecurringTransaction.objects.none()
            
        try:
            business_account = BusinessAccount.objects.get(primary_user=self.request.user)
            return RecurringTransaction.objects.filter(business_account=business_account)
        except BusinessAccount.DoesNotExist:
            return RecurringTransaction.objects.none()
    
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
        operation_id="recurring_transaction_generate",
        operation_summary="Generate upcoming transactions",
        responses={
            200: "Transactions generated successfully",
            404: "Recurring transaction not found"
        }
    )
    @action(detail=True, methods=['post'])
    def generate_transactions(self, request, pk=None):
        recurring = self.get_object()
        
        # Generate the next transaction(s)
        generated = recurring.generate_upcoming_transactions(max_transactions=1)
        
        return Response({
            'status': 'success',
            'message': f'Generated {len(generated)} transaction(s)',
            'transactions': TransactionSerializer(generated, many=True).data
        })
