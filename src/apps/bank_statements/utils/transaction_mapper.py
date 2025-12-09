"""
Transaction Mapper Utility

Standardizes bank transaction data from various sources (GPT parser, CSV imports, 
different bank formats) into a consistent internal structure.

This ensures reliable:
- Reconciliation with invoices
- Calculations (totals, balances)
- Export to accounting software
- Duplicate detection
"""

import re
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)


class TransactionMapper:
    """
    Maps and normalizes bank transactions from various sources to a standardized format.
    
    Standardized Transaction Structure:
    {
        'operation_date': date,           # YYYY-MM-DD (required)
        'value_date': date or None,       # YYYY-MM-DD
        'reference': str or None,         # Transaction reference
        'description': str,               # Main description/label (required)
        'debit': Decimal,                 # Positive value or 0
        'credit': Decimal,                # Positive value or 0
        'category': str,                  # One of VALID_CATEGORIES
        'merchant': str or None,          # Merchant name
        'location': str or None,          # Transaction location
        'beneficiary': str or None,       # For transfers out
        'depositor': str or None,         # For deposits
        'counterparty_name': str or None, # Other party name
        'counterparty_account': str or None, # Other party account
        'time': time or None,             # HH:MM:SS
        'payment_method': str or None,    # Card, check, etc.
    }
    """
    
    # Valid category choices matching the BankTransaction model
    VALID_CATEGORIES = [
        'BANK_FEE', 'ATM_WITHDRAWAL', 'BILL_PAYMENT', 'LOAN_REPAYMENT',
        'TAX', 'TRANSFER_OUT', 'TRANSFER_IN', 'CASH_DEPOSIT',
        'CARD_PAYMENT', 'CHECK_PAYMENT', 'SALARY', 'INTEREST', 'OTHER'
    ]
    
    # Field name mappings for different sources
    # Key: Alternative field name, Value: Standardized field name
    FIELD_MAPPINGS = {
        # Date fields
        'date': 'operation_date',
        'transaction_date': 'operation_date',
        'date_operation': 'operation_date',
        'date_op': 'operation_date',
        'op_date': 'operation_date',
        'date_valeur': 'value_date',
        
        # Description fields
        'label': 'description',
        'libelle': 'description',
        'libellé': 'description',
        'wording': 'description',
        'detail': 'description',
        'details': 'description',
        'transaction_description': 'description',
        
        # Amount fields
        'montant': 'amount',
        'amount': 'amount',
        'somme': 'amount',
        'value': 'amount',
        
        # Reference fields
        'ref': 'reference',
        'num': 'reference',
        'numero': 'reference',
        'transaction_id': 'reference',
        'tx_id': 'reference',
        
        # Category fields
        'type': 'category',
        'transaction_type': 'category',
        'category_code': 'category',
        'categorie': 'category',
        
        # Party fields
        'vendor': 'merchant',
        'payee': 'beneficiary',
        'payer': 'depositor',
        'other_party': 'counterparty_name',
        'counterparty': 'counterparty_name',
    }
    
    # Category keyword mappings for auto-categorization
    CATEGORY_KEYWORDS = {
        'BANK_FEE': ['commission', 'frais', 'fee', 'charge', 'agios', 'intérêts débiteurs'],
        'ATM_WITHDRAWAL': ['retrait', 'withdrawal', 'gab', 'atm', 'dab', 'cash out'],
        'BILL_PAYMENT': ['facture', 'bill', 'iam', 'maroc telecom', 'redal', 'lydec', 'amendis', 'onee'],
        'LOAN_REPAYMENT': ['crédit', 'credit', 'prêt', 'loan', 'remboursement', 'echeance'],
        'TAX': ['taxe', 'tax', 'tva', 'impot', 'impôt', 'timbre', 'dgi', 'fisc'],
        'TRANSFER_OUT': ['virement emis', 'vir emis', 'transfer out', 'virement vers'],
        'TRANSFER_IN': ['virement recu', 'vir recu', 'transfer in', 'virement de'],
        'CASH_DEPOSIT': ['versement', 'depot', 'dépôt', 'deposit', 'cash in'],
        'CARD_PAYMENT': ['carte', 'card', 'paiement carte', 'tpe', 'cb'],
        'CHECK_PAYMENT': ['cheque', 'chèque', 'check'],
        'SALARY': ['salaire', 'salary', 'paie', 'wage', 'vir sal'],
        'INTEREST': ['intérêts', 'interest', 'int créditeurs'],
    }
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize the transaction mapper.
        
        Args:
            strict_mode: If True, raises exceptions for invalid data.
                        If False, logs warnings and uses defaults.
        """
        self.strict_mode = strict_mode
    
    def normalize_transaction(self, raw_tx: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a single transaction from any source format to standardized structure.
        
        Args:
            raw_tx: Raw transaction data (dict with various field names)
            
        Returns:
            dict: Normalized transaction with standardized field names and types
        """
        # Step 1: Map field names to standard names
        mapped_tx = self._map_field_names(raw_tx)
        
        # Step 2: Parse and normalize each field
        normalized = {
            'operation_date': self._parse_date(mapped_tx.get('operation_date')),
            'value_date': self._parse_date(mapped_tx.get('value_date')),
            'reference': self._normalize_string(mapped_tx.get('reference')),
            'description': self._normalize_description(mapped_tx.get('description', '')),
            'debit': Decimal('0.00'),
            'credit': Decimal('0.00'),
            'category': self._normalize_category(mapped_tx),
            'merchant': self._normalize_string(mapped_tx.get('merchant')),
            'location': self._normalize_string(mapped_tx.get('location')),
            'beneficiary': self._normalize_string(mapped_tx.get('beneficiary')),
            'depositor': self._normalize_string(mapped_tx.get('depositor')),
            'counterparty_name': self._normalize_string(mapped_tx.get('counterparty_name')),
            'counterparty_account': self._normalize_string(mapped_tx.get('counterparty_account')),
            'time': self._parse_time(mapped_tx.get('time')),
            'payment_method': self._normalize_string(mapped_tx.get('payment_method')),
        }
        
        # Step 3: Parse amounts (debit/credit)
        debit, credit = self._parse_amounts(mapped_tx)
        normalized['debit'] = debit
        normalized['credit'] = credit
        
        # Step 4: Auto-categorize if category is OTHER or not set
        if normalized['category'] == 'OTHER':
            normalized['category'] = self._auto_categorize(normalized['description'])
        
        return normalized
    
    def normalize_transactions(self, raw_transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize a list of transactions.
        
        Args:
            raw_transactions: List of raw transaction dicts
            
        Returns:
            list: List of normalized transaction dicts
        """
        normalized = []
        for i, raw_tx in enumerate(raw_transactions):
            try:
                normalized.append(self.normalize_transaction(raw_tx))
            except Exception as e:
                logger.warning(f"Failed to normalize transaction {i}: {str(e)}")
                if self.strict_mode:
                    raise
        return normalized
    
    def normalize_statement(self, raw_statement: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a complete statement including all transactions.
        
        Args:
            raw_statement: Raw statement data (may be nested or flat)
            
        Returns:
            dict: Normalized statement with standardized structure
        """
        # Handle nested structure (e.g., from GPT parser)
        stmt = raw_statement.get('statement', raw_statement)
        
        normalized = {
            'account_holder': self._normalize_string(stmt.get('account_holder')),
            'account_number': self._normalize_string(stmt.get('account_number')),
            'bank_name': stmt.get('bank_name'),  # Already normalized by GPT parser
            'branch': self._normalize_string(stmt.get('branch')),
            'iban': self._normalize_string(stmt.get('iban')),
            'period_start': self._parse_date(stmt.get('period_start')),
            'period_end': self._parse_date(stmt.get('period_end')),
            'opening_balance': self._parse_decimal(stmt.get('opening_balance')),
            'closing_balance': self._parse_decimal(stmt.get('closing_balance')),
            'currency': self._normalize_currency(stmt.get('currency')),
            'transactions': self.normalize_transactions(stmt.get('transactions', [])),
        }
        
        return normalized
    
    def _map_field_names(self, raw_tx: Dict[str, Any]) -> Dict[str, Any]:
        """Map alternative field names to standardized names."""
        mapped = {}
        
        for raw_key, value in raw_tx.items():
            # Convert to lowercase for matching
            lower_key = raw_key.lower().strip()
            
            # Check if it's an alternative field name
            if lower_key in self.FIELD_MAPPINGS:
                standard_key = self.FIELD_MAPPINGS[lower_key]
                # Don't overwrite if standard key already exists
                if standard_key not in mapped:
                    mapped[standard_key] = value
            else:
                # Keep original key (in case it's already standard)
                mapped[raw_key] = value
        
        return mapped
    
    def _parse_date(self, value: Any) -> Optional[date]:
        """Parse date from various formats to standard date object."""
        if value is None:
            return None
        
        if isinstance(value, date):
            return value
        
        if isinstance(value, datetime):
            return value.date()
        
        if not isinstance(value, str):
            value = str(value)
        
        value = value.strip()
        if not value:
            return None
        
        # Common date formats to try
        formats = [
            '%Y-%m-%d',      # ISO format: 2025-01-15
            '%d/%m/%Y',      # French format: 15/01/2025
            '%d-%m-%Y',      # 15-01-2025
            '%d.%m.%Y',      # 15.01.2025
            '%Y/%m/%d',      # 2025/01/15
            '%m/%d/%Y',      # US format: 01/15/2025
            '%d %b %Y',      # 15 Jan 2025
            '%d %B %Y',      # 15 January 2025
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {value}")
        return None
    
    def _parse_time(self, value: Any) -> Optional[Any]:
        """Parse time from various formats."""
        if value is None:
            return None
        
        if hasattr(value, 'hour'):  # Already a time object
            return value
        
        if not isinstance(value, str):
            value = str(value)
        
        value = value.strip()
        if not value:
            return None
        
        formats = ['%H:%M:%S', '%H:%M', '%I:%M:%S %p', '%I:%M %p']
        
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).time()
            except ValueError:
                continue
        
        return None
    
    def _parse_decimal(self, value: Any) -> Optional[Decimal]:
        """Parse decimal from various formats."""
        if value is None or value == '':
            return None
        
        if isinstance(value, Decimal):
            return value
        
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        
        if isinstance(value, str):
            # Clean the string
            value = value.strip()
            
            # Remove currency symbols and spaces
            value = re.sub(r'[€$£¥MAD\s]', '', value, flags=re.IGNORECASE)
            
            # Handle European format (1.234,56 -> 1234.56)
            if ',' in value and '.' in value:
                if value.rindex(',') > value.rindex('.'):
                    # European: 1.234,56
                    value = value.replace('.', '').replace(',', '.')
                # else: American format, remove commas
                else:
                    value = value.replace(',', '')
            elif ',' in value:
                # Could be European (1234,56) or thousands separator (1,234)
                parts = value.split(',')
                if len(parts) == 2 and len(parts[1]) == 2:
                    # European decimal
                    value = value.replace(',', '.')
                else:
                    # Thousands separator
                    value = value.replace(',', '')
            
            # Remove any remaining non-numeric characters except - and .
            value = re.sub(r'[^\d.\-]', '', value)
            
            if not value or value == '-':
                return None
            
            try:
                return Decimal(value)
            except InvalidOperation:
                logger.warning(f"Could not parse decimal: {value}")
                return None
        
        return None
    
    def _parse_amounts(self, mapped_tx: Dict[str, Any]) -> tuple:
        """
        Parse debit and credit amounts from various formats.
        
        Handles:
        - Separate debit/credit fields
        - Single amount field with type indicator
        - Negative amounts for debits
        
        Returns:
            tuple: (debit: Decimal, credit: Decimal)
        """
        debit = Decimal('0.00')
        credit = Decimal('0.00')
        
        # Case 1: Already has debit and credit fields
        if 'debit' in mapped_tx or 'credit' in mapped_tx:
            debit = self._parse_decimal(mapped_tx.get('debit', 0)) or Decimal('0.00')
            credit = self._parse_decimal(mapped_tx.get('credit', 0)) or Decimal('0.00')
            
            # Ensure positive values
            debit = abs(debit)
            credit = abs(credit)
            return (debit, credit)
        
        # Case 2: Single amount field with type
        if 'amount' in mapped_tx:
            amount = self._parse_decimal(mapped_tx.get('amount')) or Decimal('0.00')
            tx_type = str(mapped_tx.get('type', '')).lower()
            
            # Determine if debit or credit
            if tx_type in ['debit', 'd', 'db', 'withdrawal', 'expense', 'out']:
                debit = abs(amount)
            elif tx_type in ['credit', 'c', 'cr', 'deposit', 'income', 'in']:
                credit = abs(amount)
            elif amount < 0:
                debit = abs(amount)
            else:
                credit = abs(amount)
            
            return (debit, credit)
        
        # Case 3: Check for Montant (French) with separate columns
        if 'montant_debit' in mapped_tx or 'montant_credit' in mapped_tx:
            debit = self._parse_decimal(mapped_tx.get('montant_debit', 0)) or Decimal('0.00')
            credit = self._parse_decimal(mapped_tx.get('montant_credit', 0)) or Decimal('0.00')
            return (abs(debit), abs(credit))
        
        return (debit, credit)
    
    def _normalize_string(self, value: Any) -> Optional[str]:
        """Normalize string value - strip whitespace, return None for empty."""
        if value is None:
            return None
        
        if not isinstance(value, str):
            value = str(value)
        
        value = ' '.join(value.split())  # Normalize whitespace
        return value if value else None
    
    def _normalize_description(self, value: Any) -> str:
        """Normalize description field - always returns a string."""
        normalized = self._normalize_string(value)
        return normalized if normalized else ''
    
    def _normalize_category(self, mapped_tx: Dict[str, Any]) -> str:
        """Normalize category to valid category code."""
        category = mapped_tx.get('category', '')
        
        if isinstance(category, str):
            category = category.upper().strip()
            category = category.replace(' ', '_').replace('-', '_')
            
            if category in self.VALID_CATEGORIES:
                return category
        
        return 'OTHER'
    
    def _normalize_currency(self, value: Any) -> str:
        """Normalize currency code."""
        if not value:
            return 'MAD'  # Default for Morocco
        
        currency = str(value).upper().strip()
        
        # Map common variations
        currency_map = {
            'DH': 'MAD',
            'DIRHAM': 'MAD',
            'DIRHAMS': 'MAD',
            'درهم': 'MAD',
            'EURO': 'EUR',
            '€': 'EUR',
            'DOLLAR': 'USD',
            '$': 'USD',
        }
        
        return currency_map.get(currency, currency)
    
    def _auto_categorize(self, description: str) -> str:
        """
        Auto-categorize transaction based on description keywords.
        
        Args:
            description: Transaction description
            
        Returns:
            str: Category code
        """
        if not description:
            return 'OTHER'
        
        description_lower = description.lower()
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in description_lower:
                    return category
        
        return 'OTHER'
    
    def get_transaction_type(self, transaction: Dict[str, Any]) -> str:
        """
        Get transaction type (debit/credit) from normalized transaction.
        
        Args:
            transaction: Normalized transaction dict
            
        Returns:
            str: 'debit' or 'credit'
        """
        debit = transaction.get('debit', Decimal('0.00'))
        credit = transaction.get('credit', Decimal('0.00'))
        
        if debit > 0:
            return 'debit'
        return 'credit'
    
    def get_amount(self, transaction: Dict[str, Any]) -> Decimal:
        """
        Get the transaction amount (whichever is non-zero).
        
        Args:
            transaction: Normalized transaction dict
            
        Returns:
            Decimal: The transaction amount
        """
        debit = transaction.get('debit', Decimal('0.00'))
        credit = transaction.get('credit', Decimal('0.00'))
        
        return debit if debit > 0 else credit
    
    def calculate_totals(self, transactions: List[Dict[str, Any]]) -> Dict[str, Decimal]:
        """
        Calculate totals from a list of normalized transactions.
        
        Args:
            transactions: List of normalized transaction dicts
            
        Returns:
            dict: {total_debits, total_credits, net_amount, transaction_count}
        """
        total_debits = sum(tx.get('debit', Decimal('0.00')) for tx in transactions)
        total_credits = sum(tx.get('credit', Decimal('0.00')) for tx in transactions)
        
        return {
            'total_debits': total_debits,
            'total_credits': total_credits,
            'net_amount': total_credits - total_debits,
            'transaction_count': len(transactions),
        }


# Convenience function for quick normalization
def normalize_transaction(raw_tx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Quick normalize a single transaction using default settings.
    
    Args:
        raw_tx: Raw transaction data
        
    Returns:
        dict: Normalized transaction
    """
    mapper = TransactionMapper()
    return mapper.normalize_transaction(raw_tx)


def normalize_transactions(raw_transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Quick normalize a list of transactions using default settings.
    
    Args:
        raw_transactions: List of raw transaction dicts
        
    Returns:
        list: List of normalized transactions
    """
    mapper = TransactionMapper()
    return mapper.normalize_transactions(raw_transactions)
