import uuid
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator

from apps.common.models import BaseModel
from apps.accounts.models import BusinessAccount
from apps.users.models import User


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
    business_account = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name


class Invoice(BaseModel):
    """Main invoice model"""
    # Basic invoice information
    INVOICE_TYPE_CHOICES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('invoice', 'Invoice'),
        ('credit_note', 'Credit Note'),
    ]
    invoice_type = models.CharField(max_length=20, choices=INVOICE_TYPE_CHOICES)
    invoice_number = models.CharField(max_length=50)
    
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
    payment_communication = models.CharField(max_length=255, null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    
    # Financial information
    currency = models.CharField(max_length=3, default='USD')
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=21.00, validators=[MinValueValidator(0)])
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    vat_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Reference information
    reference = models.CharField(max_length=100, blank=True, null=True)
    supplier_iban = models.CharField(max_length=34, blank=True, null=True)
    about = models.TextField(blank=True, null=True)
    
    # Additional information
    sent = models.BooleanField(default=False)
    comments = models.TextField(blank=True, null=True)
    internal_notes = models.TextField(blank=True, null=True)
    additional_text_for_pdf = models.TextField(blank=True, null=True)
    
    # Document handling
    original_document = models.FileField(upload_to='invoices/', null=True, blank=True)
    generated_pdf = models.FileField(upload_to='invoices/generated/', null=True, blank=True)
    
    def __str__(self):
        return f"{self.invoice_number} - {self.get_invoice_type_display()}"
    
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
        self.save()


class InvoiceLineItem(BaseModel):
    """Model for individual line items on an invoice"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='line_items')
    description = models.TextField()
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    def __str__(self):
        return f"{self.description} ({self.quantity} x {self.price})"
    
    @property
    def line_total(self):
        """Calculate the total for this line item"""
        return self.quantity * self.price
    
    def save(self, *args, **kwargs):
        """Override save to update invoice totals"""
        super().save(*args, **kwargs)
        self.invoice.calculate_totals()


class InvoiceAttachment(BaseModel):
    """Model for additional attachments to an invoice"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='invoice_attachments/')
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
