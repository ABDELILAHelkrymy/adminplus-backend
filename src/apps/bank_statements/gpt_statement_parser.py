import json
import logging
from decimal import Decimal, InvalidOperation
from typing import Dict, Any
from openai import OpenAI
from django.conf import settings

from .utils import TransactionMapper

logger = logging.getLogger(__name__)


class GPTStatementParser:
    """
    AI-powered bank statement parser using GPT
    """

    def __init__(self, debug: bool = False):
        """Initialize the GPT parser with API key"""
        self.api_key = getattr(settings, 'GPT_API_KEY', None) or getattr(settings, 'OPENAI_API_KEY', None)
        if not self.api_key:
            raise ValueError("GPT_API_KEY or OPENAI_API_KEY is not configured in settings")
        self.client = OpenAI(api_key=self.api_key, timeout=90.0)  # 90 second timeout
        self.debug = debug

    def extract_statement_data(self, text: str) -> Dict[str, Any]:
        """
        Extract structured data from bank statement text using GPT
        
        Args:
            text: Extracted text from bank statement file
            
        Returns:
            dict: Structured bank statement data
        """
        try:
            prompt = self._create_extraction_prompt(text)
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo-16k",  # Faster than GPT-4 and handles longer context
                messages=[
                    {
                        "role": "system",
                        "content": """You are a financial document analysis expert specializing in bank statement data extraction.
                        Extract key information and return it in exact JSON format.
                        Follow these rules:
                        1. Return ONLY valid JSON, no markdown formatting
                        2. Use null for missing values
                        3. Format monetary values as numbers (not strings)
                        4. Extract ALL transactions visible in the statement
                        5. Categorize transactions appropriately
                        6. Identify merchants, locations, and beneficiaries
                        7. Be precise with dates (YYYY-MM-DD format)
                        8. For amounts, debit should be positive, credit should be positive
                        9. ALWAYS extract the bank name from the header/logo (in French or Arabic)
                        10. For Moroccan banks, detect currency as MAD (may appear as DH, Dirham, or MAD)
                        """
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            content = response.choices[0].message.content.strip()
            if self.debug:
                logger.debug(f"Raw GPT response: {content}")

            extracted_data = self._parse_gpt_response(content)
            result = self._post_process(extracted_data)
            
            return result

        except Exception as e:
            logger.error(f"Error in GPT statement parsing: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def _create_extraction_prompt(self, text: str) -> str:
        """Create detailed prompt for GPT extraction"""
        return f"""
Extract all information from this bank statement and return ONLY a JSON object with this exact structure:

{{
  "statement": {{
    "account_holder": "string or null",
    "account_number": "string or null",
    "bank_name": "string or null",
    "branch": "string or null",
    "period_start": "YYYY-MM-DD or null",
    "period_end": "YYYY-MM-DD or null",
    "opening_balance": number or null,
    "closing_balance": number or null,
    "currency": "MAD|EUR|USD|GBP or null (detect from statement, default MAD for Morocco)",
    "transactions": [
      {{
        "operation_date": "YYYY-MM-DD",
        "value_date": "YYYY-MM-DD or null",
        "reference": "string or null",
        "description": "string",
        "category": "BANK_FEE|ATM_WITHDRAWAL|BILL_PAYMENT|LOAN_REPAYMENT|TAX|TRANSFER_OUT|TRANSFER_IN|CASH_DEPOSIT|CARD_PAYMENT|CHECK_PAYMENT|SALARY|INTEREST|OTHER",
        "debit": number (0 if credit transaction),
        "credit": number (0 if debit transaction),
        "merchant": "string or null",
        "location": "string or null",
        "beneficiary": "string or null (for transfers)",
        "depositor": "string or null (for deposits)",
        "time": "HH:MM:SS or null"
      }}
    ]
  }}
}}

Category Guidelines:
- BANK_FEE: Commission, fees, charges
- ATM_WITHDRAWAL: Cash withdrawals from ATM
- BILL_PAYMENT: Payment of bills, taxes, utilities
- LOAN_REPAYMENT: Credit/loan repayments
- TAX: Tax payments (TVA, stamp duty, etc.)
- TRANSFER_OUT: Money sent to others (virements)
- TRANSFER_IN: Money received from others
- CASH_DEPOSIT: Cash deposits (versement)
- CARD_PAYMENT: Card purchases
- CHECK_PAYMENT: Check payments
- SALARY: Salary payments
- INTEREST: Interest earned/paid
- OTHER: Anything else

Important Rules:
1. Extract ALL visible transactions
2. For each transaction, set either debit OR credit (not both)
3. Dates must be in YYYY-MM-DD format
4. Numbers should be numeric values, not strings
5. Extract merchant names, locations from descriptions when possible
6. For transfers, identify beneficiary/depositor names
7. Extract time if visible in format HH:MM:SS
8. **CRITICAL**: Always extract bank_name from the document header/logo/top of page:
   - Look for: BANQUE POPULAIRE, Attijariwafa Bank, BMCE, BMCI, CIH Bank, Crédit Agricole, 
     Société Générale, CDM, Al Barid Bank, Bank of Africa, CFG Bank, Umnia Bank, etc.
   - Bank name may appear in French, Arabic (البنك الشعبي, بنك المغرب, etc.), or both
   - Extract the French name when available
9. **CRITICAL**: Detect currency from statement (look for MAD, DH, Dirham, درهم, EUR, €, USD, $, etc.)
   - Default to MAD for Moroccan banks (BANQUE POPULAIRE, Attijariwafa, BMCE, CIH, etc.)
10. **CRITICAL**: Always extract the account_number (numéro de compte, N° compte, رقم الحساب):
   - Look for patterns like: 007 123 456 789 00 24, RIB, account number, N° compte
   - It's usually a 24-digit number for Moroccan banks (RIB format)
   - May appear as: "Compte: XXXXX" or "N° Compte: XXXXX" or "Account Number: XXXXX"
   - Remove spaces/dashes and extract the full number
11. **CRITICAL**: Extract account_holder (titulaire du compte, صاحب الحساب):
   - Look for client name at the top of the statement
   - May appear as "Client:", "Titulaire:", or near the address
12. Return ONLY the JSON object, no extra text or markdown

Bank Statement Content:
{text}
"""

    def _parse_gpt_response(self, response: str) -> Dict[str, Any]:
        """Parse GPT API response to JSON"""
        try:
            cleaned_response = response.strip()
            
            # Remove markdown code blocks if present
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            
            cleaned_response = cleaned_response.strip()
            
            return json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}\nResponse: {response}")
            raise ValueError("GPT returned invalid JSON")

    def _post_process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and convert numerical values using TransactionMapper"""
        def parse_decimal(val):
            try:
                if val is None or val == '':
                    return None
                return Decimal(str(val))
            except (ValueError, InvalidOperation, TypeError):
                return None

        statement = data.get('statement', {})
        
        # Normalize bank_name to match predefined list
        detected_bank = statement.get('bank_name', '').upper() if statement.get('bank_name') else ''
        statement['bank_name'] = self._normalize_bank_name(detected_bank)
        
        # Ensure currency is populated (default MAD for Morocco)
        if not statement.get('currency'):
            statement['currency'] = 'MAD'
            logger.info("Currency not detected, defaulting to MAD")
        
        # Process balance values
        if 'opening_balance' in statement:
            statement['opening_balance'] = parse_decimal(statement['opening_balance'])
        if 'closing_balance' in statement:
            statement['closing_balance'] = parse_decimal(statement['closing_balance'])
        
        # Use TransactionMapper to normalize transactions
        mapper = TransactionMapper()
        raw_transactions = statement.get('transactions', [])
        normalized_transactions = []
        
        for raw_tx in raw_transactions:
            try:
                normalized = mapper.normalize_transaction(raw_tx)
                normalized_transactions.append(normalized)
            except Exception as e:
                logger.warning(f"Failed to normalize transaction in GPT parser: {str(e)}")
                # Fallback: keep raw transaction with basic processing
                raw_tx['debit'] = parse_decimal(raw_tx.get('debit', 0)) or Decimal('0.00')
                raw_tx['credit'] = parse_decimal(raw_tx.get('credit', 0)) or Decimal('0.00')
                if raw_tx.get('category') not in mapper.VALID_CATEGORIES:
                    raw_tx['category'] = 'OTHER'
                normalized_transactions.append(raw_tx)
        
        statement['transactions'] = normalized_transactions
        
        return data
    
    def _normalize_bank_name(self, detected_name: str) -> str:
        """
        Normalize detected bank name to match predefined list
        
        Args:
            detected_name: Bank name detected by GPT (may be in various formats)
            
        Returns:
            str: Normalized bank code from MOROCCAN_BANKS list
        """
        if not detected_name:
            return None
            
        # Remove extra spaces and convert to uppercase
        detected_name = ' '.join(detected_name.split()).upper()
        
        # Bank name mapping with various patterns
        bank_patterns = {
            'ATTIJARIWAFA_BANK': [
                'ATTIJARIWAFA', 'ATTIJARI', 'WAFA', 'AWB',
                'التجاري وفا', 'التجاري', 'وفا بنك'
            ],
            'BANQUE_CENTRALE_POPULAIRE': [
                'BANQUE POPULAIRE', 'POPULAIRE', 'BCP', 'BP',
                'البنك الشعبي', 'الشعبي', 'CENTRALE POPULAIRE'
            ],
            'BANK_OF_AFRICA': [
                'BANK OF AFRICA', 'BOA', 'BMCE', 'BMCE BANK',
                'بنك افريقيا', 'بنك المغرب للتجارة'
            ],
            'BMCI': [
                'BMCI', 'BANQUE MAROCAINE', 'COMMERCE ET INDUSTRIE',
                'MAROCAINE POUR LE COMMERCE'
            ],
            'CREDIT_AGRICOLE': [
                'CREDIT AGRICOLE', 'CAM', 'AGRICOLE DU MAROC',
                'القرض الفلاحي'
            ],
            'CIH_BANK': [
                'CIH', 'CREDIT IMMOBILIER', 'IMMOBILIER ET HOTELIER',
                'القرض العقاري'
            ],
            'CREDIT_DU_MAROC': [
                'CREDIT DU MAROC', 'CDM', 'CRÉDIT DU MAROC'
            ],
            'SOCIETE_GENERALE': [
                'SOCIETE GENERALE', 'SG MAROC', 'SGMA', 'SG'
            ],
            'AL_BARID_BANK': [
                'BARID BANK', 'AL BARID', 'BARIDBANK',
                'بريد بنك', 'البريد بنك'
            ],
            'CFG_BANK': [
                'CFG', 'CFG BANK'
            ],
            'UMNIA_BANK': [
                'UMNIA', 'UMNIA BANK'
            ],
        }
        
        # Try to match detected name with patterns
        for bank_code, patterns in bank_patterns.items():
            for pattern in patterns:
                if pattern in detected_name or detected_name in pattern:
                    logger.info(f"Matched bank: {detected_name} -> {bank_code}")
                    return bank_code
        
        # If no match found, log warning and return OTHER
        logger.warning(f"Could not match bank name: {detected_name}, defaulting to OTHER")
        return 'OTHER'
