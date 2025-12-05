from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from PIL import Image
import io
import traceback
import logging
from django.db import models
from decimal import Decimal, DecimalException, InvalidOperation
import os

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
    InvoiceEmailLog,
    Article,
    TimeEntry
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
    InvoiceEmailLogSerializer,
    ArticleSerializer,
    TimeEntrySerializer
)
from .utils import send_invoice_email, generate_invoice_email_content
from .invoice_parser import InvoiceParser

# Set up logger
logger = logging.getLogger(__name__)


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
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'reference_number']
    ordering_fields = ['name', 'status', 'created_at', 'budget', 'hourly_rate', 'start_date', 'end_date']
    filterset_fields = ['status', 'customer']

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

    @swagger_auto_schema(
        operation_summary="Start time tracking",
        operation_description="Start tracking time for this project",
        responses={200: TimeEntrySerializer()},
    )
    @action(detail=True, methods=['post'])
    def start_clock(self, request, pk=None):
        """Start time tracking for this project"""
        project = self.get_object()
        
        # Check if there's already an active time entry for this user in any project
        active_entries = TimeEntry.objects.filter(
            user=request.user,
            end_time__isnull=True
        )
        
        if active_entries.exists():
            # Stop the active time entry before starting a new one
            active_entry = active_entries.first()
            active_entry.end_time = timezone.now()
            active_entry.save()
            
            # Return warning with the new entry
            warning = f"Stopped active time entry for project '{active_entry.project.name}'"
        else:
            warning = None
        
        # Create a new time entry for this project
        time_entry = TimeEntry.objects.create(
            project=project,
            user=request.user,
            start_time=timezone.now(),
            description="Time tracking started" # Default description
        )
        
        serializer = TimeEntrySerializer(time_entry)
        response_data = serializer.data
        
        if warning:
            response_data['warning'] = warning
            
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    @swagger_auto_schema(
        operation_summary="Stop time tracking",
        operation_description="Stop active time tracking for this project",
        responses={200: TimeEntrySerializer()},
    )
    @action(detail=True, methods=['post'])
    def stop_clock(self, request, pk=None):
        """Stop time tracking for this project"""
        project = self.get_object()
        
        # Find active time entry for this user and project
        try:
            time_entry = TimeEntry.objects.get(
                user=request.user,
                project=project,
                end_time__isnull=True
            )
            
            # Set the end time
            time_entry.end_time = timezone.now()
            time_entry.save()
            
            serializer = TimeEntrySerializer(time_entry)
            return Response(serializer.data)
        except TimeEntry.DoesNotExist:
            return Response(
                {"error": "No active time tracking found for this project"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @swagger_auto_schema(
        operation_summary="Add manual time entry",
        operation_description="Add a manual time entry for this project",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['description', 'start_time', 'end_time'],
            properties={
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='Description of work done'),
                'start_time': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description='Start time'),
                'end_time': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description='End time'),
                'is_billable': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Whether this time is billable'),
            }
        ),
        responses={201: TimeEntrySerializer()},
    )
    @action(detail=True, methods=['post'])
    def add_time_entry(self, request, pk=None):
        """Add a manual time entry for this project"""
        project = self.get_object()
        
        # Validate required fields
        required_fields = ['description', 'start_time', 'end_time']
        for field in required_fields:
            if field not in request.data:
                return Response(
                    {"error": f"Field '{field}' is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Create the time entry
        time_entry_data = {
            'project': project,
            'user': request.user,
            'description': request.data.get('description'),
            'start_time': request.data.get('start_time'),
            'end_time': request.data.get('end_time'),
            'is_billable': request.data.get('is_billable', True)
        }
        
        time_entry = TimeEntry.objects.create(**time_entry_data)
        
        serializer = TimeEntrySerializer(time_entry)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @swagger_auto_schema(
        operation_summary="Get time entries",
        operation_description="Get all time entries for this project",
        responses={200: TimeEntrySerializer(many=True)},
    )
    @action(detail=True, methods=['get'])
    def time_entries(self, request, pk=None):
        """Get all time entries for this project"""
        project = self.get_object()
        
        # Filter by date range if provided
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        time_entries = project.time_entries.all()
        
        if start_date:
            time_entries = time_entries.filter(start_time__gte=start_date)
        
        if end_date:
            time_entries = time_entries.filter(end_time__lte=end_date)
        
        # Order by start_time descending (most recent first)
        time_entries = time_entries.order_by('-start_time')
        
        # Paginate the results
        page = self.paginate_queryset(time_entries)
        if page is not None:
            serializer = TimeEntrySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = TimeEntrySerializer(time_entries, many=True)
        return Response(serializer.data)


class ArticleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing articles
    """
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'article_number', 'description']
    ordering_fields = ['name', 'article_number', 'price', 'created_at']
    filterset_fields = ['article_number', 'is_active']

    def get_queryset(self):
        """Return articles for the user's business account"""
        if not self.request.user.is_authenticated:
            return Article.objects.none()
        
        # Get the business accounts the user has access to
        business_accounts = self.request.user.business_accounts.all()
        if hasattr(self.request.user, 'owned_business'):
            business_accounts = business_accounts | BusinessAccount.objects.filter(id=self.request.user.owned_business.id)
        
        return Article.objects.filter(business_account__in=business_accounts)
    
    def perform_create(self, serializer):
        """Set the business account when creating an article"""
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
    ordering_fields = ['date', 'due_date', 'created_at', 'total', 'status']
    filterset_fields = ['invoice_type', 'is_paid', 'status', 'sent', 'category', 'project', 'supplier', 'customer']

    def get_serializer_class(self):
        """Return different serializer for list and detail"""
        # if self.action == 'list':
        #     return InvoiceSerializer
        return InvoiceDetailSerializer

    def get_queryset(self):
        """Return invoices for the user's business account"""
        if not self.request.user.is_authenticated:
            return Invoice.objects.none()
        
        # Get the business accounts the user has access to
        business_accounts = self.request.user.business_accounts.all()
        if hasattr(self.request.user, 'owned_business'):
            business_accounts = business_accounts | BusinessAccount.objects.filter(id=self.request.user.owned_business.id)
        
        # Filter by invoice_type if specified in the query params
        queryset = Invoice.objects.filter(business_account__in=business_accounts)
        invoice_type = self.request.query_params.get('invoice_type', None)
        if invoice_type:
            queryset = queryset.filter(invoice_type=invoice_type)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set the business account when creating an invoice"""
        if hasattr(self.request.user, 'owned_business'):
            # Set invoice_type if it's in the query parameters but not the data
            if 'invoice_type' not in self.request.data and self.request.query_params.get('invoice_type'):
                serializer.save(
                    business_account=self.request.user.owned_business,
                    invoice_type=self.request.query_params.get('invoice_type')
                )
            else:
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
        responses={200: openapi.Response(description="Invoice marked as paid")},
    )
    @action(detail=True, methods=['post'])
    def mark_as_paid(self, request, pk=None):
        """Mark the invoice as paid"""
        invoice = self.get_object()
        invoice.mark_as_paid()
        return Response({"status": "Invoice marked as paid"}, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_summary="Get overdue invoices",
        operation_description="Get all overdue invoices for the user's business account",
        responses={200: openapi.Response(description="List of overdue invoices")},
    )
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get all overdue invoices"""
        today = timezone.now().date()
        queryset = self.get_queryset().filter(
            is_paid=False,
            due_date__lt=today
        )
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_summary="Send invoice by email",
        operation_description="Send the invoice to a specified email address",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['recipient'],
            properties={
                'recipient': openapi.Schema(type=openapi.TYPE_STRING, description='Email recipient'),
                'subject': openapi.Schema(type=openapi.TYPE_STRING, description='Email subject (optional)'),
                'body': openapi.Schema(type=openapi.TYPE_STRING, description='Email body (optional)'),
                'from_email': openapi.Schema(type=openapi.TYPE_STRING, description='Sender email (optional)'),
                'attach_pdf': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Whether to attach the PDF invoice (optional)'),
                'additional_attachments': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_FILE),
                    description='Additional files to attach to the email'
                ),
            }
        ),
        responses={200: openapi.Response(description="Invoice sent by email")},
    )
    @action(detail=True, methods=['post'])
    def send_email(self, request, pk=None):
        """Send the invoice by email"""
        invoice = self.get_object()
        
        # Validate required fields
        recipient = request.data.get('recipient')
        
        if not recipient:
            return Response(
                {"error": "Recipient email is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get optional fields with defaults
        subject = request.data.get('subject', f"{invoice.business_account.business_name}: Invoice {invoice.invoice_number}")
        
        # Generate default body if not provided
        if request.data.get('body'):
            body = request.data.get('body')
        else:
            # Generate email content from template
            body = generate_invoice_email_content(invoice)
        
        from_email = request.data.get('from_email')
        
        # Check if we should attach the PDF
        attach_pdf = request.data.get('attach_pdf', True)
        logger.info(f"Raw attach_pdf value: {attach_pdf}, type: {type(attach_pdf)}")
        
        # Handle different types of attach_pdf values
        if isinstance(attach_pdf, str):
            # Convert string 'true'/'false' to boolean
            attach_pdf = attach_pdf.lower() in ('true', 't', 'yes', 'y', '1')
        elif isinstance(attach_pdf, bool):
            # Keep as is if it's already a boolean
            pass
        else:
            # Default to True for any other value
            attach_pdf = bool(attach_pdf)
            
        logger.info(f"Processed attach_pdf value: {attach_pdf}")
        
        # Get additional attachments
        attachments = []
        if 'additional_attachments' in request.FILES:
            attachments = request.FILES.getlist('additional_attachments')
        
        # Check if PDF is available if attachment is requested
        if attach_pdf and invoice.generated_pdf:
            from django.core.files.storage import default_storage
            pdf_exists = False
            try:
                if hasattr(invoice.generated_pdf, 'path') and os.path.exists(invoice.generated_pdf.path):
                    pdf_exists = True
                    logger.info(f"PDF exists at path: {invoice.generated_pdf.path}")
                elif hasattr(invoice.generated_pdf, 'name'):
                    # Use the relative path (name) not the full URL or absolute path
                    pdf_path = invoice.generated_pdf.name
                    # Remove any leading slashes to ensure relative path
                    if pdf_path.startswith('/'):
                        pdf_path = pdf_path[1:]
                    
                    pdf_exists = default_storage.exists(pdf_path)
                    logger.info(f"PDF exists in storage with name: {pdf_path}, exists={pdf_exists}")
                
                if not pdf_exists:
                    logger.warning(f"PDF attachment requested but file does not exist")
            except Exception as e:
                logger.warning(f"Error checking PDF existence: {str(e)}")
        
        # Send the email
        try:
            logger.info(f"Sending email to {recipient} for invoice {invoice.invoice_number} with attach_pdf={attach_pdf}")
            
            email_success = send_invoice_email(
                invoice=invoice,
                recipient_email=recipient,
                subject=subject,
                content=body,
                from_email=from_email,
                attachments=attachments,
                attach_pdf=attach_pdf
            )
            
            if not email_success:
                # Check if the generated PDF file exists
                pdf_message = ""
                if invoice.generated_pdf:
                    try:
                        print(f"Checking if PDF file exists for invoice {invoice.id}")
                        if hasattr(invoice.generated_pdf, 'path'):
                            if os.path.exists(invoice.generated_pdf.path):
                                pdf_message = "PDF file exists but could not be attached."
                            else:
                                pdf_message = "PDF file path exists but file not found on disk."
                        elif default_storage.exists(invoice.generated_pdf.name):
                            pdf_message = "PDF file exists in storage but could not be attached."
                        else:
                            pdf_message = "PDF file reference exists but file not found in storage."
                    except Exception as e:
                        pdf_message = f"Error checking PDF file: {str(e)}"
                else:
                    pdf_message = "No PDF file has been generated for this invoice."
                
                logger.error(f"Email send failure details: {pdf_message}")
                
                return Response(
                    {
                        "error": "Failed to send email. Please check the logs for more details.",
                        "pdf_status": pdf_message
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
            # Create email log
            email_log = InvoiceEmailLog.objects.create(
                invoice=invoice,
                sent_by=request.user,
                recipient=recipient,
                subject=subject,
                body=body
            )
            
            # Update invoice sent status and timestamp
            invoice.sent = True
            invoice.sent_to = recipient
            invoice.sent_date = timezone.now()
            invoice.save()
            
            # Return success response with email log details
            email_log_serializer = InvoiceEmailLogSerializer(email_log)
            return Response({
                "status": "Invoice sent by email successfully",
                "email_log": email_log_serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Exception during email sending: {str(e)}")
            return Response(
                {
                    "error": f"Error during email sending: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    @swagger_auto_schema(
        operation_summary="Generate email content",
        operation_description="Generate default email content for sending the invoice",
        responses={200: openapi.Response(description="Generated email content")},
    )
    @action(detail=True, methods=['get'])
    def generate_email_content(self, request, pk=None):
        """Generate default email content for the invoice"""
        invoice = self.get_object()
        
        # First ensure the business account has an email
        if not invoice.business_account.email and hasattr(invoice.business_account, 'primary_user'):
            # Fill business email from primary user if missing
            invoice.business_account.email = invoice.business_account.primary_user.email
            invoice.business_account.save()
            logger.info(f"Updated business account email from primary user: {invoice.business_account.email}")
        
        # Generate content with template
        content = generate_invoice_email_content(invoice)
        
        # Prepare response data
        subject = f"{invoice.business_account.business_name}: Invoice {invoice.invoice_number}"
        recipient = ""
        
        # If this is a customer invoice, use customer email as recipient
        if invoice.customer and invoice.customer.email:
            recipient = invoice.customer.email
        
        response_data = {
            "subject": subject,
            "content": content,
            "recipient": recipient,
            "from_email": invoice.business_account.email,
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Parse invoice file",
        operation_description="Extract data from uploaded invoice file",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['file'],
            properties={
                'file': openapi.Schema(type=openapi.TYPE_FILE, description='Invoice file (PDF, JPG, PNG)'),
            }
        ),
        responses={200: openapi.Response(description="Extracted data from invoice")},
    )
    @action(detail=False, methods=['post'])
    def parse_invoice(self, request):
        """
        Extract data from uploaded invoice file
        """
        try:
            if 'file' not in request.FILES:
                return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
            
            invoice_file = request.FILES['file']
            
            # Use the new InvoiceParser.parse_invoice method that switches between regex and GPT parser
            try:
                extracted_data = InvoiceParser.parse_invoice(invoice_file)
                return Response(extracted_data, status=status.HTTP_200_OK)
            except ValueError as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Invoice parsing error: {str(e)}\n{traceback.format_exc()}")
            return Response(
                {"error": f"Failed to parse invoice: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='save_pdf')
    def save_pdf(self, request, pk=None):
        """Save a PDF file to the invoice (either generated PDF or original document)"""
        invoice = self.get_object()
        
        # Check if either file type is provided
        if 'generated_pdf' not in request.FILES and 'original_document' not in request.FILES:
            return Response(
                {"error": "No file provided. Either 'generated_pdf' or 'original_document' must be included."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Determine which file type is being saved
            file_field = 'generated_pdf' if 'generated_pdf' in request.FILES else 'original_document'
            pdf_file = request.FILES[file_field]
            
            # Check if it's a PDF
            if not pdf_file.name.lower().endswith('.pdf') and not pdf_file.content_type == 'application/pdf':
                logger.warning(f"File may not be a PDF: name={pdf_file.name}, content_type={pdf_file.content_type}")
                # We'll still try to save it, but log the warning
            
            # Log the filename for debugging
            logger.info(f"Saving {file_field} file: {pdf_file.name} for invoice ID: {invoice.id}, size: {pdf_file.size} bytes, content_type: {pdf_file.content_type}")
            
            # Get explicit document_type parameter if provided
            document_type = request.data.get('document_type', file_field)
            logger.info(f"Document type from request: {document_type}, defaulting to: {file_field}")
            
            # Use the explicit document_type if different from the file field
            if document_type != file_field and document_type in ['generated_pdf', 'original_document']:
                logger.info(f"Using explicit document_type '{document_type}' instead of file field '{file_field}'")
                file_field = document_type
            
            # Ensure the file has a proper extension and includes invoice ID
            prefix = "invoice" if file_field == "generated_pdf" else "original"
            if not pdf_file.name.lower().endswith('.pdf'):
                original_name = pdf_file.name
                pdf_file.name = f"{prefix}_{invoice.invoice_number}_{invoice.id}.pdf"
                logger.info(f"Renamed file from {original_name} to {pdf_file.name}")
            elif not pdf_file.name.lower().endswith(f"_{invoice.id}.pdf"):
                original_name = pdf_file.name
                base_name = pdf_file.name[:-4]  # Remove .pdf extension
                pdf_file.name = f"{base_name}_{invoice.id}.pdf"
                logger.info(f"Added invoice ID to file name: {original_name} → {pdf_file.name}")
            
            # Read the file content to ensure it's readable
            file_content = pdf_file.read()
            pdf_file.seek(0)  # Reset file pointer
            
            logger.info(f"Successfully read {len(file_content)} bytes from uploaded file")
            
            # Get the current field value before setting the new value
            old_value = getattr(invoice, file_field)
            if old_value:
                logger.info(f"Current {file_field} value: {old_value.name}")
            else:
                logger.info(f"No current {file_field} value (null)")
            
            # Set the file to the appropriate invoice field
            if file_field == 'generated_pdf':
                invoice.generated_pdf = pdf_file
            else:
                invoice.original_document = pdf_file
                
            # Force save to ensure the database is updated
            invoice.save(update_fields=[file_field])
            
            # Reload the invoice to verify changes
            invoice.refresh_from_db()
            new_value = getattr(invoice, file_field)
            if new_value:
                logger.info(f"Updated {file_field} value: {new_value.name}")
            else:
                logger.warning(f"Updated {file_field} is still null after save!")
            
            # Try to directly access the file to verify it was saved correctly
            try:
                from django.core.files.storage import default_storage
                # Get the path without any leading slashes
                stored_file = getattr(invoice, file_field)
                if not stored_file:
                    logger.error(f"Field {file_field} is null after save!")
                    return Response(
                        {"error": f"Failed to save {file_field}. Field is null after save."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                    
                storage_path = stored_file.name
                if storage_path.startswith('/'):
                    storage_path = storage_path[1:]
                    
                if default_storage.exists(storage_path):
                    logger.info(f"File verified in storage: {storage_path}")
                    
                    # Try to read it back
                    with default_storage.open(storage_path, 'rb') as f:
                        content = f.read()
                        logger.info(f"Successfully verified file content ({len(content)} bytes)")
                else:
                    logger.warning(f"File not found in storage immediately after save: {storage_path}")
            except Exception as verify_error:
                logger.warning(f"Error verifying saved file: {str(verify_error)}")
            
            # Return success response with the file name
            return Response({
                "status": f"{file_field.replace('_', ' ').title()} saved successfully",
                "invoice_id": invoice.id,
                "filename": pdf_file.name,
                "file_size": pdf_file.size,
                "file_type": file_field,
                "storage_path": stored_file.name if stored_file else None
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error saving file to invoice: {str(e)}\n{traceback.format_exc()}")
            return Response(
                {"error": f"Failed to save file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_summary="Parse expenditure invoice file",
        operation_description="Extract data from uploaded expenditure invoice file and prepare for supplier processing",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['file'],
            properties={
                'file': openapi.Schema(type=openapi.TYPE_FILE, description='Expenditure invoice file (PDF, JPG, PNG)'),
            }
        ),
        responses={200: openapi.Response(description="Extracted data from expenditure invoice")},
    )
    @action(detail=False, methods=['post'], url_path='parse-expenditure-invoice')
    def parse_expenditure_invoice(self, request):
        """
        Extract data from uploaded expenditure invoice file specifically for expenditure invoices
        """
        try:
            # Check dependencies
            is_tesseract_installed, is_poppler_installed = InvoiceParser.check_dependencies()
            
            if not is_tesseract_installed or not is_poppler_installed:
                # Get installation instructions
                instructions = InvoiceParser.get_dependency_installation_instructions()
                
                error_message = []
                if not is_tesseract_installed:
                    error_message.append("Tesseract OCR is not installed or not in your PATH.")
                if not is_poppler_installed:
                    error_message.append("Poppler is not installed or not in your PATH.")
                
                return Response({
                    "error": " ".join(error_message) + " Please install the required dependencies.",
                    "installation_instructions": instructions
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
            if 'file' not in request.FILES:
                return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
            
            invoice_file = request.FILES['file']
            
            # Use the InvoiceParser class to extract text and data
            try:
                extracted_data = InvoiceParser.parse_invoice(invoice_file)
                # Try to find supplier based on extracted data if user has a business account
                if hasattr(request.user, 'owned_business'):
                    business_account = request.user.owned_business
                    
                    # Get supplier name from ICE number
                    supplier_info = extracted_data.get('supplier_info', {}) or {}
                    supplier_ice = supplier_info.get('ice')
                    supplier_name = str(supplier_ice).strip() if supplier_ice else ''
                    
                    suppliers = Supplier.objects.filter(
                        business_account=business_account,
                        ice_number=supplier_name
                    )
                    if suppliers.exists():
                        extracted_data['supplier_id'] = suppliers.first().id
                
                # Get customer name from ICE number
                customer_info = extracted_data.get('customer_info', {}) or {}
                customer_ice = customer_info.get('ice')
                customer_name = str(customer_ice).strip() if customer_ice else ''
                
                return Response(extracted_data, status=status.HTTP_200_OK)
                
            except ValueError as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Expenditure invoice parsing error: {str(e)}\n{traceback.format_exc()}")
            return Response(
                {"error": f"Failed to parse expenditure invoice: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_summary="Batch parse expenditure invoice files",
        operation_description="Extract data from multiple uploaded expenditure invoice files (max 20 files)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['files'],
            properties={
                'files': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_FILE),
                    description='Expenditure invoice files (PDF, JPG, PNG) - max 20 files'
                ),
            }
        ),
        responses={
            200: openapi.Response(description="Array of extracted data from expenditure invoices"),
            400: openapi.Response(description="Invalid request (too many files or missing files)"),
        },
    )
    @action(detail=False, methods=['post'], url_path='batch-parse-expenditure-invoices')
    def batch_parse_expenditure_invoices(self, request):
        """
        Extract data from multiple uploaded expenditure invoice files
        Maximum 20 files per batch
        Returns array with success/error status for each file
        """
        try:
            # Check dependencies
            is_tesseract_installed, is_poppler_installed = InvoiceParser.check_dependencies()
            
            if not is_tesseract_installed or not is_poppler_installed:
                instructions = InvoiceParser.get_dependency_installation_instructions()
                error_message = []
                if not is_tesseract_installed:
                    error_message.append("Tesseract OCR is not installed or not in your PATH.")
                if not is_poppler_installed:
                    error_message.append("Poppler is not installed or not in your PATH.")
                
                return Response({
                    "error": " ".join(error_message) + " Please install the required dependencies.",
                    "installation_instructions": instructions
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Get files from request
            files = request.FILES.getlist('files')
            
            if not files:
                return Response(
                    {"error": "No files provided"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if len(files) > 20:
                return Response(
                    {"error": "Maximum 20 files allowed per batch"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            results = []
            business_account = None
            if hasattr(request.user, 'owned_business'):
                business_account = request.user.owned_business
            
            # Process each file
            for invoice_file in files:
                try:
                    # Parse the invoice
                    extracted_data = InvoiceParser.parse_invoice(invoice_file)
                    
                    # Try to find supplier if business account exists
                    if business_account:
                        supplier_info = extracted_data.get('supplier_info', {}) or {}
                        supplier_ice = supplier_info.get('ice')
                        supplier_name = str(supplier_ice).strip() if supplier_ice else ''
                        
                        suppliers = Supplier.objects.filter(
                            business_account=business_account,
                            ice_number=supplier_name
                        )
                        if suppliers.exists():
                            extracted_data['supplier_id'] = suppliers.first().id
                    
                    results.append({
                        "success": True,
                        "filename": invoice_file.name,
                        "data": extracted_data
                    })
                    
                except ValueError as e:
                    results.append({
                        "success": False,
                        "filename": invoice_file.name,
                        "error": str(e)
                    })
                except Exception as e:
                    logger.error(f"Error parsing file {invoice_file.name}: {str(e)}\n{traceback.format_exc()}")
                    results.append({
                        "success": False,
                        "filename": invoice_file.name,
                        "error": f"Failed to parse invoice: {str(e)}"
                    })
            
            return Response(results, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Batch parse error: {str(e)}\n{traceback.format_exc()}")
            return Response(
                {"error": f"Failed to process batch: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_summary="Batch create expenditure invoices",
        operation_description="Create multiple expenditure invoices from array of invoice data",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['invoices'],
            properties={
                'invoices': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_OBJECT),
                    description='Array of invoice data objects'
                ),
            }
        ),
        responses={
            207: openapi.Response(description="Multi-Status - Array with success/error status for each invoice"),
            400: openapi.Response(description="Invalid request"),
        },
    )
    @action(detail=False, methods=['post'], url_path='batch-create-expenditure-invoices')
    def batch_create_expenditure_invoices(self, request):
        """
        Create multiple expenditure invoices from array of invoice data
        Returns HTTP 207 Multi-Status with individual results for each invoice
        """
        try:
            invoices_data = request.data.get('invoices', [])
            
            if not invoices_data:
                return Response(
                    {"error": "No invoices data provided"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not isinstance(invoices_data, list):
                return Response(
                    {"error": "Invoices data must be an array"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            results = []
            
            # Process each invoice
            for idx, invoice_data in enumerate(invoices_data):
                try:
                    # Add business account if user has one
                    if hasattr(request.user, 'owned_business'):
                        invoice_data['business_account'] = request.user.owned_business.id
                    
                    # Ensure invoice_type is set
                    if 'invoice_type' not in invoice_data:
                        invoice_data['invoice_type'] = 'purchase'
                    
                    # Create the invoice
                    serializer = InvoiceSerializer(data=invoice_data, context={'request': request})
                    
                    if serializer.is_valid():
                        invoice = serializer.save()
                        results.append({
                            "success": True,
                            "invoice_id": invoice.id,
                            "invoice_number": invoice.invoice_number_ref,
                            "data": InvoiceSerializer(invoice).data
                        })
                    else:
                        results.append({
                            "success": False,
                            "index": idx,
                            "errors": serializer.errors
                        })
                        
                except Exception as e:
                    logger.error(f"Error creating invoice at index {idx}: {str(e)}\n{traceback.format_exc()}")
                    results.append({
                        "success": False,
                        "index": idx,
                        "error": str(e)
                    })
            
            # Return 207 Multi-Status
            return Response(results, status=status.HTTP_207_MULTI_STATUS)
            
        except Exception as e:
            logger.error(f"Batch create error: {str(e)}\n{traceback.format_exc()}")
            return Response(
                {"error": f"Failed to process batch: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # This method is no longer needed as we're using the InvoiceParser class
    # Keeping it here commented out for reference
    # def _extract_invoice_data(self, text):
    #    pass


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
        
    @swagger_auto_schema(
        operation_summary="Get available articles",
        operation_description="Retrieve a list of articles that can be used in invoice line items",
        responses={200: openapi.Response(description="List of available articles")},
    )
    @action(detail=False, methods=['get'])
    def available_articles(self, request, invoice_pk=None):
        """
        Retrieve a list of available articles that can be used in invoice line items
        """
        # Get the invoice first to determine business account
        try:
            invoice = Invoice.objects.get(id=invoice_pk)
            
            # Get articles for this business account
            articles = Article.objects.filter(
                business_account=invoice.business_account,
                is_active=True
            )
            
            # Apply search filter if provided
            search_query = request.query_params.get('search', None)
            if search_query:
                articles = articles.filter(
                    models.Q(name__icontains=search_query) | 
                    models.Q(article_number__icontains=search_query) |
                    models.Q(description__icontains=search_query)
                )

                
            # Paginate the results
            page = self.paginate_queryset(articles)
            if page is not None:
                serializer = ArticleSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
                
            serializer = ArticleSerializer(articles, many=True)
            return Response(serializer.data)
            
        except Invoice.DoesNotExist:
            return Response(
                {"error": "Invoice not found"},
                status=status.HTTP_404_NOT_FOUND
            )


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


class TimeEntryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing time entries
    """
    serializer_class = TimeEntrySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['description']
    ordering_fields = ['start_time', 'end_time', 'duration_minutes', 'created_at']
    filterset_fields = ['project', 'user', 'is_billable', 'billed']
    
    def get_queryset(self):
        """Return time entries for projects the user has access to"""
        if not self.request.user.is_authenticated:
            return TimeEntry.objects.none()
        
        # Get the business accounts the user has access to
        business_accounts = self.request.user.business_accounts.all()
        if hasattr(self.request.user, 'owned_business'):
            business_accounts = business_accounts | BusinessAccount.objects.filter(id=self.request.user.owned_business.id)
        
        # Get projects for these business accounts
        projects = Project.objects.filter(business_account__in=business_accounts)
        
        # Return time entries for these projects
        return TimeEntry.objects.filter(project__in=projects)
    
    def perform_create(self, serializer):
        """Set the user when creating a time entry"""
        serializer.save(user=self.request.user)
    
    @swagger_auto_schema(
        operation_summary="Stop active time entry",
        operation_description="Stop the currently active time entry for the authenticated user",
        responses={200: TimeEntrySerializer()},
    )
    @action(detail=False, methods=['post'])
    def stop_active(self, request):
        """Stop the currently active time entry for the authenticated user"""
        try:
            time_entry = TimeEntry.objects.get(
                user=request.user,
                end_time__isnull=True
            )
            
            # Set the end time
            time_entry.end_time = timezone.now()
            time_entry.save()
            
            serializer = TimeEntrySerializer(time_entry)
            return Response(serializer.data)
        except TimeEntry.DoesNotExist:
            return Response(
                {"error": "No active time tracking found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @swagger_auto_schema(
        operation_summary="Get active time entry",
        operation_description="Get the currently active time entry for the authenticated user if any",
        responses={200: TimeEntrySerializer()},
    )
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get the currently active time entry for the authenticated user if any"""
        try:
            time_entry = TimeEntry.objects.get(
                user=request.user,
                end_time__isnull=True
            )
            
            serializer = TimeEntrySerializer(time_entry)
            return Response(serializer.data)
        except TimeEntry.DoesNotExist:
            return Response(
                {"active": False},
                status=status.HTTP_200_OK
            )
    
    @swagger_auto_schema(
        operation_summary="Generate invoice from time entries",
        operation_description="Create an invoice from selected time entries",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['customer_id', 'time_entry_ids'],
            properties={
                'customer_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Customer ID'),
                'time_entry_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_INTEGER),
                    description='List of time entry IDs to include in invoice'
                ),
            }
        ),
        responses={201: InvoiceSerializer()},
    )
    @action(detail=False, methods=['post'])
    def create_invoice(self, request):
        """Create an invoice from selected time entries"""
        customer_id = request.data.get('customer_id')
        time_entry_ids = request.data.get('time_entry_ids', [])
        
        if not customer_id or not time_entry_ids:
            return Response(
                {"error": "Customer ID and time entry IDs are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            customer = Customer.objects.get(id=customer_id)
            time_entries = TimeEntry.objects.filter(id__in=time_entry_ids)
            
            if not time_entries:
                return Response(
                    {"error": "No valid time entries found"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Group time entries by project to ensure they're for the same customer
            projects = set(entry.project for entry in time_entries)
            project = projects.pop() if len(projects) == 1 else None
            
            # Create invoice
            from datetime import datetime
            invoice = Invoice.objects.create(
                business_account=customer.business_account,
                invoice_type='sele',
                invoice_number=f"INV-{datetime.now().strftime('%Y%m%d')}-{customer.number}",
                customer=customer,
                project=project,
                date=timezone.now().date(),
                due_date=(timezone.now() + timezone.timedelta(days=30)).date(),
                currency='EUR'  # Default to EUR based on screenshots
            )
            
            # Add line items for each time entry
            for time_entry in time_entries:
                # Create line item for this time entry
                InvoiceLineItem.objects.create(
                    invoice=invoice,
                    description=f"{time_entry.description or 'Time entry'} - {time_entry.hours:.2f} hours",
                    quantity=Decimal(str(time_entry.hours)),
                    price=time_entry.project.hourly_rate,
                    unit='hours'
                )
                
                # Mark time entry as billed
                time_entry.billed = True
                time_entry.invoice = invoice
                time_entry.save()
            
            # Calculate invoice totals
            invoice.calculate_totals()
            
            serializer = InvoiceSerializer(invoice)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Customer.DoesNotExist:
            return Response(
                {"error": "Customer not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to create invoice: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


try:
    from pdf2image import convert_from_bytes
    # Test if poppler is installed
    test_pdf_bytes = b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%EOF"
    convert_from_bytes(test_pdf_bytes, size=1)
except Exception as e:
    # Handle Poppler not installed/configured properly
    poppler_error = str(e)
