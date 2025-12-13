"""
Views for Accounting Export API
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging

from .services import AccountingExportService
from .serializers import (
    AccountingExportRequestSerializer,
    AccountingExportSummarySerializer,
)
from apps.accounts.models import BusinessAccount

logger = logging.getLogger(__name__)


class AccountingExportView(APIView):
    """
    API endpoint for generating accounting exports (CSV files for Sage 100).
    
    This endpoint allows business owners to download their invoices in a format
    compatible with professional accounting software following the Moroccan
    Chart of Accounts (Plan Comptable Marocain).
    """
    
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_id='accounting_export_preview',
        operation_summary='Preview Accounting Export',
        operation_description="""
        Get a summary/preview of what will be included in the accounting export.
        Use this before downloading to verify the date range and invoice counts.
        """,
        manual_parameters=[
            openapi.Parameter(
                'start_date',
                openapi.IN_QUERY,
                description='Start date (YYYY-MM-DD)',
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
                required=True,
            ),
            openapi.Parameter(
                'end_date',
                openapi.IN_QUERY,
                description='End date (YYYY-MM-DD)',
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
                required=True,
            ),
            openapi.Parameter(
                'journal_type',
                openapi.IN_QUERY,
                description='Type of journal (purchases, sales, all)',
                type=openapi.TYPE_STRING,
                enum=['purchases', 'sales', 'all'],
                default='all',
            ),
        ],
        responses={
            200: AccountingExportSummarySerializer,
            400: 'Bad Request - Invalid parameters',
            403: 'Forbidden - No business account',
        },
        tags=['Accounting'],
    )
    def get(self, request):
        """Get export preview/summary."""
        # Validate request parameters
        serializer = AccountingExportRequestSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get business account
        try:
            business_account = BusinessAccount.objects.get(primary_user=request.user)
        except BusinessAccount.DoesNotExist:
            return Response(
                {'error': 'No business account found for this user.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate summary
        service = AccountingExportService(business_account)
        summary = service.get_export_summary(
            start_date=serializer.validated_data['start_date'],
            end_date=serializer.validated_data['end_date'],
            journal_type=serializer.validated_data['journal_type'],
        )
        
        return Response(summary)
    
    @swagger_auto_schema(
        operation_id='accounting_export_download',
        operation_summary='Download Accounting Export',
        operation_description="""
        Generate and download an accounting export file.
        
        **Supported Formats:**
        - **CSV**: Sage 100 compatible, semicolon-delimited
        - **Excel**: .xlsx with formatted columns and summary sheet
        - **JSON**: Structured data for API integrations
        - **UBL/XML**: Universal Business Language format for interoperability
        
        **CSV Columns:**
        - Journal: Journal code (AC=Achats, VE=Ventes)
        - Date: Invoice date (DD/MM/YYYY)
        - Pièce: Invoice number/reference
        - Compte: Account code (Plan Comptable)
        - Auxiliaire: Partner code (supplier/customer)
        - Libellé: Description
        - Débit: Debit amount
        - Crédit: Credit amount
        - Référence: Additional reference
        
        **Accounting Entries Generated:**
        For each invoice, 2-3 lines are generated following double-entry principles:
        
        *Purchase Invoice:*
        1. Debit: Expense account (Class 6)
        2. Debit: VAT Recoverable (34552)
        3. Credit: Supplier account (4411)
        
        *Sale Invoice:*
        1. Debit: Customer account (3421)
        2. Credit: Revenue account (Class 7)
        3. Credit: VAT Collected (44552)
        """,
        request_body=AccountingExportRequestSerializer,
        responses={
            200: openapi.Response(
                description='Export file download',
                schema=openapi.Schema(type=openapi.TYPE_FILE),
            ),
            400: 'Bad Request - Invalid parameters',
            403: 'Forbidden - No business account',
        },
        tags=['Accounting'],
    )
    def post(self, request):
        """Generate and download accounting export in specified format."""
        # Validate request parameters
        serializer = AccountingExportRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get business account
        try:
            business_account = BusinessAccount.objects.get(primary_user=request.user)
        except BusinessAccount.DoesNotExist:
            return Response(
                {'error': 'No business account found for this user.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate export in requested format
        service = AccountingExportService(business_account)
        export_format = serializer.validated_data.get('format', 'csv')
        
        try:
            content, filename, content_type = service.generate_export(
                start_date=serializer.validated_data['start_date'],
                end_date=serializer.validated_data['end_date'],
                journal_type=serializer.validated_data['journal_type'],
                format=export_format,
            )
        except ImportError as e:
            return Response(
                {'error': f'Missing dependency for {export_format} export: {str(e)}'},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        except Exception as e:
            logger.exception(f"Error generating accounting export: {str(e)}")
            return Response(
                {'error': f'Failed to generate export: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Create HTTP response with file
        response = HttpResponse(
            content,
            content_type=content_type
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['X-Filename'] = filename
        
        logger.info(
            f"User {request.user.email} downloaded accounting export: {filename}"
        )
        
        return response


class AccountMappingView(APIView):
    """
    API endpoint for viewing the account code mappings.
    
    Shows how invoice categories are mapped to accounting codes
    from the Moroccan Chart of Accounts.
    """
    
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_id='account_mappings_list',
        operation_summary='Get Account Mappings',
        operation_description="""
        Get the list of category-to-account mappings used in accounting exports.
        
        This shows how invoice categories are mapped to Moroccan Chart of Accounts
        codes (Plan Comptable Marocain).
        """,
        responses={
            200: 'List of account mappings',
        },
        tags=['Accounting'],
    )
    def get(self, request):
        """Get account mappings."""
        # Return the standard mappings
        expense_mappings = [
            {'category': key, 'account_code': code, 'type': 'expense'}
            for key, code in AccountingExportService.EXPENSE_ACCOUNT_MAPPING.items()
        ]
        
        revenue_mappings = [
            {'category': key, 'account_code': code, 'type': 'revenue'}
            for key, code in AccountingExportService.REVENUE_ACCOUNT_MAPPING.items()
        ]
        
        vat_accounts = [
            {'name': key, 'account_code': code, 'type': 'vat'}
            for key, code in AccountingExportService.VAT_ACCOUNTS.items()
        ]
        
        third_party_accounts = [
            {'name': key, 'account_code': code, 'type': 'third_party'}
            for key, code in AccountingExportService.THIRD_PARTY_ACCOUNTS.items()
        ]
        
        return Response({
            'expense_accounts': expense_mappings,
            'revenue_accounts': revenue_mappings,
            'vat_accounts': vat_accounts,
            'third_party_accounts': third_party_accounts,
            'journal_codes': AccountingExportService.JOURNAL_CODES,
        })
