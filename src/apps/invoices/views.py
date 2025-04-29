from django.shortcuts import render
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import pytesseract
from PIL import Image
import pandas as pd
from pdf2image import convert_from_bytes
import re
import io
import traceback
from django.db import models
from decimal import Decimal, DecimalException, InvalidOperation

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
    Article
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
    ArticleSerializer
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
        responses={200: openapi.Response(description="Invoice sent by email")},
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
            file_extension = invoice_file.name.split('.')[-1].lower()
            
            # Extract text based on file type
            if file_extension == 'pdf':
                # Convert PDF to images
                images = convert_from_bytes(invoice_file.read())
                text = ""
                for img in images:
                    img_byte_array = io.BytesIO()
                    img.save(img_byte_array, format='PNG')
                    img_byte_array.seek(0)
                    text += pytesseract.image_to_string(Image.open(img_byte_array))
            elif file_extension in ['jpg', 'jpeg', 'png']:
                text = pytesseract.image_to_string(Image.open(invoice_file))
            else:
                return Response(
                    {"error": "Unsupported file format. Please upload PDF, JPG, or PNG."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Extract information from the text
            extracted_data = self._extract_invoice_data(text)
            
            return Response(extracted_data, status=status.HTTP_200_OK)
        except Exception as e:
            print(traceback.format_exc())
            return Response(
                {"error": f"Failed to parse invoice: {str(e)}"},
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
            # Check if Tesseract is installed
            try:
                import pytesseract
                pytesseract.get_tesseract_version()
            except (ImportError, pytesseract.TesseractNotFoundError):
                return Response({
                    "error": "Tesseract OCR is not installed or not in your PATH. Please install Tesseract OCR and make sure it's in your PATH.",
                    "installation_instructions": {
                        "windows": "1. Download and install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki\n2. Add the Tesseract installation directory to your PATH environment variable",
                        "linux": "sudo apt-get install tesseract-ocr",
                        "mac": "brew install tesseract"
                    }
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
            if 'file' not in request.FILES:
                return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
            
            invoice_file = request.FILES['file']
            file_extension = invoice_file.name.split('.')[-1].lower()
            
            # Extract text based on file type
            if file_extension == 'pdf':
                try:
                    # Convert PDF to images
                    images = convert_from_bytes(invoice_file.read())
                    text = ""
                    for img in images:
                        img_byte_array = io.BytesIO()
                        img.save(img_byte_array, format='PNG')
                        img_byte_array.seek(0)
                        text += pytesseract.image_to_string(Image.open(img_byte_array))
                except Exception as e:
                    # If pdf2image fails, we might need poppler
                    return Response({
                        "error": f"Error processing PDF file: {str(e)}",
                        "installation_instructions": {
                            "windows": "1. Download and install Poppler from https://github.com/oschwartz10612/poppler-windows/releases\n2. Add the Poppler bin directory to your PATH environment variable",
                            "linux": "sudo apt-get install poppler-utils",
                            "mac": "brew install poppler"
                        }
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            elif file_extension in ['jpg', 'jpeg', 'png']:
                text = pytesseract.image_to_string(Image.open(invoice_file))
            else:
                return Response(
                    {"error": "Unsupported file format. Please upload PDF, JPG, or PNG."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Extract information from the text, specifically for expenditure invoices
            extracted_data = self._extract_expenditure_invoice_data(text)
            
            # Save the uploaded file for reference
            if hasattr(request.user, 'owned_business'):
                business_account = request.user.owned_business
                
                # Try to find supplier based on extracted data
                supplier_name = extracted_data.get('supplier_info', {}).get('name', '').strip()
                if supplier_name:
                    suppliers = Supplier.objects.filter(
                        business_account=business_account,
                        corporate_name__icontains=supplier_name
                    )
                    if suppliers.exists():
                        extracted_data['supplier_id'] = suppliers.first().id
            
            return Response(extracted_data, status=status.HTTP_200_OK)
        except Exception as e:
            print(traceback.format_exc())
            return Response(
                {"error": f"Failed to parse expenditure invoice: {str(e)}",
                 "possible_solution": "If the error is related to Tesseract, please install it and ensure it's in your PATH."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _extract_expenditure_invoice_data(self, text):
        """
        Extract structured data from expenditure invoice text
        Specifically tailored for expenditure invoices from suppliers
        """
        # Default empty data
        data = {
            "invoice_number": "",
            "date": "",
            "supplier_info": {
                "name": "",
                "tax_id": "",
                "address": ""
            },
            "line_items": [],
            "subtotal": Decimal('0.0'),
            "tax_amount": Decimal('0.0'),
            "total": Decimal('0.0'),
            "invoice_type": "purchase"  # Default to purchase for expenditure invoices
        }
        
        # Extract invoice number
        invoice_number_match = re.search(r'invoice\s*(?:#|no|number|num)[:\s]*([0-9a-zA-Z\-_/]+)', text, re.IGNORECASE)
        if invoice_number_match:
            data["invoice_number"] = invoice_number_match.group(1).strip()
        
        # Extract date
        date_match = re.search(r'date[:\s]*([\d]{1,2}[-/\.][\d]{1,2}[-/\.][\d]{2,4})', text, re.IGNORECASE)
        if date_match:
            data["date"] = date_match.group(1).strip()
        
        # Extract supplier name
        supplier_match = re.search(r'(from|vendor|supplier|bill\s*from)[:\s]*([A-Za-z0-9\s.,]+)', text, re.IGNORECASE)
        if supplier_match:
            data["supplier_info"]["name"] = supplier_match.group(2).strip()
        else:
            # Try alternative patterns that might indicate supplier info
            alt_supplier_match = re.search(r'^([A-Za-z0-9\s.,]+)\s*\n', text)
            if alt_supplier_match:
                data["supplier_info"]["name"] = alt_supplier_match.group(1).strip()
        
        # Extract supplier tax ID
        tax_id_match = re.search(r'(tax\s*id|vat\s*number|ico|ice)[:\s]*([A-Za-z0-9\s.,]+)', text, re.IGNORECASE)
        if tax_id_match:
            data["supplier_info"]["tax_id"] = tax_id_match.group(2).strip()
        
        # Extract address - look for common address indicators
        address_match = re.search(r'(address|location)[:\s]*([A-Za-z0-9\s.,\-]+(?:\n[A-Za-z0-9\s.,\-]+){0,3})', text, re.IGNORECASE)
        if address_match:
            data["supplier_info"]["address"] = address_match.group(2).strip()
        
        # Extract line items - this is more complex and depends on invoice format
        # Here's a simple approach that looks for patterns that might be line items
        lines = text.split('\n')
        line_items = []
        
        for i, line in enumerate(lines):
            # Look for lines with quantity, description and price patterns
            qty_match = re.search(r'^[\s]*(\d+\.?\d*)', line)
            price_match = re.search(r'(\d+\.?\d*)$', line)
            
            if qty_match and price_match and i+1 < len(lines):
                try:
                    quantity = Decimal(qty_match.group(1))
                    price = Decimal(price_match.group(1))
                    # Description is likely on the next line or between qty and price
                    desc_part = line[len(qty_match.group(0)):line.rfind(price_match.group(0))]
                    if not desc_part.strip():
                        desc_part = lines[i+1]
                    
                    line_items.append({
                        "description": desc_part.strip(),
                        "quantity": quantity,
                        "price": price,
                        "unit": "ea"  # Default unit
                    })
                except (ValueError, InvalidOperation, DecimalException):
                    # Skip this line if there's an error converting to Decimal
                    continue
        
        data["line_items"] = line_items
        
        # Extract totals
        total_match = re.search(r'(total)[:\s]*[$€£]?(\d+\.?\d*)', text, re.IGNORECASE)
        if total_match:
            try:
                data["total"] = Decimal(total_match.group(2))
            except (ValueError, InvalidOperation, DecimalException):
                # Keep default value if conversion fails
                pass
        
        subtotal_match = re.search(r'(subtotal|sub-total|net)[:\s]*[$€£]?(\d+\.?\d*)', text, re.IGNORECASE)
        if subtotal_match:
            try:
                data["subtotal"] = Decimal(subtotal_match.group(2))
            except (ValueError, InvalidOperation, DecimalException):
                # Keep default value if conversion fails
                pass
        
        tax_match = re.search(r'(tax|vat|gst)[:\s]*[$€£]?(\d+\.?\d*)', text, re.IGNORECASE)
        if tax_match:
            try:
                data["tax_amount"] = Decimal(tax_match.group(2))
            except (ValueError, InvalidOperation, DecimalException):
                # Keep default value if conversion fails
                pass
        
        return data

    def _extract_invoice_data(self, text):
        """
        Extract structured data from invoice text
        """
        # Default empty data
        data = {
            "invoice_number": "",
            "date": "",
            "supplier_info": {
                "name": "",
                "tax_id": "",
                "address": ""
            },
            "line_items": [],
            "subtotal": Decimal('0.0'),
            "tax_amount": Decimal('0.0'),
            "total": Decimal('0.0')
        }
        
        # Extract invoice number
        invoice_number_match = re.search(r'invoice\s*(?:#|no|number|num)[:\s]*([0-9a-zA-Z\-_/]+)', text, re.IGNORECASE)
        if invoice_number_match:
            data["invoice_number"] = invoice_number_match.group(1).strip()
        
        # Extract date
        date_match = re.search(r'date[:\s]*([\d]{1,2}[-/\.][\d]{1,2}[-/\.][\d]{2,4})', text, re.IGNORECASE)
        if date_match:
            data["date"] = date_match.group(1).strip()
        
        # Extract supplier name
        supplier_match = re.search(r'(from|vendor|supplier|bill\s*from)[:\s]*([A-Za-z0-9\s.,]+)', text, re.IGNORECASE)
        if supplier_match:
            data["supplier_info"]["name"] = supplier_match.group(2).strip()
        
        # Extract supplier tax ID
        tax_id_match = re.search(r'(tax\s*id|vat\s*number)[:\s]*([A-Za-z0-9\s.,]+)', text, re.IGNORECASE)
        if tax_id_match:
            data["supplier_info"]["tax_id"] = tax_id_match.group(2).strip()
        
        # Extract line items - this is more complex and depends on invoice format
        # Here's a simple approach that looks for patterns that might be line items
        lines = text.split('\n')
        line_items = []
        
        for i, line in enumerate(lines):
            # Look for lines with quantity, description and price patterns
            qty_match = re.search(r'^[\s]*(\d+\.?\d*)', line)
            price_match = re.search(r'(\d+\.?\d*)$', line)
            
            if qty_match and price_match and i+1 < len(lines):
                try:
                    quantity = Decimal(qty_match.group(1))
                    price = Decimal(price_match.group(1))
                    # Description is likely on the next line or between qty and price
                    desc_part = line[len(qty_match.group(0)):line.rfind(price_match.group(0))]
                    if not desc_part.strip():
                        desc_part = lines[i+1]
                    
                    line_items.append({
                        "description": desc_part.strip(),
                        "quantity": quantity,
                        "price": price,
                        "unit": "ea"  # Default unit
                    })
                except (ValueError, InvalidOperation, DecimalException):
                    # Skip this line if there's an error converting to Decimal
                    continue
        
        data["line_items"] = line_items
        
        # Extract totals
        total_match = re.search(r'(total)[:\s]*[$€£]?(\d+\.?\d*)', text, re.IGNORECASE)
        if total_match:
            try:
                data["total"] = Decimal(total_match.group(2))
            except (ValueError, InvalidOperation, DecimalException):
                # Keep default value if conversion fails
                pass
        
        subtotal_match = re.search(r'(subtotal|sub-total|net)[:\s]*[$€£]?(\d+\.?\d*)', text, re.IGNORECASE)
        if subtotal_match:
            try:
                data["subtotal"] = Decimal(subtotal_match.group(2))
            except (ValueError, InvalidOperation, DecimalException):
                # Keep default value if conversion fails
                pass
        
        tax_match = re.search(r'(tax|vat|gst)[:\s]*[$€£]?(\d+\.?\d*)', text, re.IGNORECASE)
        if tax_match:
            try:
                data["tax_amount"] = Decimal(tax_match.group(2))
            except (ValueError, InvalidOperation, DecimalException):
                # Keep default value if conversion fails
                pass
        
        return data


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

try:
    from pdf2image import convert_from_bytes
    # Test if poppler is installed
    test_pdf_bytes = b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%EOF"
    convert_from_bytes(test_pdf_bytes, size=1)
except Exception as e:
    # Handle Poppler not installed/configured properly
    poppler_error = str(e)
