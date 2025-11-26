from rest_framework import serializers
from decimal import Decimal
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
    Article,
    TimeEntry
)


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        exclude = ['business_account']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        exclude = ['business_account']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        exclude = ['business_account']
        read_only_fields = ['id', 'created_at', 'updated_at']


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        exclude = ['business_account']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProjectSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    customer_name = serializers.SerializerMethodField(read_only=True)
    used_budget = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    remaining_budget = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_hours = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Project
        exclude = ['business_account']
        read_only_fields = ['id', 'created_at', 'updated_at', 'used_budget', 'remaining_budget']
    
    def get_customer_name(self, obj):
        return obj.customer.corporate_name if obj.customer else None
        
    def get_used_budget(self, obj):
        return obj.used_budget
        
    def get_remaining_budget(self, obj):
        return obj.remaining_budget
        
    def get_total_hours(self, obj):
        from django.db.models import Sum
        total_minutes = obj.time_entries.aggregate(Sum('duration_minutes'))['duration_minutes__sum']
        return round(float(total_minutes or 0) / 60, 2)


class ArticleSerializer(serializers.ModelSerializer):    
    class Meta:
        model = Article
        exclude = ['business_account']
        read_only_fields = ['id', 'created_at', 'updated_at']


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    article_details = ArticleSerializer(source='article', read_only=True)
    
    class Meta:
        model = InvoiceLineItem
        exclude = ['invoice']
        read_only_fields = ['id', 'created_at', 'updated_at']


class InvoiceAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceAttachment
        exclude = ['invoice']
        read_only_fields = ['id', 'created_at', 'updated_at']


class InvoiceEmailLogSerializer(serializers.ModelSerializer):
    sent_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = InvoiceEmailLog
        exclude = ['invoice']
        read_only_fields = ['id', 'sent_by', 'recipient', 'subject', 'body', 'sent_at', 'created_at', 'updated_at']
    
    def get_sent_by_name(self, obj):
        if obj.sent_by:
            return obj.sent_by.get_full_name() or obj.sent_by.email
        return None


class InvoiceSerializer(serializers.ModelSerializer):
    """Simplified serializer for list view"""
    supplier_name = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    project_name = serializers.SerializerMethodField()
    payment_method_name = serializers.SerializerMethodField()
    invoice_type_display = serializers.CharField(source='get_invoice_type_display', read_only=True)
    supplier_details = SupplierSerializer(source='supplier', read_only=True)
    customer_details = CustomerSerializer(source='customer', read_only=True)
    
    class Meta:
        model = Invoice
        exclude = ['business_account', 'supplier_iban', 'about', 'comments', 'internal_notes', 
                  'additional_text_for_pdf', 'original_document', 'generated_pdf']
        read_only_fields = ['id', 'invoice_number', 'subtotal', 'vat_amount', 'total', 'created_at', 'updated_at']
    
    def get_supplier_name(self, obj):
        return obj.supplier.corporate_name if obj.supplier else None
    
    def get_customer_name(self, obj):
        return obj.customer.corporate_name if obj.customer else None
    
    def get_category_name(self, obj):
        return obj.category.name if obj.category else None
    
    def get_project_name(self, obj):
        return obj.project.name if obj.project else None
    
    def get_payment_method_name(self, obj):
        return obj.payment_method.name if obj.payment_method else None


class InvoiceDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for retrieve view"""
    supplier_name = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    project_name = serializers.SerializerMethodField()
    payment_method_name = serializers.SerializerMethodField()
    invoice_type_display = serializers.CharField(source='get_invoice_type_display', read_only=True)
    line_items = InvoiceLineItemSerializer(many=True, read_only=True)
    attachments = InvoiceAttachmentSerializer(many=True, read_only=True)
    email_logs = InvoiceEmailLogSerializer(many=True, read_only=True)
    supplier_details = SupplierSerializer(source='supplier', read_only=True)
    customer_details = CustomerSerializer(source='customer', read_only=True)
    category_details = CategorySerializer(source='category', read_only=True)
    project_details = ProjectSerializer(source='project', read_only=True)
    payment_method_details = PaymentMethodSerializer(source='payment_method', read_only=True)
    
    class Meta:
        model = Invoice
        exclude = ['business_account']
        read_only_fields = ['id', 'invoice_number', 'subtotal', 'vat_amount', 'total', 'created_at', 'updated_at']
    
    def get_supplier_name(self, obj):
        return obj.supplier.corporate_name if obj.supplier else None
    
    def get_customer_name(self, obj):
        return obj.customer.corporate_name if obj.customer else None
    
    def get_category_name(self, obj):
        return obj.category.name if obj.category else None
    
    def get_project_name(self, obj):
        return obj.project.name if obj.project else None
    
    def get_payment_method_name(self, obj):
        return obj.payment_method.name if obj.payment_method else None
    
    def create(self, validated_data):
        """Create invoice with line items"""
        line_items_data = self.context['request'].data.get('line_items', [])
        
        # Set invoice type if specified
        if 'invoice_type' not in validated_data and self.context['request'].query_params.get('invoice_type'):
            validated_data['invoice_type'] = self.context['request'].query_params.get('invoice_type')
        
        # Create the invoice
        invoice = Invoice.objects.create(**validated_data)
        
        # Create line items
        for item_data in line_items_data:
            InvoiceLineItem.objects.create(invoice=invoice, **item_data)
        
        # Calculate totals
        invoice.calculate_totals()
        
        # Set the original document if provided in request
        if 'original_document' in self.context['request'].FILES:
            invoice.original_document = self.context['request'].FILES['original_document']
            invoice.save()
        
        return invoice
    
    def update(self, instance, validated_data):
        """Update invoice with line items"""
        # Update the invoice
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Handle line items if provided
        line_items_data = self.context['request'].data.get('line_items')
        if line_items_data is not None:
            # Clear existing items if we're explicitly providing a new set
            instance.line_items.all().delete()
            
            # Create new items
            for item_data in line_items_data:
                InvoiceLineItem.objects.create(invoice=instance, **item_data)
            
            # Recalculate totals
            instance.calculate_totals()
        
        # Update the original document if provided
        if 'original_document' in self.context['request'].FILES:
            instance.original_document = self.context['request'].FILES['original_document']
            instance.save()
            
        return instance


class TimeEntrySerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField(read_only=True)
    project_name = serializers.SerializerMethodField(read_only=True)
    hours = serializers.FloatField(read_only=True)
    billable_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = TimeEntry
        exclude = []
        read_only_fields = ['id', 'created_at', 'updated_at', 'hours', 'billable_amount']
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email
    
    def get_project_name(self, obj):
        return obj.project.name