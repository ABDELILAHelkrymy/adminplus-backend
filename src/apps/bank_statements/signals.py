from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.invoices.models import Invoice
from apps.bank_statements.models import BankTransaction
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Invoice)
def unlink_transactions_on_unpaid(sender, instance, created, **kwargs):
    """
    When an invoice is marked as 'unpaid', unlink any reconciled bank transactions.
    """
    print(f"[SIGNAL DEBUG] Invoice post_save fired: id={instance.id}, status={instance.status}, created={created}")
    logger.info(f"[SIGNAL DEBUG] Invoice post_save fired: id={instance.id}, status={instance.status}, created={created}")
    
    if created:
        return

    # Check if status matches 'unpaid', 'overdue', or 'draft' (i.e., NOT 'paid')
    if instance.status in ['unpaid', 'overdue', 'draft']:
        # Find transactions linked to this invoice
        linked_transactions = BankTransaction.objects.filter(matched_invoice=instance)
        
        if linked_transactions.exists():
            count = linked_transactions.count()
            logger.info(f"Unlinking {count} transactions from invoice {instance.invoice_number} (status: {instance.status})")
            
            # Update each transaction efficiently
            # We don't use update() for all fields because we want to trigger individual save signals 
            # if we add more logic later, but for now update() is safer to avoid looping signals
            # However, looking at the plan, we want to be careful.
            # Let's simple iterate and save to be safe and consistent with model logic if any.
            
            for transaction in linked_transactions:
                transaction.matched_invoice = None
                transaction.is_reconciled = False
                transaction.reconciled_at = None
                transaction.reconciled_by = None
                transaction.save()
                
                logger.info(f"Unlinked transaction {transaction.id} from invoice {instance.id}")
