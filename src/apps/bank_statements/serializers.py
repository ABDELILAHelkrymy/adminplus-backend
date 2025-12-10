from rest_framework import serializers
from decimal import Decimal
from .models import BankStatement, BankTransaction, TransactionCategory


class BankStatementSerializer(serializers.ModelSerializer):
    """Simplified serializer for list view"""
    transaction_count = serializers.IntegerField(read_only=True)
    total_debits = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    total_credits = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = BankStatement
        exclude = ['business_account']
        read_only_fields = ['id', 'created_at', 'updated_at', 'transaction_count', 'total_debits', 'total_credits', 'status', 'parser_used', 'confidence_score']


class BankTransactionSerializer(serializers.ModelSerializer):
    """Serializer for bank transactions"""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    transaction_type = serializers.CharField(read_only=True)
    matched_invoice_number = serializers.SerializerMethodField()
    reconciled_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = BankTransaction
        exclude = ['bank_statement']
        read_only_fields = ['id', 'created_at', 'updated_at', 'reconciled_at', 'reconciled_by', 'match_confidence', 'match_reasons']

    def get_matched_invoice_number(self, obj):
        """Get the invoice number if matched"""
        if obj.matched_invoice:
            return obj.matched_invoice.invoice_number
        return None

    def get_reconciled_by_name(self, obj):
        """Get the name of the user who reconciled"""
        if obj.reconciled_by:
            return f"{obj.reconciled_by.first_name} {obj.reconciled_by.last_name}".strip() or obj.reconciled_by.email
        return None


class BankStatementDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for retrieve view with transactions"""
    transactions = BankTransactionSerializer(many=True, read_only=True)
    transaction_count = serializers.IntegerField(read_only=True)
    total_debits = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    total_credits = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = BankStatement
        exclude = ['business_account']
        read_only_fields = ['id', 'created_at', 'updated_at', 'transaction_count', 'total_debits', 'total_credits', 'status', 'parser_used', 'confidence_score']


class TransactionCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionCategory
        fields = '__all__'
        ref_name = 'BankStatementTransactionCategory'  # Add this line
