import uuid
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.core.files.storage import default_storage
import boto3
from botocore.client import Config
from django.conf import settings

from apps.common.models import BaseModel
from apps.accounts.models import BusinessAccount
from apps.users.models import User


# Add these helper functions at the top of the file, before any model classes
def original_document_path(instance, filename):
    """Generate path for original invoice documents by business account"""
    return f'business/{instance.business_account.id}_{instance.business_account.business_name}/invoices/original/{filename}'

def generated_pdf_path(instance, filename):
    """Generate path for generated invoice PDFs by business account"""
    return f'business/{instance.business_account.id}_{instance.business_account.business_name}/invoices/generated/{filename}'

def invoice_attachment_path(instance, filename):
    """Generate path for invoice attachments by business account"""
    return f'business/{instance.invoice.business_account.id}_{instance.invoice.business_account.business_name}/invoices/attachments/{filename}'


class Supplier(BaseModel):
    """Model to store supplier information for invoices"""
    business_account = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name='suppliers')
    number = models.IntegerField(unique=True, null=True, blank=True)
    corporate_name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    mobile = models.CharField(max_length=20, blank=True, null=True)
    is_small_business = models.BooleanField(default=False)

    # Company informations
    company_name = models.CharField(max_length=255, blank=True, null=True)
    ice_number = models.CharField(max_length=50, blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    commercial_register = models.CharField(max_length=50, blank=True, null=True)
    default_payment_method = models.CharField(max_length=50, blank=True, null=True)
    
    # Invoice Address fields
    country = models.CharField(max_length=100, blank=True, null=True)
    street = models.CharField(max_length=255, blank=True, null=True)
    street_number = models.CharField(max_length=20, blank=True, null=True)
    po_box = models.CharField(max_length=20, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    town_city = models.CharField(max_length=100, blank=True, null=True)
    
    # Delivery Address - Optional fields
    has_different_delivery_address = models.BooleanField(default=False)
    delivery_country = models.CharField(max_length=100, blank=True, null=True)
    delivery_street = models.CharField(max_length=255, blank=True, null=True)
    delivery_street_number = models.CharField(max_length=20, blank=True, null=True)
    delivery_po_box = models.CharField(max_length=20, blank=True, null=True)
    delivery_zip_code = models.CharField(max_length=20, blank=True, null=True)
    delivery_town_city = models.CharField(max_length=100, blank=True, null=True)

    # Customer comments
    comments = models.TextField(blank=True, null=True)
    
    def save(self, *args, **kwargs):
        # Only set number if it's a new object with no number
        if not self.number:
            # Get the max number for this business account
            max_number = Supplier.objects.filter(business_account=self.business_account).aggregate(
                models.Max('number'))['number__max']
            # Set the number to max + 1 or 1 if no existing records
            self.number = (max_number or 0) + 1
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.corporate_name


class Customer(BaseModel):
    """Model to store customer information for invoices"""
    business_account = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name='customers')
    number = models.IntegerField(unique=True, null=True, blank=True)
    corporate_name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    mobile = models.CharField(max_length=20, blank=True, null=True)
    is_small_business = models.BooleanField(default=False)

    # Company informations
    company_name = models.CharField(max_length=255, blank=True, null=True)
    ice_number = models.CharField(max_length=50, blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    commercial_register = models.CharField(max_length=50, blank=True, null=True)
    
    # Invoice Address fields
    country = models.CharField(max_length=100, blank=True, null=True)
    street = models.CharField(max_length=255, blank=True, null=True)
    street_number = models.CharField(max_length=20, blank=True, null=True)
    po_box = models.CharField(max_length=20, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    town_city = models.CharField(max_length=100, blank=True, null=True)
    
    # Delivery Address - Optional fields
    has_different_delivery_address = models.BooleanField(default=False)
    delivery_country = models.CharField(max_length=100, blank=True, null=True)
    delivery_street = models.CharField(max_length=255, blank=True, null=True)
    delivery_street_number = models.CharField(max_length=20, blank=True, null=True)
    delivery_po_box = models.CharField(max_length=20, blank=True, null=True)
    delivery_zip_code = models.CharField(max_length=20, blank=True, null=True)
    delivery_town_city = models.CharField(max_length=100, blank=True, null=True)

    # Customer comments
    comments = models.TextField(blank=True, null=True)
    
    def save(self, *args, **kwargs):
        # Only set number if it's a new object with no number
        if not self.number:
            # Get the max number for this business account
            max_number = Customer.objects.filter(business_account=self.business_account).aggregate(
                models.Max('number'))['number__max']
            # Set the number to max + 1 or 1 if no existing records
            self.number = (max_number or 0) + 1
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.corporate_name


class Category(BaseModel):
    """Model for invoice categories (set-up fees, services, etc.)"""
    business_account = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name='invoice_categories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"


class PaymentMethod(BaseModel):
    """Model for payment methods"""
    business_account = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name='payment_methods')
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return self.name


class Project(BaseModel):
    """Model for projects that can be associated with invoices"""
    STATUS_CHOICES = [
        ('prospect', 'Prospect'),
        ('in_progress', 'In Progress'),
        ('finished', 'Finished'),
        ('canceled', 'Canceled'),
    ]
    
    business_account = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='prospect')
    
    # Customer relationship
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    reference_number = models.CharField(max_length=50, blank=True, null=True, help_text='Customer reference or PO number')
    
    # Budget information
    budget = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    time_budget = models.IntegerField(default=0, help_text='Time budget in hours')
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Project duration
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return self.name
        
    @property
    def used_budget(self):
        """Calculate the used budget based on invoices linked to this project"""
        from django.db.models import Sum
        invoices = Invoice.objects.filter(project=self)
        total = invoices.aggregate(Sum('total'))['total__sum']
        return total or Decimal('0.00')
    
    @property
    def remaining_budget(self):
        """Calculate the remaining budget"""
        return self.budget - self.used_budget


class Article(BaseModel):
    """Model for articles that can be used in invoice line items"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business_account = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name='articles')
    article_number = models.CharField(max_length=50, blank=True, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=50, default='ea')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('21.00'), validators=[MinValueValidator(Decimal('0'))])
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.article_number} - {self.name}" if self.article_number else self.name


class Invoice(BaseModel):
    """Main invoice model"""
    # Basic invoice information
    INVOICE_TYPE_CHOICES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('invoice', 'Invoice'),
        ('credit_note', 'Credit Note'),
    ]
    
    # Payment status choices - separate from delivery (sent) status
    PAYMENT_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('unpaid', 'Unpaid'),
        ('overdue', 'Overdue'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    invoice_type = models.CharField(max_length=20, choices=INVOICE_TYPE_CHOICES)
    invoice_number = models.CharField(max_length=50, editable=False, blank=True)
    
    # Payment status (separate from delivery/sent status)
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='draft',
        help_text='Payment status of the invoice'
    )
    
    # Business account owner of this invoice record
    business_account = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name='invoices')
    
    # Supplier and customer - depending on invoice type, one might be null
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='supplier_invoices')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_invoices')
    
    # Category and project
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Important dates
    date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    paid_date = models.DateField(null=True, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    
    # Payment information
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    
    # Financial information
    currency = models.CharField(max_length=3, default='MAD')
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('20.00'), validators=[MinValueValidator(Decimal('0'))])
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    vat_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Reference information
    reference = models.CharField(max_length=100, blank=True, null=True)
    supplier_iban = models.CharField(max_length=34, blank=True, null=True)
    about = models.TextField(blank=True, null=True)
    
    # Delivery tracking (separate from payment status)
    sent = models.BooleanField(
        default=False,
        help_text='Whether invoice has been sent/delivered to customer'
    )
    sent_to = models.EmailField(blank=True, null=True)
    sent_date = models.DateTimeField(
        null=True, 
        blank=True,
        help_text='When the invoice was sent to customer'
    )
    
    # Additional information
    comments = models.TextField(blank=True, null=True)
    internal_notes = models.TextField(blank=True, null=True)
    additional_text_for_pdf = models.TextField(blank=True, null=True)
    
    # Document handling
    original_document = models.FileField(upload_to=original_document_path, null=True, blank=True)
    generated_pdf = models.FileField(upload_to=generated_pdf_path, null=True, blank=True)
    
    def __str__(self):
        return f"{self.invoice_number} - {self.get_invoice_type_display()}"
    
    def save(self, *args, **kwargs):
        """Override save to auto-generate invoice number"""
        # Only generate number if it's a new invoice without a number
        if not self.invoice_number:
            # Get the current year and month for the prefix
            from datetime import datetime
            current_year = datetime.now().year
            current_month = datetime.now().month
            
            # Define prefix based on invoice type
            if self.invoice_type == 'purchase':
                prefix = f"ACH-{current_year}{current_month:02d}"
            elif self.invoice_type == 'sale':
                prefix = f"VENTE-{current_year}{current_month:02d}"
            elif self.invoice_type == 'credit_note':
                prefix = f"AV-{current_year}{current_month:02d}"
            else:  # invoice or default
                prefix = f"FAC-{current_year}{current_month:02d}"
            
            # Get the max number for this business account, invoice type and period
            max_invoice = Invoice.objects.filter(
                business_account=self.business_account,
                invoice_type=self.invoice_type,
                invoice_number__startswith=prefix
            ).order_by('-invoice_number').first()
            
            if max_invoice:
                # Extract the sequence number from the last invoice
                try:
                    last_sequence = int(max_invoice.invoice_number.split('-')[-1])
                    new_sequence = last_sequence + 1
                except (ValueError, IndexError):
                    # If parsing fails, start from 1
                    new_sequence = 1
            else:
                # First invoice of this type for this period
                new_sequence = 1
            
            # Generate the new invoice number with zero-padding (4 digits)
            self.invoice_number = f"{prefix}-{new_sequence:04d}"
        
        # Auto-calculate payment status based on payment state and due date
        # Only auto-update status if not manually set to 'cancelled'
        if self.status != 'cancelled':
            if self.is_paid:
                self.status = 'paid'
            elif self.sent:
                # Once sent, it's no longer a draft - check if overdue or unpaid
                if self.due_date and timezone.now().date() > self.due_date:
                    self.status = 'overdue'
                else:
                    self.status = 'unpaid'
            # If not sent, keep as draft (don't auto-update)
        
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        """Check if invoice is overdue"""
        return (
            not self.is_paid and 
            self.due_date and 
            timezone.now().date() > self.due_date
        )
    
    def calculate_totals(self):
        """Calculate subtotal, VAT amount, and total from line items"""
        line_items = self.line_items.all()
        self.subtotal = sum(item.price * item.quantity for item in line_items)
        self.vat_amount = self.subtotal * (self.vat_rate / 100)
        self.total = self.subtotal + self.vat_amount
        self.save()
    
    def mark_as_paid(self, paid_date=None):
        """Mark invoice as paid with the given date or current date"""
        self.is_paid = True
        self.paid_date = paid_date or timezone.now().date()
        self.status = 'paid'  # Explicitly set status to paid
        self.save()


class InvoiceLineItem(BaseModel):
    """Model for individual line items on an invoice"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='line_items')
    article = models.ForeignKey(Article, on_delete=models.SET_NULL, null=True, blank=True, related_name='line_items')
    description = models.TextField()
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'))
    price = models.DecimalField(max_digits=10, decimal_places=2)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    unit = models.CharField(max_length=50, null=True, blank=True)
    
    def __str__(self):
        return f"{self.description} ({self.quantity} x {self.price})"
    
    @property
    def line_total(self):
        """Calculate the total for this line item"""
        return self.quantity * self.price
    
    def save(self, *args, **kwargs):
        """Override save to update invoice totals"""
        # If an article is selected and no custom values are set, use article values
        if self.article and not self.pk:  # Only for new items
            if not self.description:
                self.description = self.article.description or self.article.name
            if not self.price:
                self.price = self.article.price
            if not self.vat_rate:
                self.vat_rate = self.article.vat_rate
            if not self.unit:
                self.unit = self.article.unit
                
        super().save(*args, **kwargs)
        self.invoice.calculate_totals()


class InvoiceAttachment(BaseModel):
    """Model for additional attachments to an invoice"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=invoice_attachment_path)
    description = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return f"Attachment for {self.invoice.invoice_number}"


class InvoiceEmailLog(BaseModel):
    """Model to track emails sent regarding invoices"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='email_logs')
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Email for {self.invoice.invoice_number} to {self.recipient}"


class TimeEntry(BaseModel):
    """Model for tracking time spent on projects"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='time_entries')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='time_entries')
    description = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=0, help_text='Duration in minutes')
    is_billable = models.BooleanField(default=True)
    billed = models.BooleanField(default=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='time_entries')
    
    class Meta:
        verbose_name_plural = "Time entries"
    
    def __str__(self):
        return f"Time entry for {self.project.name} by {self.user.get_full_name() or self.user.email}"
    
    def save(self, *args, **kwargs):
        """Calculate duration if both start and end times are available"""
        if self.start_time and self.end_time and not self.duration_minutes:
            # Ensure we have datetime objects to work with
            from datetime import datetime
            from django.utils.dateparse import parse_datetime
            
            start = self.start_time
            end = self.end_time
            
            # Convert string dates to datetime if needed
            if isinstance(start, str):
                start = parse_datetime(start)
            if isinstance(end, str):
                end = parse_datetime(end)
                
            # Update the instance fields with datetime objects
            self.start_time = start
            self.end_time = end
            
            # Calculate duration in minutes
            delta = end - start
            self.duration_minutes = int(delta.total_seconds() / 60)
            
        super().save(*args, **kwargs)
        
    @property
    def hours(self):
        """Return duration in hours (decimal)"""
        return self.duration_minutes / 60
    
    @property
    def billable_amount(self):
        """Calculate billable amount based on project hourly rate"""
        if not self.is_billable or not self.project.hourly_rate:
            return Decimal('0.00')
        return self.project.hourly_rate * Decimal(self.hours)


s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME,
    config=Config(
        connect_timeout=5,
        read_timeout=10,
        retries={'max_attempts': 2}
    )
)
