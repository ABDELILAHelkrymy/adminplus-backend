from django.shortcuts import render
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.accounts.models import BusinessAccount
from .models import (
    Supplier,
    Customer,
    Category,
    PaymentMethod,
    Project,
    Invoice,
    InvoiceLineItem,
    InvoiceAttachment,
    InvoiceEmailLog
)
from .serializers import (
    SupplierSerializer,
    CustomerSerializer,
    CategorySerializer,
    PaymentMethodSerializer,
    ProjectSerializer,
    InvoiceSerializer,
    InvoiceDetailSerializer,
    InvoiceLineItemSerializer,
    InvoiceAttachmentSerializer,
    InvoiceEmailLogSerializer
)


class SupplierViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing suppliers
    """
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['corporate_name', 'first_name', 'last_name', 'email', 'telephone', 'mobile']
    ordering_fields = ['corporate_name', 'created_at']
    filterset_fields = ['country', 'is_small_business']

    def get_queryset(self):
        """Return suppliers for the user's business account"""
        if not self.request.user.is_authenticated:
            return Supplier.objects.none()
        
        # Get the business accounts the user has access to
        business_accounts = self.request.user.business_accounts.all()
        if hasattr(self.request.user, 'owned_business'):
            business_accounts = business_accounts | BusinessAccount.objects.filter(id=self.request.user.owned_business.id)
        
        return Supplier.objects.filter(business_account__in=business_accounts)
    
    def perform_create(self, serializer):
        """Set the business account when creating a supplier"""
        if hasattr(self.request.user, 'owned_business'):
            serializer.save(business_account=self.request.user.owned_business)
        else:
            # Handle case where user doesn't have a business account
            return Response(
                {"error": "User does not have a business account"},
                status=status.HTTP_400_BAD_REQUEST
            )


class CustomerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing customers
    """
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['corporate_name', 'first_name', 'last_name', 'email', 'telephone', 'mobile']
    ordering_fields = ['corporate_name', 'created_at']
    filterset_fields = ['country', 'is_small_business']

    def get_queryset(self):
        """Return customers for the user's business account"""
        if not self.request.user.is_authenticated:
            return Customer.objects.none()
        
        # Get the business accounts the user has access to
        business_accounts = self.request.user.business_accounts.all()
        if hasattr(self.request.user, 'owned_business'):
            business_accounts = business_accounts | BusinessAccount.objects.filter(id=self.request.user.owned_business.id)
        
        return Customer.objects.filter(business_account__in=business_accounts)
    
    def perform_create(self, serializer):
        """Set the business account when creating a customer"""
        if hasattr(self.request.user, 'owned_business'):
            serializer.save(business_account=self.request.user.owned_business)
        else:
            # Handle case where user doesn't have a business account
            return Response(
                {"error": "User does not have a business account"},
                status=status.HTTP_400_BAD_REQUEST
            )


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing invoice categories
    """
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        """Return categories for the user's business account"""
        if not self.request.user.is_authenticated:
            return Category.objects.none()
        
        # Get the business accounts the user has access to
        business_accounts = self.request.user.business_accounts.all()
        if hasattr(self.request.user, 'owned_business'):
            business_accounts = business_accounts | BusinessAccount.objects.filter(id=self.request.user.owned_business.id)
        
        return Category.objects.filter(business_account__in=business_accounts)
    
    def perform_create(self, serializer):
        """Set the business account when creating a category"""
        if hasattr(self.request.user, 'owned_business'):
            serializer.save(business_account=self.request.user.owned_business)
        else:
            # Handle case where user doesn't have a business account
            return Response(
                {"error": "User does not have a business account"},
                status=status.HTTP_400_BAD_REQUEST
            )


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing payment methods
    """
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        """Return payment methods for the user's business account"""
        if not self.request.user.is_authenticated:
            return PaymentMethod.objects.none()
        
        # Get the business accounts the user has access to
        business_accounts = self.request.user.business_accounts.all()
        if hasattr(self.request.user, 'owned_business'):
            business_accounts = business_accounts | BusinessAccount.objects.filter(id=self.request.user.owned_business.id)
        
        return PaymentMethod.objects.filter(business_account__in=business_accounts)
    
    def perform_create(self, serializer):
        """Set the business account when creating a payment method"""
        if hasattr(self.request.user, 'owned_business'):
            serializer.save(business_account=self.request.user.owned_business)
        else:
            # Handle case where user doesn't have a business account
            return Response(
                {"error": "User does not have a business account"},
                status=status.HTTP_400_BAD_REQUEST
            )


class ProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing projects
    """
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        """Return projects for the user's business account"""
        if not self.request.user.is_authenticated:
            return Project.objects.none()
        
        # Get the business accounts the user has access to
        business_accounts = self.request.user.business_accounts.all()
        if hasattr(self.request.user, 'owned_business'):
            business_accounts = business_accounts | BusinessAccount.objects.filter(id=self.request.user.owned_business.id)
        
        return Project.objects.filter(business_account__in=business_accounts)
    
    def perform_create(self, serializer):
        """Set the business account when creating a project"""
        if hasattr(self.request.user, 'owned_business'):
            serializer.save(business_account=self.request.user.owned_business)
        else:
            # Handle case where user doesn't have a business account
            return Response(
                {"error": "User does not have a business account"},
                status=status.HTTP_400_BAD_REQUEST
            )


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing invoices
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['invoice_number', 'reference', 'supplier__corporate_name', 'customer__corporate_name']
    ordering_fields = ['date', 'due_date', 'created_at', 'total']
    filterset_fields = ['invoice_type', 'is_paid', 'category', 'project', 'supplier', 'customer']

    def get_serializer_class(self):
        """Return different serializer for list and detail"""
        if self.action == 'list':
            return InvoiceSerializer
        return InvoiceDetailSerializer

    def get_queryset(self):
        """Return invoices for the user's business account"""
        if not self.request.user.is_authenticated:
            return Invoice.objects.none()
        
        # Get the business accounts the user has access to
        business_accounts = self.request.user.business_accounts.all()
        if hasattr(self.request.user, 'owned_business'):
            business_accounts = business_accounts | BusinessAccount.objects.filter(id=self.request.user.owned_business.id)
        
        return Invoice.objects.filter(business_account__in=business_accounts)
    
    def perform_create(self, serializer):
        """Set the business account when creating an invoice"""
        if hasattr(self.request.user, 'owned_business'):
            serializer.save(business_account=self.request.user.owned_business)
        else:
            # Handle case where user doesn't have a business account
            return Response(
                {"error": "User does not have a business account"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @swagger_auto_schema(
        operation_summary="Mark an invoice as paid",
        operation_description="Mark the invoice as paid with the current date",
        responses={200: openapi.Response("Invoice marked as paid")},
    )
    @action(detail=True, methods=['post'])
    def mark_as_paid(self, request, pk=None):
        """Mark the invoice as paid"""
        invoice = self.get_object()
        invoice.mark_as_paid()
        return Response({"status": "Invoice marked as paid"}, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_summary="Send invoice by email",
        operation_description="Send the invoice to a specified email address",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['recipient', 'subject', 'body'],
            properties={
                'recipient': openapi.Schema(type=openapi.TYPE_STRING, description='Email recipient'),
                'subject': openapi.Schema(type=openapi.TYPE_STRING, description='Email subject'),
                'body': openapi.Schema(type=openapi.TYPE_STRING, description='Email body'),
            }
        ),
        responses={200: openapi.Response("Invoice sent by email")},
    )
    @action(detail=True, methods=['post'])
    def send_email(self, request, pk=None):
        """Send the invoice by email"""
        invoice = self.get_object()
        
        # Validate required fields
        recipient = request.data.get('recipient')
        subject = request.data.get('subject')
        body = request.data.get('body')
        
        if not all([recipient, subject, body]):
            return Response(
                {"error": "Recipient, subject, and body are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create email log
        email_log = InvoiceEmailLog.objects.create(
            invoice=invoice,
            sent_by=request.user,
            recipient=recipient,
            subject=subject,
            body=body
        )
        
        # TODO: Actual email sending logic would go here
        
        # Update invoice sent status
        invoice.sent = True
        invoice.save()
        
        return Response({"status": "Invoice sent by email"}, status=status.HTTP_200_OK)


class InvoiceLineItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing invoice line items
    """
    serializer_class = InvoiceLineItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return line items for the specified invoice"""
        invoice_id = self.kwargs.get('invoice_pk')
        if not invoice_id:
            return InvoiceLineItem.objects.none()
        
        return InvoiceLineItem.objects.filter(invoice_id=invoice_id)
    
    def perform_create(self, serializer):
        """Set the invoice when creating a line item"""
        invoice_id = self.kwargs.get('invoice_pk')
        invoice = Invoice.objects.get(id=invoice_id)
        serializer.save(invoice=invoice)


class InvoiceAttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing invoice attachments
    """
    serializer_class = InvoiceAttachmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return attachments for the specified invoice"""
        invoice_id = self.kwargs.get('invoice_pk')
        if not invoice_id:
            return InvoiceAttachment.objects.none()
        
        return InvoiceAttachment.objects.filter(invoice_id=invoice_id)
    
    def perform_create(self, serializer):
        """Set the invoice when creating an attachment"""
        invoice_id = self.kwargs.get('invoice_pk')
        invoice = Invoice.objects.get(id=invoice_id)
        serializer.save(invoice=invoice)
