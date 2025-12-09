from django.shortcuts import render
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging
import traceback
from decimal import Decimal
from datetime import datetime

from apps.accounts.models import BusinessAccount
from .models import BankStatement, BankTransaction, TransactionCategory, MOROCCAN_BANKS
from .serializers import (
    BankStatementSerializer,
    BankStatementDetailSerializer,
    BankTransactionSerializer,
    TransactionCategorySerializer
)
from .statement_parser import StatementParser

logger = logging.getLogger(__name__)


class BankStatementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing bank statements
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['account_holder', 'bank_name', 'account_number', 'branch']
    ordering_fields = ['period_start', 'period_end', 'created_at', 'opening_balance', 'closing_balance']
    filterset_fields = ['status', 'currency', 'parser_used']

    def get_serializer_class(self):
        """Return different serializer for list and detail"""
        if self.action == 'retrieve':
            return BankStatementDetailSerializer
        return BankStatementSerializer

    def get_queryset(self):
        """Return bank statements for the user's business account"""
        if not self.request.user.is_authenticated:
            return BankStatement.objects.none()
        
        # Get the business accounts the user has access to
        business_accounts = self.request.user.business_accounts.all()
        if hasattr(self.request.user, 'owned_business'):
            business_accounts = business_accounts | BusinessAccount.objects.filter(id=self.request.user.owned_business.id)
        
        return BankStatement.objects.filter(business_account__in=business_accounts)
    
    def perform_create(self, serializer):
        """Set the business account when creating a bank statement"""
        if hasattr(self.request.user, 'owned_business'):
            serializer.save(business_account=self.request.user.owned_business)
        else:
            return Response(
                {"error": "User does not have a business account"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @swagger_auto_schema(
        operation_summary="Get list of Moroccan banks",
        operation_description="Returns the list of available Moroccan banks for selection",
        responses={200: openapi.Response(description="List of banks")},
    )
    @action(detail=False, methods=['get'])
    def moroccan_banks(self, request):
        """
        Get list of Moroccan banks
        """
        banks = [{'code': code, 'name': name} for code, name in MOROCCAN_BANKS]
        return Response(banks, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Parse bank statement file",
        operation_description="Extract transactions and metadata from uploaded bank statement file (PDF, Image, CSV, Excel)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['file'],
            properties={
                'file': openapi.Schema(type=openapi.TYPE_FILE, description='Bank statement file'),
                'use_gpt': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Use GPT parser (default: true)', default=True),
            }
        ),
        responses={
            200: openapi.Response(description="Extracted bank statement data"),
            400: openapi.Response(description="Bad request"),
            500: openapi.Response(description="Server error"),
        },
    )
    @action(detail=False, methods=['post'])
    def parse_statement(self, request):
        """
        Extract data from uploaded bank statement file
        """
        try:
            if 'file' not in request.FILES:
                return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
            
            statement_file = request.FILES['file']
            use_gpt = request.data.get('use_gpt', 'true').lower() in ('true', 't', 'yes', 'y', '1')
            
            # Parse the statement
            # Note: Poppler and Tesseract are only needed for image files and scanned PDFs
            # Most PDFs with text will work fine without these dependencies
            try:
                extracted_data = StatementParser.parse_statement(statement_file, use_gpt=use_gpt)
                return Response(extracted_data, status=status.HTTP_200_OK)
            except ValueError as e:
                # Check if it's a dependency issue
                error_msg = str(e)
                if "Poppler" in error_msg or "Tesseract" in error_msg:
                    instructions = StatementParser.get_dependency_installation_instructions()
                    return Response({
                        "error": error_msg,
                        "installation_instructions": instructions,
                        "note": "Text-based PDFs can be processed without these dependencies. Only image files and scanned PDFs require Poppler and Tesseract."
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                return Response(
                    {"error": error_msg},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Bank statement parsing error: {str(e)}\n{traceback.format_exc()}")
            return Response(
                {"error": f"Failed to parse bank statement: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_summary="Create statement from parsed data",
        operation_description="Create a bank statement and transactions from previously parsed data",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['statement_data'],
            properties={
                'statement_data': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    description='Parsed statement data from parse_statement endpoint'
                ),
                'file': openapi.Schema(type=openapi.TYPE_FILE, description='Original statement file (optional)'),
            }
        ),
        responses={
            201: BankStatementDetailSerializer(),
            400: openapi.Response(description="Bad request"),
        },
    )
    @action(detail=False, methods=['post'])
    def create_from_parsed(self, request):
        """
        Create a bank statement and transactions from parsed data
        """
        try:
            statement_data = request.data.get('statement_data')
            if not statement_data:
                return Response(
                    {"error": "statement_data is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Parse JSON string if needed
            if isinstance(statement_data, str):
                import json
                statement_data = json.loads(statement_data)
            
            if not hasattr(request.user, 'owned_business'):
                return Response(
                    {"error": "User does not have a business account"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # The data is already flat (not nested under 'statement' key)
            # because the frontend extracts it from the parse response
            stmt = statement_data
            
            # Determine file type
            file_type = None
            if 'file' in request.FILES:
                file_name = request.FILES['file'].name.lower()
                if file_name.endswith('.pdf'):
                    file_type = 'PDF'
                elif file_name.endswith(('.jpg', '.jpeg', '.png')):
                    file_type = 'Image'
                elif file_name.endswith('.csv'):
                    file_type = 'CSV'
                elif file_name.endswith(('.xls', '.xlsx')):
                    file_type = 'Excel'
            
            # Create bank statement
            bank_statement = BankStatement.objects.create(
                business_account=request.user.owned_business,
                account_holder=stmt.get('account_holder'),
                bank_name=stmt.get('bank_name') or 'Auto-detected',
                account_number=stmt.get('account_number'),
                branch=stmt.get('branch'),
                period_start=stmt.get('period_start'),
                period_end=stmt.get('period_end'),
                opening_balance=Decimal(str(stmt.get('opening_balance', 0))) if stmt.get('opening_balance') else None,
                closing_balance=Decimal(str(stmt.get('closing_balance', 0))) if stmt.get('closing_balance') else None,
                currency=stmt.get('currency') or 'MAD',
                file_type=file_type,
                status='processing',
                parser_used='gpt'
            )
            
            # Save original file if provided
            if 'file' in request.FILES:
                bank_statement.original_file = request.FILES['file']
                bank_statement.save()
            
            # Create transactions
            transactions = stmt.get('transactions', [])
            created_transactions = []
            
            for trans_data in transactions:
                try:
                    # Parse time if present
                    time_value = None
                    if trans_data.get('time'):
                        try:
                            time_value = datetime.strptime(trans_data['time'], '%H:%M:%S').time()
                        except:
                            pass
                    
                    # Handle field name mapping: transaction_date -> operation_date
                    operation_date = trans_data.get('operation_date') or trans_data.get('transaction_date')
                    
                    transaction = BankTransaction.objects.create(
                        bank_statement=bank_statement,
                        operation_date=operation_date,
                        value_date=trans_data.get('value_date'),
                        reference=trans_data.get('reference'),
                        description=trans_data.get('description', ''),
                        debit=Decimal(str(trans_data.get('debit', 0))),
                        credit=Decimal(str(trans_data.get('credit', 0))),
                        category=trans_data.get('category', 'OTHER'),
                        merchant=trans_data.get('merchant'),
                        location=trans_data.get('location'),
                        beneficiary=trans_data.get('beneficiary'),
                        depositor=trans_data.get('depositor'),
                        time=time_value,
                    )
                    created_transactions.append(transaction)
                except Exception as e:
                    logger.warning(f"Failed to create transaction: {str(e)}")
                    continue
            
            # Calculate totals
            bank_statement.calculate_totals()
            bank_statement.status = 'completed'
            bank_statement.save()
            
            # Return created statement
            serializer = BankStatementDetailSerializer(bank_statement)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating statement from parsed data: {str(e)}\n{traceback.format_exc()}")
            return Response(
                {"error": f"Failed to create statement: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_summary="Recalculate statement totals",
        operation_description="Recalculate total debits, credits, and transaction count",
        responses={200: openapi.Response(description="Totals recalculated")},
    )
    @action(detail=True, methods=['post'])
    def recalculate_totals(self, request, pk=None):
        """Recalculate statement totals"""
        statement = self.get_object()
        statement.calculate_totals()
        return Response({"status": "Totals recalculated successfully"}, status=status.HTTP_200_OK)


class BankTransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing bank transactions
    """
    serializer_class = BankTransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['description', 'reference', 'merchant', 'beneficiary', 'depositor']
    ordering_fields = ['operation_date', 'value_date', 'debit', 'credit', 'created_at']
    filterset_fields = ['category', 'is_reconciled', 'needs_review', 'is_duplicate']

    def get_queryset(self):
        """Return transactions for statements the user has access to"""
        if not self.request.user.is_authenticated:
            return BankTransaction.objects.none()
        
        # Get the business accounts the user has access to
        business_accounts = self.request.user.business_accounts.all()
        if hasattr(self.request.user, 'owned_business'):
            business_accounts = business_accounts | BusinessAccount.objects.filter(id=self.request.user.owned_business.id)
        
        # Get statements for these business accounts
        statements = BankStatement.objects.filter(business_account__in=business_accounts)
        
        # Filter by statement_id if provided
        statement_id = self.request.query_params.get('statement_id')
        if statement_id:
            statements = statements.filter(id=statement_id)
        
        return BankTransaction.objects.filter(bank_statement__in=statements)

    @swagger_auto_schema(
        operation_summary="Mark transaction as reconciled",
        operation_description="Mark a transaction as reconciled",
        responses={200: openapi.Response(description="Transaction reconciled")},
    )
    @action(detail=True, methods=['post'])
    def reconcile(self, request, pk=None):
        """Mark transaction as reconciled"""
        transaction = self.get_object()
        transaction.is_reconciled = True
        transaction.save()
        return Response({"status": "Transaction marked as reconciled"}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Mark transaction as duplicate",
        operation_description="Mark a transaction as a duplicate",
        responses={200: openapi.Response(description="Transaction marked as duplicate")},
    )
    @action(detail=True, methods=['post'])
    def mark_duplicate(self, request, pk=None):
        """Mark transaction as duplicate"""
        transaction = self.get_object()
        transaction.is_duplicate = True
        transaction.save()
        return Response({"status": "Transaction marked as duplicate"}, status=status.HTTP_200_OK)


class TransactionCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing transaction categories
    """
    serializer_class = TransactionCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        """Return categories for the user's business account"""
        if not self.request.user.is_authenticated:
            return TransactionCategory.objects.none()
        
        # Get the business accounts the user has access to
        business_accounts = self.request.user.business_accounts.all()
        if hasattr(self.request.user, 'owned_business'):
            business_accounts = business_accounts | BusinessAccount.objects.filter(id=self.request.user.owned_business.id)
        
        return TransactionCategory.objects.filter(business_account__in=business_accounts)
    
    def perform_create(self, serializer):
        """Set the business account when creating a category"""
        if hasattr(self.request.user, 'owned_business'):
            serializer.save(business_account=self.request.user.owned_business)
        else:
            return Response(
                {"error": "User does not have a business account"},
                status=status.HTTP_400_BAD_REQUEST
            )
