"""
Invoice Matcher Service

Provides intelligent matching between bank transactions and invoices
based on amount, date, description, and reference similarity.
"""

import logging
from decimal import Decimal
from datetime import timedelta
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher

from django.db.models import Q
from django.utils import timezone

from apps.invoices.models import Invoice

logger = logging.getLogger(__name__)


class InvoiceMatcher:
    """
    Matches bank transactions with unpaid invoices using a scoring system.
    
    Scoring Criteria:
    - Exact amount match: 50 points
    - Close amount (±5%): 30 points
    - Reference match: 30 points
    - Date proximity (≤3 days): 25 points
    - Date proximity (≤7 days): 15 points
    - Date proximity (≤30 days): 5 points
    - Name in description: 20 points
    
    Confidence Levels:
    - High (70-100): Strong match - auto-suggest
    - Medium (40-69): Possible match - review needed
    - Low (1-39): Weak match - unlikely
    """
    
    # Scoring weights
    EXACT_AMOUNT_SCORE = 50
    CLOSE_AMOUNT_SCORE = 30
    REFERENCE_MATCH_SCORE = 30
    DATE_3_DAYS_SCORE = 25
    DATE_7_DAYS_SCORE = 15
    DATE_30_DAYS_SCORE = 5
    NAME_MATCH_SCORE = 20
    DESCRIPTION_SIMILARITY_SCORE = 15
    
    # Thresholds
    AMOUNT_TOLERANCE = Decimal('0.05')  # 5% tolerance for close matches
    MIN_SCORE_THRESHOLD = 20  # Minimum score to consider a match
    
    def __init__(self, business_account):
        """
        Initialize the matcher with a business account context.
        
        Args:
            business_account: BusinessAccount instance to scope invoice queries
        """
        self.business_account = business_account
    
    def find_matches(self, transaction, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find potential invoice matches for a bank transaction.
        
        Args:
            transaction: BankTransaction instance
            limit: Maximum number of matches to return
            
        Returns:
            list: List of match dicts sorted by score (highest first)
        """
        # Determine if we're looking for supplier or customer invoices
        # based on transaction type (debit = expense, credit = income)
        is_expense = transaction.debit > 0
        transaction_amount = transaction.debit if is_expense else transaction.credit
        
        # Get relevant unpaid invoices
        invoices = self._get_candidate_invoices(is_expense)
        
        matches = []
        for invoice in invoices:
            score, reasons = self._calculate_match_score(
                transaction, invoice, transaction_amount, is_expense
            )
            
            if score >= self.MIN_SCORE_THRESHOLD:
                matches.append({
                    'invoice': invoice,
                    'score': score,
                    'reasons': reasons,
                    'confidence': self._get_confidence_level(score),
                })
        
        # Sort by score descending
        matches.sort(key=lambda x: x['score'], reverse=True)
        
        return matches[:limit]
    
    def _get_candidate_invoices(self, is_expense: bool) -> List[Invoice]:
        """
        Get candidate invoices for matching based on transaction type.
        
        Args:
            is_expense: True for debit (expense), False for credit (income)
            
        Returns:
            QuerySet of Invoice objects
        """
        # Include draft, unpaid, and overdue invoices (exclude paid and cancelled)
        queryset = Invoice.objects.filter(
            business_account=self.business_account,
            status__in=['draft', 'unpaid', 'overdue']
        )
        
        if is_expense:
            # Debit transaction → Match with purchase invoices (supplier invoices)
            queryset = queryset.filter(invoice_type='purchase')
        else:
            # Credit transaction → Match with sale invoices (customer invoices)
            queryset = queryset.filter(invoice_type='sale')
        
        return queryset.select_related('supplier', 'customer')[:100]  # Limit for performance
    
    def _calculate_match_score(
        self,
        transaction,
        invoice: Invoice,
        transaction_amount: Decimal,
        is_expense: bool
    ) -> tuple:
        """
        Calculate match score between transaction and invoice.
        
        Returns:
            tuple: (score: int, reasons: list[str])
        """
        score = 0
        reasons = []
        
        invoice_amount = invoice.total or Decimal('0.00')
        
        # 1. Amount matching
        amount_score, amount_reason = self._score_amount_match(
            transaction_amount, invoice_amount
        )
        score += amount_score
        if amount_reason:
            reasons.append(amount_reason)
        
        # 2. Date proximity
        date_score, date_reason = self._score_date_proximity(
            transaction.operation_date, invoice.due_date
        )
        score += date_score
        if date_reason:
            reasons.append(date_reason)
        
        # 3. Reference matching
        ref_score, ref_reason = self._score_reference_match(
            transaction.reference, invoice.invoice_number, invoice.reference
        )
        score += ref_score
        if ref_reason:
            reasons.append(ref_reason)
        
        # 4. Name matching in description
        name_score, name_reason = self._score_name_match(
            transaction.description, invoice, is_expense
        )
        score += name_score
        if name_reason:
            reasons.append(name_reason)
        
        # 5. Description similarity (if counterparty matches)
        desc_score, desc_reason = self._score_description_similarity(
            transaction.description, invoice.about
        )
        score += desc_score
        if desc_reason:
            reasons.append(desc_reason)
        
        return score, reasons
    
    def _score_amount_match(
        self, transaction_amount: Decimal, invoice_amount: Decimal
    ) -> tuple:
        """Score based on amount match."""
        if transaction_amount == Decimal('0.00') or invoice_amount == Decimal('0.00'):
            return 0, None
        
        # Exact match
        if transaction_amount == invoice_amount:
            return self.EXACT_AMOUNT_SCORE, "exact_amount"
        
        # Close match (within tolerance)
        difference = abs(transaction_amount - invoice_amount)
        tolerance = invoice_amount * self.AMOUNT_TOLERANCE
        
        if difference <= tolerance:
            return self.CLOSE_AMOUNT_SCORE, "close_amount"
        
        return 0, None
    
    def _score_date_proximity(self, transaction_date, invoice_due_date) -> tuple:
        """Score based on date proximity."""
        if not transaction_date or not invoice_due_date:
            return 0, None
        
        days_diff = abs((transaction_date - invoice_due_date).days)
        
        if days_diff <= 3:
            return self.DATE_3_DAYS_SCORE, "date_close"
        elif days_diff <= 7:
            return self.DATE_7_DAYS_SCORE, "date_within_week"
        elif days_diff <= 30:
            return self.DATE_30_DAYS_SCORE, "date_within_month"
        
        return 0, None
    
    def _score_reference_match(
        self, tx_reference: Optional[str], invoice_number: str, invoice_reference: Optional[str]
    ) -> tuple:
        """Score based on reference/invoice number match."""
        if not tx_reference:
            return 0, None
        
        tx_ref_lower = tx_reference.lower()
        
        # Check if invoice number is in transaction reference
        if invoice_number and invoice_number.lower() in tx_ref_lower:
            return self.REFERENCE_MATCH_SCORE, "reference_match"
        
        # Check if invoice reference is in transaction reference
        if invoice_reference and invoice_reference.lower() in tx_ref_lower:
            return self.REFERENCE_MATCH_SCORE, "reference_match"
        
        return 0, None
    
    def _score_name_match(
        self, description: str, invoice: Invoice, is_expense: bool
    ) -> tuple:
        """Score based on supplier/customer name in transaction description."""
        if not description:
            return 0, None
        
        desc_lower = description.lower()
        
        # Get party name based on invoice type
        if is_expense and invoice.supplier:
            party_name = invoice.supplier.corporate_name
        elif not is_expense and invoice.customer:
            party_name = invoice.customer.corporate_name
        else:
            return 0, None
        
        if not party_name:
            return 0, None
        
        # Check if party name or parts of it appear in description
        party_lower = party_name.lower()
        
        # Full name match
        if party_lower in desc_lower:
            return self.NAME_MATCH_SCORE, "name_match"
        
        # Partial name match (first word)
        first_word = party_lower.split()[0] if party_lower.split() else ""
        if len(first_word) >= 3 and first_word in desc_lower:
            return self.NAME_MATCH_SCORE // 2, "partial_name_match"
        
        return 0, None
    
    def _score_description_similarity(
        self, tx_description: Optional[str], invoice_about: Optional[str]
    ) -> tuple:
        """Score based on description text similarity."""
        if not tx_description or not invoice_about:
            return 0, None
        
        # Use sequence matcher for similarity
        similarity = SequenceMatcher(
            None, tx_description.lower(), invoice_about.lower()
        ).ratio()
        
        if similarity > 0.5:
            return self.DESCRIPTION_SIMILARITY_SCORE, "description_similar"
        
        return 0, None
    
    def _get_confidence_level(self, score: int) -> str:
        """Get confidence level based on score."""
        if score >= 70:
            return 'high'
        elif score >= 40:
            return 'medium'
        else:
            return 'low'
    
    def reconcile_transaction_with_invoice(
        self, transaction, invoice: Invoice, user
    ) -> Dict[str, Any]:
        """
        Link a bank transaction to an invoice and update both statuses.
        
        Args:
            transaction: BankTransaction instance
            invoice: Invoice instance to link
            user: User performing the reconciliation
            
        Returns:
            dict: Result with updated transaction and invoice
        """
        # Update transaction
        transaction.matched_invoice = invoice
        transaction.is_reconciled = True
        transaction.reconciled_at = timezone.now()
        transaction.reconciled_by = user
        transaction.save()
        
        # Update invoice status to paid
        invoice.status = 'paid'
        invoice.paid_date = transaction.operation_date
        invoice.is_paid = True
        invoice.save()
        
        logger.info(
            f"Reconciled transaction {transaction.id} with invoice {invoice.id} "
            f"by user {user.id}"
        )
        
        return {
            'transaction_id': str(transaction.id),
            'invoice_id': str(invoice.id),
            'status': 'reconciled',
            'reconciled_at': transaction.reconciled_at,
        }
    
    def unreconcile_transaction(self, transaction, user) -> Dict[str, Any]:
        """
        Remove reconciliation link and reset invoice status.
        
        Args:
            transaction: BankTransaction instance
            user: User performing the action
            
        Returns:
            dict: Result with updated transaction
        """
        invoice = transaction.matched_invoice
        
        # Reset transaction
        transaction.matched_invoice = None
        transaction.is_reconciled = False
        transaction.reconciled_at = None
        transaction.reconciled_by = None
        transaction.save()
        
        # Reset invoice status if it was linked
        if invoice:
            invoice.status = 'unpaid'
            invoice.paid_date = None
            invoice.is_paid = False
            invoice.save()
            
            logger.info(
                f"Unreconciled transaction {transaction.id} from invoice {invoice.id} "
                f"by user {user.id}"
            )
        
        return {
            'transaction_id': str(transaction.id),
            'status': 'unreconciled',
        }


# Match reason labels for frontend display
MATCH_REASON_LABELS = {
    'exact_amount': 'Exact amount match',
    'close_amount': 'Amount within 5%',
    'date_close': 'Date within 3 days',
    'date_within_week': 'Date within a week',
    'date_within_month': 'Date within a month',
    'reference_match': 'Invoice reference found',
    'name_match': 'Party name matches',
    'partial_name_match': 'Partial name match',
    'description_similar': 'Description similarity',
}

MATCH_REASON_LABELS_FR = {
    'exact_amount': 'Montant exact',
    'close_amount': 'Montant proche (±5%)',
    'date_close': 'Date proche (3 jours)',
    'date_within_week': 'Date proche (7 jours)',
    'date_within_month': 'Date proche (30 jours)',
    'reference_match': 'Référence facture trouvée',
    'name_match': 'Nom correspondant',
    'partial_name_match': 'Nom partiellement correspondant',
    'description_similar': 'Description similaire',
}
