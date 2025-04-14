from django.contrib import admin
from .models import (
    TransactionCategory, FinancialAccount, 
    Transaction, RecurringTransaction
)


class TransactionCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'business_account', 'is_expense', 'is_system', 'parent')
    list_filter = ('is_expense', 'is_system')
    search_fields = ('name', 'business_account__business_name')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('business_account', 'parent')


class FinancialAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'business_account', 'account_type', 'current_balance', 'currency', 'is_active')
    list_filter = ('account_type', 'currency', 'is_active')
    search_fields = ('name', 'business_account__business_name', 'account_number')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('business_account')


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_type', 'amount', 'business_account', 'financial_account', 
                   'transaction_date', 'status')
    list_filter = ('transaction_type', 'status', 'transaction_date')
    search_fields = ('description', 'reference', 'business_account__business_name')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('business_account', 'financial_account', 'category', 'created_by')


class RecurringTransactionAdmin(admin.ModelAdmin):
    list_display = ('name', 'transaction_type', 'amount', 'frequency', 'next_due_date', 
                   'is_active')
    list_filter = ('transaction_type', 'frequency', 'is_active')
    search_fields = ('name', 'description', 'business_account__business_name')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('business_account', 'financial_account', 'category', 'created_by')


# Register models
admin.site.register(TransactionCategory, TransactionCategoryAdmin)
admin.site.register(FinancialAccount, FinancialAccountAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(RecurringTransaction, RecurringTransactionAdmin)
