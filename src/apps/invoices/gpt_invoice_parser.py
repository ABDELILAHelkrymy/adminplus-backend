import os
import json
import logging
from decimal import Decimal, InvalidOperation
from typing import Dict, Any
from openai import OpenAI
from django.conf import settings

logger = logging.getLogger(__name__)


class GPTInvoiceParser:
    """
    Class responsible for parsing and extracting data from invoice files using OpenAI's GPT API
    """

    def __init__(self, debug: bool = False):
        """Initialize the GPT parser with API key from environment"""
        self.api_key = settings.GPT_API_KEY
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.client = OpenAI(api_key=self.api_key)
        self.debug = debug

    def extract_invoice_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data from invoice text using GPT API"""
        try:
            prompt = self._prepare_prompt(text)
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert at extracting structured data from invoice text. 
                        Extract key information and return it in a specific JSON format.
                        Follow these rules:
                        1. Always return a complete JSON structure with all fields
                        2. Use null for empty values
                        3. Format monetary values as decimal numbers
                        4. Extract supplier and customer information carefully
                        5. For line items, ensure quantity, unit_price, and amount are properly calculated
                        6. Set appropriate currency based on the invoice content
                        7. Set language and country based on the invoice content
                        8. Extract tax information (rate and amount) accurately
                        9. Set invoice_type to 'standard' by default
                        10. Include all legal mentions and metadata"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=1500
            )
            content = response.choices[0].message.content.strip()
            if self.debug:
                logger.debug(f"Raw GPT response: {content}")

            extracted_data = self._parse_gpt_response(content)
            return self._post_process(extracted_data)

        except Exception as e:
            logger.error(f"Error in GPT invoice parsing: {str(e)}")
            raise

    def _prepare_prompt(self, text: str) -> str:
        """Prepare the GPT input prompt with structured instructions"""
        return f"""
        Extract the following information from this invoice text and return it in JSON format:
        {{
            "invoice_number": "string",
            "status": "unpaid/paid/overdue",
            "date": "string (ISO format)",
            "due_date": "string (ISO format)",
            "paid_date": "string (ISO format) or null",
            "supplier_info": {{
                "name": "string",
                "legal_name": "string",
                "tax_id": "string",
                "if": "string",
                "rc": "string",
                "cnss": "string",
                "address": "string",
                "email": "string",
                "phone": "string",
                "ice": "string"
            }},
            "customer_info": {{
                "name": "string",
                "legal_name": "string",
                "tax_id": "string",
                "address": "string",
                "reference": "string",
                "email": "string",
                "phone": "string",
                "ice": "string"
            }},
            "line_items": [
                {{
                    "id": number,
                    "description": "string",
                    "quantity": number,
                    "unit_price": number,
                    "amount": number,
                    "tax_rate": number or null,
                    "tax_amount": number or null
                }}
            ],
            "subtotal": number,
            "tax_amount": number,
            "tax_rate": number,
            "total": number,
            "currency": "string (e.g. EUR, MAD, USD)",
            "invoice_type": "standard",
            "payment_terms": "string",
            "payment_method": "string",
            "notes": "string",
            "legal_mentions": {{
                "compliance": "string",
                "late_fee": number or null,
                "penalties": number or null
            }},
            "metadata": {{
                "language": "string (en/fr)",
                "country": "string (e.g. FR, MA, US)",
                "template": "standard"
            }}
        }}

        Rules for extraction:
        1. For supplier_info and customer_info, extract all available fields
        2. For line items, ensure quantity * unit_price = amount
        3. For tax calculations, ensure tax_amount = subtotal * (tax_rate/100)
        4. Set currency based on the invoice content (EUR, MAD, USD, etc.)
        5. Set language based on the invoice content (en/fr)
        6. Set country based on the invoice content and currency
        7. Extract all legal mentions and compliance information
        8. For empty or missing fields, use null
        9. Format all monetary values as decimal numbers
        10. Ensure all required fields are present in the response

        Invoice text:
        {text}
        """

    def _parse_gpt_response(self, response: str) -> Dict[str, Any]:
        """Cleans and parses the GPT response to JSON"""
        try:
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            return json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            raise ValueError("GPT returned invalid JSON")

    def _post_process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and convert numerical values to Decimal"""
        def parse_decimal(val):
            try:
                return Decimal(str(val)) if val is not None else None
            except (ValueError, InvalidOperation, TypeError):
                return None

        # Process monetary values
        data["subtotal"] = parse_decimal(data.get("subtotal"))
        data["tax_amount"] = parse_decimal(data.get("tax_amount"))
        data["total"] = parse_decimal(data.get("total"))
        data["tax_rate"] = parse_decimal(data.get("tax_rate"))

        # Process line items
        for item in data.get("line_items", []):
            item["quantity"] = parse_decimal(item.get("quantity"))
            item["unit_price"] = parse_decimal(item.get("unit_price"))
            item["amount"] = parse_decimal(item.get("amount"))
            item["tax_rate"] = parse_decimal(item.get("tax_rate"))
            item["tax_amount"] = parse_decimal(item.get("tax_amount"))

        # Process legal mentions
        if "legal_mentions" in data:
            data["legal_mentions"]["late_fee"] = parse_decimal(data["legal_mentions"].get("late_fee"))
            data["legal_mentions"]["penalties"] = parse_decimal(data["legal_mentions"].get("penalties"))

        # Ensure all required fields are present
        required_fields = {
            "invoice_number": "",
            "status": "unpaid",
            "date": "",
            "due_date": "",
            "paid_date": None,
            "supplier_info": {
                "name": "",
                "legal_name": "",
                "tax_id": "",
                "if": "",
                "rc": "",
                "cnss": "",
                "address": "",
                "email": "",
                "phone": "",
                "ice": ""
            },
            "customer_info": {
                "name": "",
                "legal_name": "",
                "tax_id": "",
                "address": "",
                "reference": "",
                "email": "",
                "phone": "",
                "ice": ""
            },
            "line_items": [],
            "subtotal": None,
            "tax_amount": None,
            "tax_rate": None,
            "total": None,
            "currency": "EUR",
            "invoice_type": "standard",
            "payment_terms": "",
            "payment_method": "",
            "notes": "",
            "legal_mentions": {
                "compliance": "",
                "late_fee": None,
                "penalties": None
            },
            "metadata": {
                "language": "fr",
                "country": "FR",
                "template": "standard"
            }
        }

        # Merge with required fields to ensure all are present
        for key, default_value in required_fields.items():
            if key not in data:
                data[key] = default_value
            elif isinstance(default_value, dict):
                for subkey, subvalue in default_value.items():
                    if subkey not in data[key]:
                        data[key][subkey] = subvalue

        return data
