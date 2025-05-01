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
    InvoiceEmailLog,
    Article
)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('corporate_name', 'email', 'telephone', 'country')
    search_fields = ('corporate_name', 'email', 'ice_number', 'tax_id')
    list_filter = ('country', 'is_small_business')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('corporate_name', 'email', 'telephone', 'country')
    search_fields = ('corporate_name', 'email', 'ice_number', 'tax_id')
    list_filter = ('country', 'is_small_business')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('article_number', 'name', 'price', 'is_active')
    search_fields = ('name', 'article_number', 'description')
    list_filter = ('article_number','is_active')


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 1


class InvoiceAttachmentInline(admin.TabularInline):
    model = InvoiceAttachment
    extra = 1


class InvoiceEmailLogInline(admin.TabularInline):
    model = InvoiceEmailLog
    readonly_fields = ('sent_by', 'recipient', 'subject', 'body', 'sent_at')
    extra = 0
    can_delete = False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'invoice_type', 'date', 'due_date', 'is_paid', 'total')
    list_filter = ('invoice_type', 'is_paid', 'date')
    search_fields = ('invoice_number', 'reference', 'supplier__corporate_name', 'customer__corporate_name')
    readonly_fields = ('subtotal', 'vat_amount', 'total')
    inlines = [InvoiceLineItemInline, InvoiceAttachmentInline, InvoiceEmailLogInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('invoice_type', 'invoice_number', 'business_account', 'date', 'due_date')
        }),
        ('Parties', {
            'fields': ('supplier', 'customer', 'category', 'project')
        }),
        ('Financial Information', {
            'fields': ('currency', 'vat_rate', 'subtotal', 'vat_amount', 'total', 'is_paid', 'paid_date')
        }),
        ('Additional Information', {
            'fields': ('reference', 'supplier_iban', 'about', 'comments', 'internal_notes', 'additional_text_for_pdf')
        }),
        ('Documents', {
            'fields': ('original_document', 'generated_pdf')
        }),
    )


@admin.register(InvoiceLineItem)
class InvoiceLineItemAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'description', 'quantity', 'price', 'line_total')
    search_fields = ('description', 'invoice__invoice_number')
    list_filter = ('invoice__invoice_type',)


@admin.register(InvoiceAttachment)
class InvoiceAttachmentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'description', 'file')
    search_fields = ('description', 'invoice__invoice_number')


@admin.register(InvoiceEmailLog)
class InvoiceEmailLogAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'recipient', 'subject', 'sent_at')
    search_fields = ('recipient', 'subject', 'invoice__invoice_number')
    readonly_fields = ('sent_by', 'invoice', 'recipient', 'subject', 'body', 'sent_at')
