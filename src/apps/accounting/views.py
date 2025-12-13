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
import traceback
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from dateutil.relativedelta import relativedelta

from apps.bank_statements.models import BankTransaction, BankStatement
from apps.invoices.models import Invoice

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


class DashboardStatsView(APIView):
    """
    Dashboard statistics API endpoint.
    Returns aggregated data for dashboard cards, charts, and activity timeline.
    """
    permission_classes = [IsAuthenticated]
    
    def get_business_accounts(self, user):
        """Get business accounts the user has access to"""
        business_accounts = user.business_accounts.all()
        if hasattr(user, 'owned_business') and user.owned_business:
            business_accounts = business_accounts | BusinessAccount.objects.filter(id=user.owned_business.id)
        return business_accounts
    
    def get(self, request):
        """Get dashboard statistics"""
        try:
            business_accounts = self.get_business_accounts(request.user)
            
            if not business_accounts.exists():
                return Response({
                    "error": "No business account found"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            today = timezone.now().date()
            current_month_start = today.replace(day=1)
            last_month_start = (current_month_start - relativedelta(months=1))
            last_month_end = current_month_start - relativedelta(days=1)
            six_months_ago = current_month_start - relativedelta(months=6)
            
            # Base queryset for invoices
            invoices = Invoice.objects.filter(business_account__in=business_accounts)
            
            # ===================
            # 1. TOTAL SALES (Paid sale invoices)
            # ===================
            total_sales_current = invoices.filter(
                invoice_type='sale',
                status='paid'
            ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
            
            total_sales_last_month = invoices.filter(
                invoice_type='sale',
                status='paid',
                paid_date__gte=last_month_start,
                paid_date__lte=last_month_end
            ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
            
            # Calculate trend
            sales_trend = 0
            if total_sales_last_month > 0:
                sales_trend = round(float((total_sales_current - total_sales_last_month) / total_sales_last_month * 100), 1)
            
            # ===================
            # 2. OUTSTANDING INVOICES (Unpaid/Overdue)
            # ===================
            outstanding_result = invoices.filter(
                status__in=['unpaid', 'overdue']
            ).aggregate(
                total=Sum('total'),
                count=Count('id')
            )
            outstanding_amount = outstanding_result['total'] or Decimal('0.00')
            outstanding_count = outstanding_result['count'] or 0
            
            # ===================
            # 3. TOTAL EXPENSES (Paid purchase invoices)
            # ===================
            total_expenses_current = invoices.filter(
                invoice_type='purchase',
                status='paid'
            ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
            
            total_expenses_last_month = invoices.filter(
                invoice_type='purchase',
                status='paid',
                paid_date__gte=last_month_start,
                paid_date__lte=last_month_end
            ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
            
            # Calculate trend
            expenses_trend = 0
            if total_expenses_last_month > 0:
                expenses_trend = round(float((total_expenses_current - total_expenses_last_month) / total_expenses_last_month * 100), 1)
            
            # ===================
            # 4. TRANSACTIONS COUNT (Bank transactions this month)
            # ===================
            transactions_count = BankTransaction.objects.filter(
                bank_statement__business_account__in=business_accounts,
                operation_date__gte=current_month_start
            ).count()
            
            transactions_last_month = BankTransaction.objects.filter(
                bank_statement__business_account__in=business_accounts,
                operation_date__gte=last_month_start,
                operation_date__lte=last_month_end
            ).count()
            
            transactions_trend = transactions_count - transactions_last_month
            
            # ===================
            # 5. CASH FLOW CHART (Last 6 months)
            # ===================
            # Get income (sales) by month
            income_by_month = invoices.filter(
                invoice_type='sale',
                status='paid',
                paid_date__gte=six_months_ago
            ).annotate(
                month=TruncMonth('paid_date')
            ).values('month').annotate(
                total=Sum('total')
            ).order_by('month')
            
            # Get expenses (purchases) by month
            expenses_by_month = invoices.filter(
                invoice_type='purchase',
                status='paid',
                paid_date__gte=six_months_ago
            ).annotate(
                month=TruncMonth('paid_date')
            ).values('month').annotate(
                total=Sum('total')
            ).order_by('month')
            
            # Build chart data for last 6 months
            labels = []
            income_data = []
            expenses_data = []
            
            for i in range(5, -1, -1):
                month_date = current_month_start - relativedelta(months=i)
                month_label = month_date.strftime('%b')
                labels.append(month_label)
                
                # Find income for this month
                income_val = 0
                for item in income_by_month:
                    if item['month'] and item['month'].month == month_date.month and item['month'].year == month_date.year:
                        income_val = float(item['total'])
                        break
                income_data.append(income_val)
                
                # Find expenses for this month
                expense_val = 0
                for item in expenses_by_month:
                    if item['month'] and item['month'].month == month_date.month and item['month'].year == month_date.year:
                        expense_val = float(item['total'])
                        break
                expenses_data.append(expense_val)
            
            # ===================
            # 6. RECENT ACTIVITY (Last 5 items)
            # ===================
            recent_invoices = invoices.order_by('-created_at')[:5]
            recent_statements = BankStatement.objects.filter(
                business_account__in=business_accounts
            ).order_by('-created_at')[:3]
            
            recent_activity = []
            
            # Add recent invoices
            for inv in recent_invoices:
                days_unpaid = ""
                if inv.status in ['unpaid', 'overdue'] and inv.due_date:
                    days = (today - inv.due_date).days
                    if days > 0:
                        days_unpaid = f"Unpaid for {days} days"
                    else:
                        days_unpaid = f"Due in {abs(days)} days"
                
                activity_item = {
                    "type": "invoice",
                    "icon": "receipt",
                    "color": "warning" if inv.status == 'overdue' else ("success" if inv.status == 'paid' else "info"),
                    "title": f"Invoice #{inv.invoice_number}",
                    "description": days_unpaid or f"{inv.get_status_display()}",
                    "date": inv.created_at.strftime('%b %d, %Y')
                }
                recent_activity.append(activity_item)
            
            # Add recent bank statements
            for stmt in recent_statements:
                recent_activity.append({
                    "type": "bank_statement",
                    "icon": "account_balance",
                    "color": "primary",
                    "title": f"Bank Statement - {stmt.bank_name}",
                    "description": "PDF Added",
                    "date": stmt.created_at.strftime('%b %d, %Y')
                })
            
            # Sort by date and limit to 5
            recent_activity = sorted(recent_activity, key=lambda x: x['date'], reverse=True)[:5]
            
            # Get default currency from business account
            primary_account = business_accounts.first()
            currency = getattr(primary_account, 'currency', 'MAD') or 'MAD'
            
            # ===================
            # BUILD RESPONSE
            # ===================
            response_data = {
                "total_sales": {
                    "value": float(total_sales_current),
                    "currency": currency,
                    "trend": sales_trend,
                    "trend_text": "vs last month"
                },
                "outstanding_invoices": {
                    "value": float(outstanding_amount),
                    "count": outstanding_count,
                    "currency": currency
                },
                "total_expenses": {
                    "value": float(total_expenses_current),
                    "currency": currency,
                    "trend": expenses_trend,
                    "trend_text": "vs last month"
                },
                "transactions_count": {
                    "value": transactions_count,
                    "trend": transactions_trend,
                    "trend_text": "vs last month"
                },
                "cash_flow": {
                    "labels": labels,
                    "income": income_data,
                    "expenses": expenses_data
                },
                "recent_activity": recent_activity
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Dashboard stats error: {str(e)}\n{traceback.format_exc()}")
            return Response(
                {"error": f"Failed to get dashboard stats: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
