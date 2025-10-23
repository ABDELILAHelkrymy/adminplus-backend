import json
import logging
from decimal import Decimal, InvalidOperation
from typing import Dict, Any
from openai import OpenAI
from django.conf import settings

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
    "branch": "string or null",
    "period_start": "YYYY-MM-DD or null",
    "period_end": "YYYY-MM-DD or null",
    "opening_balance": number or null,
    "closing_balance": number or null,
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
8. Return ONLY the JSON object, no extra text or markdown

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
        """Normalize and convert numerical values to Decimal"""
        def parse_decimal(val):
            try:
                if val is None or val == '':
                    return None
                return Decimal(str(val))
            except (ValueError, InvalidOperation, TypeError):
                return None

        statement = data.get('statement', {})
        
        # Process balance values
        if 'opening_balance' in statement:
            statement['opening_balance'] = parse_decimal(statement['opening_balance'])
        if 'closing_balance' in statement:
            statement['closing_balance'] = parse_decimal(statement['closing_balance'])
        
        # Process transactions
        transactions = statement.get('transactions', [])
        for transaction in transactions:
            transaction['debit'] = parse_decimal(transaction.get('debit', 0)) or Decimal('0.00')
            transaction['credit'] = parse_decimal(transaction.get('credit', 0)) or Decimal('0.00')
            
            # Ensure category is valid
            valid_categories = [
                'BANK_FEE', 'ATM_WITHDRAWAL', 'BILL_PAYMENT', 'LOAN_REPAYMENT',
                'TAX', 'TRANSFER_OUT', 'TRANSFER_IN', 'CASH_DEPOSIT',
                'CARD_PAYMENT', 'CHECK_PAYMENT', 'SALARY', 'INTEREST', 'OTHER'
            ]
            if transaction.get('category') not in valid_categories:
                transaction['category'] = 'OTHER'
        
        return data
