import uuid
from django.db import models
from django.utils import timezone
from decimal import Decimal

from apps.common.models import BaseModel
from apps.accounts.models import BusinessAccount
from apps.users.models import User


# Helper functions for file paths
def statement_document_path(instance, filename):
    """Generate path for bank statement documents by business account"""
    return f'business/{instance.business_account.id}_{instance.business_account.business_name}/bank_statements/original/{filename}'


class BankStatement(BaseModel):
    """Main bank statement model"""
    business_account = models.ForeignKey(
        BusinessAccount, 
        on_delete=models.CASCADE, 
        related_name='bank_statements'
    )
    
    # Statement metadata
    account_holder = models.CharField(max_length=255, null=True, blank=True)
    bank_name = models.CharField(max_length=255, null=True, blank=True)
    account_number = models.CharField(max_length=100, null=True, blank=True)
    iban = models.CharField(max_length=34, null=True, blank=True)
    branch = models.CharField(max_length=255, null=True, blank=True)
    
    # Statement period
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    
    # Balances
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    closing_balance = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='MAD')
    
    # File information
    original_file = models.FileField(upload_to=statement_document_path, null=True, blank=True)
    file_type = models.CharField(max_length=50, null=True, blank=True)  # PDF, CSV, XLS, Image
    
    # Processing status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('review', 'Needs Review'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Parser information
    parser_used = models.CharField(max_length=50, null=True, blank=True)  # 'traditional' or 'gpt'
    processing_error = models.TextField(null=True, blank=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Calculated fields
    total_debits = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total_credits = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    transaction_count = models.IntegerField(default=0)
    
    # Additional metadata
    notes = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['-period_end', '-created_at']
        verbose_name = 'Bank Statement'
        verbose_name_plural = 'Bank Statements'

    def __str__(self):
        return f"{self.bank_name} - {self.account_number} ({self.period_start} to {self.period_end})"
    
    def calculate_totals(self):
        """Calculate total debits, credits, and transaction count"""
        transactions = self.transactions.all()
        self.total_debits = sum(t.debit for t in transactions if t.debit)
        self.total_credits = sum(t.credit for t in transactions if t.credit)
        self.transaction_count = transactions.count()
        self.save()


class BankTransaction(BaseModel):
    """Individual bank transactions from statements"""
    bank_statement = models.ForeignKey(
        BankStatement, 
        on_delete=models.CASCADE, 
        related_name='transactions'
    )
    
    # Transaction dates
    operation_date = models.DateField()
    value_date = models.DateField(null=True, blank=True)
    
    # Transaction details
    reference = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField()
    
    # Financial details
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    balance_after = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Categorization
    CATEGORY_CHOICES = [
        ('BANK_FEE', 'Bank Fee'),
        ('ATM_WITHDRAWAL', 'ATM Withdrawal'),
        ('BILL_PAYMENT', 'Bill Payment'),
        ('LOAN_REPAYMENT', 'Loan Repayment'),
        ('TAX', 'Tax'),
        ('TRANSFER_OUT', 'Transfer Out'),
        ('TRANSFER_IN', 'Transfer In'),
        ('CASH_DEPOSIT', 'Cash Deposit'),
        ('CARD_PAYMENT', 'Card Payment'),
        ('CHECK_PAYMENT', 'Check Payment'),
        ('SALARY', 'Salary'),
        ('INTEREST', 'Interest'),
        ('OTHER', 'Other'),
    ]
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='OTHER')
    subcategory = models.CharField(max_length=100, null=True, blank=True)
    
    # Party information
    merchant = models.CharField(max_length=255, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    beneficiary = models.CharField(max_length=255, null=True, blank=True)
    depositor = models.CharField(max_length=255, null=True, blank=True)
    counterparty_name = models.CharField(max_length=255, null=True, blank=True)
    counterparty_account = models.CharField(max_length=100, null=True, blank=True)
    
    # Additional details
    payment_method = models.CharField(max_length=100, null=True, blank=True)
    card_number = models.CharField(max_length=20, null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    
    # Matching and reconciliation
    is_reconciled = models.BooleanField(default=False)
    matched_invoice = models.ForeignKey(
        'invoices.Invoice', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='bank_transactions'
    )
    
    # Flags
    is_duplicate = models.BooleanField(default=False)
    needs_review = models.BooleanField(default=False)
    review_notes = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['-operation_date', '-created_at']
        verbose_name = 'Bank Transaction'
        verbose_name_plural = 'Bank Transactions'
        indexes = [
            models.Index(fields=['operation_date']),
            models.Index(fields=['category']),
            models.Index(fields=['is_reconciled']),
        ]

    def __str__(self):
        return f"{self.operation_date} - {self.description[:50]} - {self.debit or self.credit}"
    
    @property
    def amount(self):
        """Return the transaction amount (debit or credit)"""
        return self.debit if self.debit > 0 else self.credit
    
    @property
    def transaction_type(self):
        """Return transaction type based on debit/credit"""
        return 'debit' if self.debit > 0 else 'credit'


class TransactionCategory(BaseModel):
    """Custom categories for transaction classification"""
    business_account = models.ForeignKey(
        BusinessAccount, 
        on_delete=models.CASCADE, 
        related_name='bank_transaction_categories'
    )
    
    name = models.CharField(max_length=100)
    parent_category = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='subcategories'
    )
    description = models.TextField(null=True, blank=True)
    color = models.CharField(max_length=7, default='#000000')  # Hex color code
    
    # Auto-classification rules
    keywords = models.JSONField(default=list, blank=True)  # List of keywords for auto-categorization
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Bank Transaction Category'
        verbose_name_plural = 'Bank Transaction Categories'
        unique_together = ['business_account', 'name', 'parent_category']

    def __str__(self):
        if self.parent_category:
            return f"{self.parent_category.name} > {self.name}"
        return self.name
