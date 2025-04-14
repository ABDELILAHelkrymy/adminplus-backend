from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel
from apps.accounts.models import BusinessAccount
from apps.users.models import User


class TransactionStatus(models.TextChoices):
    """Transaction status choices"""
    PENDING = 'pending', _('Pending')
    COMPLETED = 'completed', _('Completed')
    CANCELLED = 'cancelled', _('Cancelled')
    RECONCILED = 'reconciled', _('Reconciled')


class TransactionType(models.TextChoices):
    """Transaction type choices"""
    INCOME = 'income', _('Income')
    EXPENSE = 'expense', _('Expense')
    TRANSFER = 'transfer', _('Transfer')
    ADJUSTMENT = 'adjustment', _('Adjustment')


class TransactionCategory(BaseModel):
    """Model for transaction categories"""
    business_account = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name='transaction_categories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subcategories')
    is_expense = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)  # System categories can't be deleted
    
    def __str__(self):
        return self.name


class FinancialAccount(BaseModel):
    """Model for financial accounts (bank accounts, credit cards, etc.)"""
    ACCOUNT_TYPE_CHOICES = [
        ('checking', _('Checking Account')),
        ('savings', _('Savings Account')),
        ('credit_card', _('Credit Card')),
        ('loan', _('Loan')),
        ('investment', _('Investment')),
        ('cash', _('Cash')),
        ('other', _('Other')),
    ]
    
    business_account = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name='financial_accounts')
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()})"
    
    def update_balance(self, amount, is_credit=True):
        """
        Update account balance
        :param amount: Amount to add/subtract
        :param is_credit: True for credit, False for debit
        """
        if is_credit:
            self.current_balance += amount
        else:
            self.current_balance -= amount
        self.save(update_fields=['current_balance'])


class Transaction(BaseModel):
    """Model for financial transactions"""
    
    business_account = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name='transactions')
    financial_account = models.ForeignKey(FinancialAccount, on_delete=models.CASCADE, related_name='transactions')
    category = models.ForeignKey(TransactionCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    reference = models.CharField(max_length=100, blank=True, null=True)
    
    transaction_date = models.DateField()
    status = models.CharField(max_length=10, choices=TransactionStatus.choices, default=TransactionStatus.COMPLETED)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_transactions')
    
    def __str__(self):
        return f"{self.get_transaction_type_display()}: {self.amount} on {self.transaction_date}"


class RecurringTransaction(BaseModel):
    """Model for recurring transactions (subscriptions, regular payments)"""
    FREQUENCY_CHOICES = [
        ('daily', _('Daily')),
        ('weekly', _('Weekly')),
        ('biweekly', _('Bi-weekly')),
        ('monthly', _('Monthly')),
        ('quarterly', _('Quarterly')),
        ('annually', _('Annually')),
    ]
    
    business_account = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name='recurring_transactions')
    name = models.CharField(max_length=100)
    financial_account = models.ForeignKey(FinancialAccount, on_delete=models.CASCADE, related_name='recurring_transactions')
    category = models.ForeignKey(TransactionCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='recurring_transactions')
    
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    next_due_date = models.DateField()
    is_active = models.BooleanField(default=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_recurring_transactions')
    
    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"
    
    def calculate_next_due_date(self):
        """Calculate the next due date based on frequency"""
        current_date = self.next_due_date or self.start_date
        
        if self.frequency == 'daily':
            self.next_due_date = current_date + timezone.timedelta(days=1)
        elif self.frequency == 'weekly':
            self.next_due_date = current_date + timezone.timedelta(weeks=1)
        elif self.frequency == 'biweekly':
            self.next_due_date = current_date + timezone.timedelta(weeks=2)
        elif self.frequency == 'monthly':
            # Add one month
            if current_date.month == 12:
                self.next_due_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                self.next_due_date = current_date.replace(month=current_date.month + 1)
        elif self.frequency == 'quarterly':
            # Add three months
            if current_date.month > 9:
                self.next_due_date = current_date.replace(year=current_date.year + 1, month=current_date.month - 9)
            else:
                self.next_due_date = current_date.replace(month=current_date.month + 3)
        elif self.frequency == 'annually':
            self.next_due_date = current_date.replace(year=current_date.year + 1)
        
        self.save(update_fields=['next_due_date'])
