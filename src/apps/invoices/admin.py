from django.contrib import admin
from .models import (
    Supplier,
    Customer,
    Category,
    PaymentMethod,
    Project,
    Invoice,
    InvoiceLineItem,
    InvoiceAttachment,
    InvoiceEmailLog
)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('corporate_name', 'email', 'telephone', 'mobile', 'business_account')
    search_fields = ('corporate_name', 'commercial_name', 'email', 'telephone', 'mobile')
    list_filter = ('is_small_business', 'country')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('corporate_name', 'email', 'telephone', 'mobile', 'business_account')
    search_fields = ('corporate_name', 'commercial_name', 'email', 'telephone', 'mobile')
    list_filter = ('is_small_business', 'country')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'business_account')
    search_fields = ('name',)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'business_account')
    search_fields = ('name',)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'business_account')
    search_fields = ('name',)


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 1


class InvoiceAttachmentInline(admin.TabularInline):
    model = InvoiceAttachment
    extra = 1


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'invoice_type', 'date', 'due_date', 
                   'supplier', 'customer', 'total', 'is_paid', 'business_account')
    list_filter = ('invoice_type', 'is_paid', 'date', 'due_date')
    search_fields = ('invoice_number', 'reference', 'supplier__corporate_name', 'customer__corporate_name')
    inlines = [InvoiceLineItemInline, InvoiceAttachmentInline]
    readonly_fields = ('subtotal', 'vat_amount', 'total')
    fieldsets = (
        ('Basic Information', {
            'fields': ('invoice_type', 'invoice_number', 'business_account', 'date', 'due_date')
        }),
        ('Parties', {
            'fields': ('supplier', 'customer')
        }),
        ('Categorization', {
            'fields': ('category', 'project')
        }),
        ('Payment Information', {
            'fields': ('is_paid', 'paid_date', 'payment_method', 'payment_communication', 'currency')
        }),
        ('Financial Information', {
            'fields': ('vat_rate', 'subtotal', 'vat_amount', 'total')
        }),
        ('Additional Information', {
            'fields': ('reference', 'supplier_iban', 'about', 'comments', 'internal_notes', 'additional_text_for_pdf')
        }),
        ('Documents', {
            'fields': ('original_document', 'generated_pdf')
        }),
    )


@admin.register(InvoiceEmailLog)
class InvoiceEmailLogAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'recipient', 'subject', 'sent_at', 'sent_by')
    search_fields = ('invoice__invoice_number', 'recipient', 'subject')
    list_filter = ('sent_at',)
    readonly_fields = ('invoice', 'sent_by', 'recipient', 'subject', 'body', 'sent_at')
