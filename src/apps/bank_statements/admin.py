from django.contrib import admin
from .models import BankStatement, BankTransaction, TransactionCategory


@admin.register(BankStatement)
class BankStatementAdmin(admin.ModelAdmin):
    list_display = ['account_number', 'bank_name', 'period_start', 'period_end', 'status', 'transaction_count', 'created_at']
    list_filter = ['status', 'currency', 'parser_used', 'created_at']
    search_fields = ['account_holder', 'account_number', 'bank_name', 'branch']
    readonly_fields = ['created_at', 'updated_at', 'transaction_count', 'total_debits', 'total_credits']
    
    fieldsets = (
        ('Account Information', {
            'fields': ('business_account', 'account_holder', 'bank_name', 'account_number', 'iban', 'branch')
        }),
        ('Statement Period', {
            'fields': ('period_start', 'period_end', 'currency')
        }),
        ('Balances', {
            'fields': ('opening_balance', 'closing_balance', 'total_debits', 'total_credits', 'transaction_count')
        }),
        ('File Information', {
            'fields': ('original_file', 'file_type')
        }),
        ('Processing', {
            'fields': ('status', 'parser_used', 'confidence_score', 'processing_error')
        }),
        ('Additional', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    list_display = ['operation_date', 'description', 'category', 'debit', 'credit', 'is_reconciled', 'created_at']
    list_filter = ['category', 'is_reconciled', 'needs_review', 'is_duplicate', 'operation_date']
    search_fields = ['description', 'reference', 'merchant', 'beneficiary', 'depositor']
    readonly_fields = ['created_at', 'updated_at', 'amount', 'transaction_type']
    
    fieldsets = (
        ('Statement', {
            'fields': ('bank_statement',)
        }),
        ('Transaction Details', {
            'fields': ('operation_date', 'value_date', 'reference', 'description', 'time')
        }),
        ('Financial', {
            'fields': ('debit', 'credit', 'balance_after', 'amount', 'transaction_type')
        }),
        ('Categorization', {
            'fields': ('category', 'subcategory')
        }),
        ('Party Information', {
            'fields': ('merchant', 'location', 'beneficiary', 'depositor', 'counterparty_name', 'counterparty_account'),
            'classes': ('collapse',)
        }),
        ('Additional Details', {
            'fields': ('payment_method', 'card_number'),
            'classes': ('collapse',)
        }),
        ('Reconciliation', {
            'fields': ('is_reconciled', 'matched_invoice', 'is_duplicate', 'needs_review', 'review_notes')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TransactionCategory)
class TransactionCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent_category', 'business_account', 'created_at']
    list_filter = ['business_account', 'parent_category']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
