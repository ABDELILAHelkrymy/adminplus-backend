# Generated migration for invoice status tracking
from django.db import migrations, models
from django.utils import timezone


def set_initial_status(apps, schema_editor):
    """Set initial status values for existing invoices based on is_paid and sent fields"""
    Invoice = apps.get_model('invoices', 'Invoice')
    today = timezone.now().date()
    
    for invoice in Invoice.objects.all():
        if invoice.is_paid:
            invoice.status = 'paid'
        elif invoice.sent:
            # Check if overdue
            if invoice.due_date and invoice.due_date < today:
                invoice.status = 'overdue'
            else:
                invoice.status = 'unpaid'
        else:
            # Not sent, treat as unpaid (or draft if you prefer)
            invoice.status = 'unpaid'
        
        # Don't call save() here to avoid triggering the model's save logic
        Invoice.objects.filter(pk=invoice.pk).update(status=invoice.status)


def reverse_status(apps, schema_editor):
    """Reverse migration - no action needed"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0015_alter_invoice_invoice_number'),  # Update this to your last migration
    ]

    operations = [
        # Add status field
        migrations.AddField(
            model_name='invoice',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('unpaid', 'Unpaid'),
                    ('overdue', 'Overdue'),
                    ('paid', 'Paid'),
                    ('cancelled', 'Cancelled')
                ],
                default='draft',
                help_text='Payment status of the invoice',
                max_length=20
            ),
        ),
        # Add sent_date field
        migrations.AddField(
            model_name='invoice',
            name='sent_date',
            field=models.DateTimeField(
                blank=True,
                help_text='When the invoice was sent to customer',
                null=True
            ),
        ),
        # Update sent field help text
        migrations.AlterField(
            model_name='invoice',
            name='sent',
            field=models.BooleanField(
                default=False,
                help_text='Whether invoice has been sent/delivered to customer'
            ),
        ),
        # Run data migration to set initial status values
        migrations.RunPython(set_initial_status, reverse_status),
    ]
