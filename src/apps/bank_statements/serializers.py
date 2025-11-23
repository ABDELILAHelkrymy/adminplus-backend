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
    
    class Meta:
        model = BankTransaction
        exclude = ['bank_statement']
        read_only_fields = ['id', 'created_at', 'updated_at']


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
