from rest_framework import serializers
from .models import TransactionCategory, FinancialAccount, Transaction, RecurringTransaction


class TransactionCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionCategory
        fields = '__all__'
        ref_name = 'FinancialTransactionCategory'  # Add this line


class FinancialAccountSerializer(serializers.ModelSerializer):
    account_type_display = serializers.CharField(source='get_account_type_display', read_only=True)
    
    class Meta:
        model = FinancialAccount
        fields = [
            'id', 'name', 'account_type', 'account_type_display',
            'account_number', 'current_balance', 'currency',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'current_balance']


class TransactionSerializer(serializers.ModelSerializer):
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_name = serializers.SerializerMethodField(read_only=True)
    financial_account_name = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'business_account', 'financial_account', 'financial_account_name',
            'category', 'category_name', 'transaction_type', 'transaction_type_display',
            'amount', 'description', 'reference', 'transaction_date',
            'status', 'status_display', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'business_account']
    
    def get_category_name(self, obj):
        if obj.category:
            return obj.category.name
        return None
    
    def get_financial_account_name(self, obj):
        if obj.financial_account:
            return obj.financial_account.name
        return None


class RecurringTransactionSerializer(serializers.ModelSerializer):
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    category_name = serializers.SerializerMethodField(read_only=True)
    financial_account_name = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = RecurringTransaction
        fields = [
            'id', 'business_account', 'name', 'financial_account', 'financial_account_name',
            'category', 'category_name', 'transaction_type', 'transaction_type_display',
            'amount', 'description', 'frequency', 'frequency_display',
            'start_date', 'end_date', 'next_due_date', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'business_account', 'next_due_date']
    
    def get_category_name(self, obj):
        if obj.category:
            return obj.category.name
        return None
    
    def get_financial_account_name(self, obj):
        if obj.financial_account:
            return obj.financial_account.name
        return None