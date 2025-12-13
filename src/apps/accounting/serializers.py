"""
Serializers for Accounting Export API
"""

from rest_framework import serializers
from datetime import date


class AccountingExportRequestSerializer(serializers.Serializer):
    """Serializer for accounting export request parameters."""
    
    JOURNAL_CHOICES = [
        ('purchases', 'Purchases (Achats)'),
        ('sales', 'Sales (Ventes)'),
        ('all', 'All (Tous)'),
    ]
    
    FORMAT_CHOICES = [
        ('csv', 'CSV (Sage 100 compatible)'),
        ('excel', 'Excel (.xlsx)'),
        ('json', 'JSON (Structured data)'),
        ('ubl', 'UBL/XML (Universal Business Language)'),
    ]
    
    start_date = serializers.DateField(
        required=True,
        help_text="Start date of the export period (YYYY-MM-DD)"
    )
    end_date = serializers.DateField(
        required=True,
        help_text="End date of the export period (YYYY-MM-DD)"
    )
    journal_type = serializers.ChoiceField(
        choices=JOURNAL_CHOICES,
        default='all',
        help_text="Type of journal to export"
    )
    format = serializers.ChoiceField(
        choices=FORMAT_CHOICES,
        default='csv',
        help_text="Export file format"
    )
    
    def validate(self, data):
        """Validate that end_date is not before start_date."""
        if data['end_date'] < data['start_date']:
            raise serializers.ValidationError({
                'end_date': "End date cannot be before start date."
            })
        
        # Don't allow exports more than 1 year
        delta = data['end_date'] - data['start_date']
        if delta.days > 366:
            raise serializers.ValidationError({
                'end_date': "Export period cannot exceed 1 year."
            })
        
        return data


class AccountingExportSummarySerializer(serializers.Serializer):
    """Serializer for export summary response."""
    
    class PeriodSerializer(serializers.Serializer):
        start = serializers.DateField()
        end = serializers.DateField()
    
    class InvoiceCountSerializer(serializers.Serializer):
        purchases = serializers.IntegerField()
        sales = serializers.IntegerField()
        total = serializers.IntegerField()
    
    class TotalsSerializer(serializers.Serializer):
        subtotal = serializers.FloatField()
        vat = serializers.FloatField()
        total = serializers.FloatField()
    
    period = PeriodSerializer()
    journal_type = serializers.CharField()
    invoice_count = InvoiceCountSerializer()
    totals = TotalsSerializer()
    estimated_entries = serializers.IntegerField()


class AccountMappingSerializer(serializers.Serializer):
    """Serializer for viewing/updating account mappings."""
    
    category_name = serializers.CharField(max_length=100)
    account_code = serializers.CharField(max_length=10)
    account_type = serializers.ChoiceField(
        choices=[('expense', 'Expense'), ('revenue', 'Revenue')]
    )
