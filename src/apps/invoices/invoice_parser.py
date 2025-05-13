import re
import io
import traceback
from PIL import Image
from pdf2image import convert_from_bytes
import pytesseract
from decimal import Decimal, DecimalException, InvalidOperation
import langdetect
import json
from datetime import datetime
import difflib
import cv2
import numpy as np


class InvoiceParser:
    """
    Class responsible for parsing and extracting data from invoice files
    """
    
    FIELD_PATTERNS = {
        'en': {
            'invoice_number': [
                r'invoice\s*(?:#|no|number|num)[:\s]*([0-9a-zA-Z\-_/]+)',
                r'invoice[:\s]*([0-9a-zA-Z\-_/]+)',
                r'#\s*([0-9a-zA-Z\-_/]+)',
                r'\binvoice\b.*?([A-Z][0-9]+)',
                r'(?<!\S)([A-Z][0-9]{6,})(?!\S)'
            ],
            'date': [
                r'date[:\s]*([\d]{1,2}[-/\.][\d]{1,2}[-/\.][\d]{2,4})',
                r'date[:\s]*(\d{4}-\d{1,2}-\d{1,2})',
                r'date:\s*([\d]{1,2}/[\d]{1,2}/[\d]{4})'
            ],
            'due_date': [
                r'due\s*date[:\s]*([\d]{1,2}[-/\.][\d]{1,2}[-/\.][\d]{2,4})',
                r'due\s*date[:\s]*(\d{4}-\d{1,2}-\d{1,2})',
                r'due\s*date:\s*([\d]{1,2}/[\d]{1,2}/[\d]{4})'
            ],
            'from': r'from[:\s]*\n*([\s\S]*?)(?=\n\s*\n|\nto[:\s]*|\Z)',
            'to': r'to[:\s]*\n*([\\s\S]*?)(?=\n\s*\n|\norder\s+lines|\Z)',
            'order_lines': r'order\s+lines.*?\n([\s\S]*?)(?=\n\s*\n|\nsubtotal|\ntotal|\Z)',
            'subtotal': [r'subtotal[:\s]*\$?(\d+\.\d+)', r'sub[ -]?total[:\s]*\$?(\d+\.\d+)'],
            'tax': [r'vat\s*(?:\((\d+)%\))?[:\s]*\$?(\d+\.\d+)', r'tax\s*(?:\((\d+)%\))?[:\s]*\$?(\d+\.\d+)'],
            'total': [r'total[:\s]*\$?(\d+\.\d+)', r'total amount[:\s]*\$?(\d+\.\d+)', r'amount due[:\s]*\$?(\d+\.\d+)'],
            'line_headers': [
                ['description', 'quantity', 'unit', 'price', 'amount'],
                ['item', 'qty', 'uom', 'rate', 'total']
            ]
        },
        'fr': {
            'invoice_number': [
                r'facture\s*(?:#|n[o°]|num[ée]ro|num)[:\s]*([0-9a-zA-Z\-_/]+)',
                r'facture[:\s]*([0-9a-zA-Z\-_/]+)',
                r'#\s*([0-9a-zA-Z\-_/]+)',
                r'\bfacture\b.*?([A-Z][0-9]+)',
                r'(?<!\S)([A-Z][0-9]{6,})(?!\S)',
                r'Facture\s+N[°o]\s*[:.]?\s*([0-9a-zA-Z\-_/]+)'
            ],
            'date': [
                r'date[:\s]*([\d]{1,2}[-/\.][\d]{1,2}[-/\.][\d]{2,4})',
                r'date[:\s]*(\d{4}-\d{1,2}-\d{1,2})',
                r'date:\s*([\d]{1,2}/[\d]{1,2}/[\d]{4})',
                r'Date\s*[:.]?\s*([\d]{1,2}[-/\.][\d]{1,2}[-/\.][\d]{2,4})',
                r'Date\s*[:.]?\s*([\d]{1,2}/[\d]{1,2}/[\d]{4})'
            ],
            'due_date': [
                r'\b[ée]ch[ée]ance[:\s]*([\d]{1,2}[-/\.][\d]{1,2}[-/\.][\d]{2,4})',
                r'\b[ée]ch[ée]ance[:\s]*(\d{4}-\d{1,2}-\d{1,2})',
                r'\b[ée]ch[ée]ance:\s*([\d]{1,2}/[\d]{1,2}/[\d]{4})',
                r'date\s+limite[:\s]*([\d]{1,2}[-/\.][\d]{1,2}[-/\.][\d]{2,4})'
            ],
            'from': r'de[:\s]*\n*([\s\S]*?)(?=\n\s*\n|\n[aà] l[ae][:\s]*|\Z)',
            'to': r'[aà] l[ae][:\s]*\n*([\s\S]*?)(?=\n\s*\n|\nlignes de commande|\Z)',
            'order_lines': r'lignes de commande.*?\n([\s\S]*?)(?=\n\s*\n|\nsous-total|\ntotal|\Z)',
            'subtotal': [r'sous-total[:\s]*€?(\d+[\.,]\d+)', r'sous[ -]?total[:\s]*€?(\d+[\.,]\d+)', r'total\s+ht[:\s]*(\d+[\.,]\d+)'],
            'tax': [r'tva\s*(?:\((\d+)%\))?[:\s]*[€\$]?(\d+[\.,]\d+)', r'taxe\s*(?:\((\d+)%\))?[:\s]*[€\$]?(\d+[\.,]\d+)', r'tva\s*\(?(\d+)%\)?[:\s]*[€\$]?(\d+[\.,]\d+)'],
            'total': [r'total[:\s]*[€\$]?(\d+[\.,]\d+)', r'montant total[:\s]*[€\$]?(\d+[\.,]\d+)', r'montant dû[:\s]*[€\$]?(\d+[\.,]\d+)', r'total\s+ttc[:\s]*(\d+[\.,]\d+)'],
            'line_headers': [
                ['désignation', 'quantité', 'unité', 'prix', 'montant'],
                ['article', 'qté', 'uom', 'tarif', 'total'],
                ['description', 'quantité', 'prix unitaire ht', 'total ht']
            ],
            'if': [r'IF[:\s]*([0-9]+)', r'Identifiant Fiscal[:\s]*([0-9]+)'],
            'rc': [r'RC[:\s]*([0-9]+)', r'Registre de Commerce[:\s]*([0-9]+)'],
            'ice': [r'ICE[:\s]*([0-9]+)'],
            'cnss': [r'CNSS[:\s]*([0-9]+)'],
            'payment_terms': [
                r'(virement bancaire sous \d+ jours)',
                r'(paiement à réception)',
                r'(paiement à \d+ jours)',
                r'mode de paiement[:\s]*(.*?)(?:\n|$)',
                r'Conditions de paiement[:\s]*(.*?)(?:\n|$)'
            ]
        }
    }

    @staticmethod
    def detect_language(text):
        try:
            lang = langdetect.detect(text)
            if lang.startswith('fr'):
                return 'fr'
            return 'en'
        except Exception:
            return 'en'
    
    @staticmethod
    def extract_text_from_file(invoice_file):
        """
        Extract text content from various file formats (PDF, JPG, PNG)
        Adds debug logging to print the OCR output before parsing.
        
        Args:
            invoice_file: The uploaded file object
            
        Returns:
            tuple: (extracted_text, file_extension)
            
        Raises:
            Exception: If file format is unsupported or extraction fails
        """
        file_extension = invoice_file.name.split('.')[-1].lower()
        text = ""
        if file_extension == 'pdf':
            images = convert_from_bytes(invoice_file.read())
            for img in images:
                img_byte_array = io.BytesIO()
                img.save(img_byte_array, format='PNG')
                img_byte_array.seek(0)
                text += pytesseract.image_to_string(Image.open(img_byte_array))
        elif file_extension in ['jpg', 'jpeg', 'png']:
            # Preprocess the image
            image = Image.open(invoice_file)
            image = image.convert('L')  # Convert to grayscale
            image = cv2.cvtColor(np.array(image), cv2.COLOR_GRAY2BGR)
            # Resize image to a standard size
            image = cv2.resize(image, (0, 0), fx=1.5, fy=1.5)
            # Apply adaptive thresholding
            image = cv2.adaptiveThreshold(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), 255,
                                          cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            # Use pytesseract with custom configuration
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(image, config=custom_config)
        else:
            raise ValueError("Unsupported file format. Please upload PDF, JPG, or PNG.")
        # Debug: Print OCR output
        print("\n===== OCR EXTRACTED TEXT =====\n" + text + "\n==============================\n")
        return text, file_extension
    
    @staticmethod
    def extract_invoice_data(text):
        """
        Robust extraction of structured data from invoice text (English and French).
        Uses language detection, language-specific extraction, and fallback extraction for missing fields.
        """
        lang = InvoiceParser.detect_language(text)
        data = InvoiceParser._init_data(lang)

        # Language-specific extraction
        if lang == 'fr':
            data = InvoiceParser._extract_french_invoice_data(text, data)
        else:
            data = InvoiceParser._extract_english_invoice_data(text, data)

        # Fallbacks for missing fields
        if not data['invoice_number']:
            data['invoice_number'] = InvoiceParser._extract_invoice_number_generic(text)
        if not data['date']:
            data['date'] = InvoiceParser._extract_date_generic(text)
        if not data['total']:
            data['total'] = InvoiceParser._extract_total_generic(text)
        if not data['subtotal']:
            data['subtotal'] = InvoiceParser._extract_subtotal_generic(text)
        if not data['tax_amount']:
            data['tax_amount'] = InvoiceParser._extract_tax_amount_generic(text)
        if not data['tax_rate']:
            data['tax_rate'] = InvoiceParser._extract_tax_rate_generic(text)

        # Only use generic line item extraction if language-specific extraction found nothing
        if not data['line_items']:
            data['line_items'] = InvoiceParser._extract_line_items(text, lang)

        # Post-process and validate
        data = InvoiceParser._post_process(data)
        return data

    @staticmethod
    def _init_data(lang):
        """Initialize the data structure for invoice extraction."""
        return {
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
            "currency": "USD" if lang == 'en' else "EUR",
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
                "language": lang,
                "country": "US" if lang == 'en' else "FR",
                "template": "standard"
            }
        }

    @staticmethod
    def _extract_english_invoice_data(text, data=None):
        """
        Robust extractor for English invoices: line items, totals, and VAT.
        Handles headers like 'Description | Quantity | Unit Price | Amount', 
        and formats like 'From/To' sections, and 'ORDER LINES'.
        Also extracts supplier and customer info, payment terms, and status.
        """
        import itertools
        import unicodedata
        import re
        if data is None:
            data = InvoiceParser._init_data('en')
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        # Helper function to parse numbers that may have commas as decimal or thousands separators
        def parse_number(num_str):
            # Remove currency symbols
            num_str = re.sub(r'[$€£]', '', num_str)
            # Handle formats like "10,000.00" - comma as thousands separator
            if ',' in num_str and '.' in num_str:
                return float(num_str.replace(',', ''))
            # Handle formats like "10.000,00" - period as thousands separator, comma as decimal
            elif ',' in num_str and not '.' in num_str:
                return float(num_str.replace('.', '').replace(',', '.'))
            # Handle formats like "10000.00" - standard US format
            elif '.' in num_str and not ',' in num_str:
                return float(num_str)
            # Handle formats like "10000,00" - comma as decimal
            elif ',' in num_str:
                return float(num_str.replace(',', '.'))
            # Just a plain number
            else:
                return float(num_str)
        
        # --- Extract Invoice Number and Dates ---
        # Invoice number
        invoice_patterns = [
            r'Invoice\s*(?:#|No|Number|Num)[:\s]*([0-9a-zA-Z\-_/]+)',
            r'Invoice[:\s]*([0-9a-zA-Z\-_/]+)',
            r'Invoice\s*#\s*([0-9a-zA-Z\-_/]+)',
            r'Invoice\s+(?:#\s*)?([\w\-]+)',  # Captures "Invoice #YH45687"
        ]
        for pattern in invoice_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["invoice_number"] = match.group(1).strip()
                break
        
        # Date
        date_patterns = [
            r'Date[:\s]*([\d]{1,2}[-/\.][\d]{1,2}[-/\.][\d]{2,4})',
            r'Date[:\s]*(\d{4}-\d{1,2}-\d{1,2})',
            r'Date:\s*([\d]{1,2}/[\d]{1,2}/[\d]{4})'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["date"] = match.group(1).strip()
                break
                
        # Due date
        due_date_patterns = [
            r'Due\s*Date[:\s]*([\d]{1,2}[-/\.][\d]{1,2}[-/\.][\d]{2,4})',
            r'Due\s*Date[:\s]*(\d{4}-\d{1,2}-\d{1,2})',
            r'Due\s*Date:\s*([\d]{1,2}/[\d]{1,2}/[\d]{4})'
        ]
        for pattern in due_date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["due_date"] = match.group(1).strip()
                break
                
        # Paid date
        paid_date_patterns = [
            r'Paid\s*Date[:\s]*([\d]{1,2}[-/\.][\d]{1,2}[-/\.][\d]{2,4})',
            r'Paid\s*Date[:\s]*(\d{4}-\d{1,2}-\d{1,2})',
            r'Paid\s*Date:\s*([\d]{1,2}/[\d]{1,2}/[\d]{4})'
        ]
        for pattern in paid_date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["paid_date"] = match.group(1).strip()
                data["status"] = "paid"
                break
                
        # Status
        status_match = re.search(r'Status[:\s]*([A-Za-z]+)', text, re.IGNORECASE)
        if status_match:
            status = status_match.group(1).strip().lower()
            if status == "paid":
                data["status"] = "paid"
            elif status == "unpaid" or status == "due":
                data["status"] = "unpaid"
            elif status == "overdue":
                data["status"] = "overdue"
        
        # --- Extract Supplier and Customer Info ---
        # Find "From:" and "To:" sections
        from_match = re.search(r'From[:\s]*\n*([\s\S]*?)(?=\n\s*\n|\nTo[:\s]*|\Z)', text, re.IGNORECASE)
        to_match = re.search(r'To[:\s]*\n*([\\s\S]*?)(?=\n\s*\n|\norder\s+lines|\Z)', text, re.IGNORECASE)
        
        if from_match:
            from_text = from_match.group(1).strip()
            from_lines = [l.strip() for l in from_text.split('\n') if l.strip()]
            
            if from_lines:
                # First line is usually the company name
                data["supplier_info"]["name"] = from_lines[0]
                data["supplier_info"]["legal_name"] = from_lines[0]
                
                # Look for email, phone, etc.
                for line in from_lines:
                    if '@' in line:
                        data["supplier_info"]["email"] = line
                    elif re.search(r'\+?\d+', line):
                        data["supplier_info"]["phone"] = line
                    elif re.search(r'VAT|Tax|ICE|IF', line, re.IGNORECASE):
                        # Check for ICE (Morocco)
                        ice_match = re.search(r'ICE\s*(?:[:.])?(?:\s*)(\d+)', line, re.IGNORECASE)
                        if ice_match:
                            data["supplier_info"]["ice"] = ice_match.group(1).strip()
                            data["supplier_info"]["tax_id"] = ice_match.group(1).strip()
                        # Check for general tax ID
                        else:
                            tax_id_match = re.search(r'(?:VAT|Tax|IF)[:\s]*([0-9A-Za-z]+)', line, re.IGNORECASE)
                            if tax_id_match:
                                data["supplier_info"]["tax_id"] = tax_id_match.group(1).strip()
                
                # Remaining lines are likely the address
                address_lines = []
                for line in from_lines[1:]:
                    if '@' not in line and not re.search(r'VAT|Tax|Tel|Phone|ICE|IF', line, re.IGNORECASE):
                        address_lines.append(line)
                
                if address_lines:
                    data["supplier_info"]["address"] = ', '.join(address_lines)
        
        # Also try to find standalone ICE values for suppliers
        ice_match = re.search(r'ICECLIENT\s*(\d+)', text, re.IGNORECASE)
        if ice_match and not data["supplier_info"]["ice"]:
            data["supplier_info"]["ice"] = ice_match.group(1).strip()
            if not data["supplier_info"]["tax_id"]:
                data["supplier_info"]["tax_id"] = ice_match.group(1).strip()
        
        if to_match:
            to_text = to_match.group(1).strip()
            to_lines = [l.strip() for l in to_text.split('\n') if l.strip()]
            
            if to_lines:
                # First line is usually the company name
                data["customer_info"]["name"] = to_lines[0]
                data["customer_info"]["legal_name"] = to_lines[0]
                
                # Look for email, phone, etc.
                for line in to_lines:
                    if '@' in line:
                        data["customer_info"]["email"] = line
                    elif re.search(r'\+?\d+', line):
                        data["customer_info"]["phone"] = line
                    elif re.search(r'VAT|Tax|ICE|IF', line, re.IGNORECASE):
                        # Check for ICE (Morocco)
                        ice_match = re.search(r'ICE\s*(?:[:.])?(?:\s*)(\d+)', line, re.IGNORECASE)
                        if ice_match:
                            data["customer_info"]["ice"] = ice_match.group(1).strip()
                            data["customer_info"]["tax_id"] = ice_match.group(1).strip()
                        # Check for general tax ID
                        else:
                            tax_id_match = re.search(r'(?:VAT|Tax|IF)[:\s]*([0-9A-Za-z]+)', line, re.IGNORECASE)
                            if tax_id_match:
                                data["customer_info"]["tax_id"] = tax_id_match.group(1).strip()
                
                # Remaining lines are likely the address
                address_lines = []
                for line in to_lines[1:]:
                    if '@' not in line and not re.search(r'VAT|Tax|Tel|Phone|ICE|IF', line, re.IGNORECASE):
                        address_lines.append(line)
                
                if address_lines:
                    data["customer_info"]["address"] = ', '.join(address_lines)
        
        # --- Extract Line Items ---
        line_items = []
        line_item_id = 1
        
        # First look for ORDER LINES section
        order_lines_match = re.search(r'ORDER\s+LINES.*?(?=Payment|Subtotal|\Z)', text, re.IGNORECASE | re.DOTALL)
        if order_lines_match:
            order_lines_text = order_lines_match.group(0)
            
            # Try to find the header row
            header_match = re.search(r'(Description|Item).*?(Quantity|Qty).*?(Price|Rate|Unit).*?(Amount|Total)', order_lines_text, re.IGNORECASE)
            if header_match:
                header_line = header_match.group(0)
                # Extract items after header line
                items_text = order_lines_text[order_lines_text.index(header_line) + len(header_line):]
                
                # Process line by line until we hit a subtotal or total line
                item_lines = [l.strip() for l in items_text.split('\n') if l.strip()]
                for line in item_lines:
                    if re.search(r'subtotal|total|vat|tax', line, re.IGNORECASE):
                        break
                        
                    # Try to extract: description, quantity, unit, price, amount
                    # Pattern: Description Quantity Unit Price Amount (with $ or without)
                    item_match = re.search(r'(.+?)\s+(\d+(?:\.\d+)?)\s+(\w+)\s+\$?(\d+\.\d+)\s+\$?(\d+\.\d+)', line)
                    if item_match:
                        try:
                            description = item_match.group(1).strip()
                            quantity = float(item_match.group(2))
                            unit = item_match.group(3).strip()
                            unit_price = float(item_match.group(4))
                            amount = float(item_match.group(5))
                            
                            line_items.append({
                                "id": line_item_id,
                                "description": description,
                                "quantity": quantity,
                                "unit_price": unit_price,
                                "amount": amount,
                                "unit": unit,
                                "tax_rate": None,
                                "tax_amount": None
                            })
                            line_item_id += 1
                        except Exception:
                            continue
        
        # If no items found, try more generic table patterns
        if not line_items:
            # Pattern: Description Quantity Unit Price Amount (with $ or without)
            # This pattern is more flexible with currency symbols and whitespace
            table_pattern = r'(.+?)\s+(\d+(?:\.\d+)?)\s+(\w+)\s+[$€£]?(\d+\.\d+)\s+[$€£]?(\d+\.\d+)'
            for match in re.finditer(table_pattern, text, re.MULTILINE):
                try:
                    description = match.group(1).strip()
                    quantity = float(match.group(2))
                    unit = match.group(3).strip()
                    unit_price = float(match.group(4))
                    amount = float(match.group(5))
                    
                    # Skip if this looks like payment information
                    if any(term in description.lower() for term in ["subtotal", "total", "tax", "vat", "payment"]):
                        continue
                    
                    # Validate that unit_price * quantity is approximately amount
                    if abs(unit_price * quantity - amount) <= 0.1 * amount:
                        line_items.append({
                            "id": line_item_id,
                            "description": description,
                            "quantity": quantity,
                            "unit_price": unit_price,
                            "amount": amount,
                            "unit": unit,
                            "tax_rate": None,
                            "tax_amount": None
                        })
                        line_item_id += 1
                except Exception:
                    continue
                    
            # Try another pattern: Description Quantity Amount (no unit)
            if not line_items:
                simple_pattern = r'(.+?)\s+(\d+(?:\.\d+)?)\s+[$€£]?(\d+\.\d+)'
                for match in re.finditer(simple_pattern, text, re.MULTILINE):
                    try:
                        description = match.group(1).strip()
                        quantity = float(match.group(2))
                        amount = float(match.group(3))
                        
                        # Skip if this looks like payment information
                        if any(term in description.lower() for term in ["subtotal", "total", "tax", "vat", "payment"]):
                            continue
                        
                        # Calculate unit price
                        unit_price = amount / quantity if quantity > 0 else 0
                        
                        line_items.append({
                            "id": line_item_id,
                            "description": description,
                            "quantity": quantity,
                            "unit_price": unit_price,
                            "amount": amount,
                            "tax_rate": None,
                            "tax_amount": None
                        })
                        line_item_id += 1
                    except Exception:
                        continue
        
        # Remove duplicates
        seen = set()
        unique_line_items = []
        for item in line_items:
            key = (item['description'], item['quantity'], item.get('unit_price', 0), item['amount'])
            if key not in seen:
                unique_line_items.append(item)
                seen.add(key)
        line_items = unique_line_items
        data["line_items"] = line_items
        
        # --- Extract Totals ---
        # Subtotal
        subtotal_patterns = [
            r'Subtotal[:\s]*[$€£]?(\d+\.\d+)',
            r'Sub[ -]?total[:\s]*[$€£]?(\d+\.\d+)'
        ]
        for pattern in subtotal_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["subtotal"] = float(match.group(1))
                break
        
        # Tax / VAT
        tax_patterns = [
            r'VAT\s*\((\d+)%\)[:\s]*[$€£]?(\d+\.\d+)',
            r'Tax\s*\((\d+)%\)[:\s]*[$€£]?(\d+\.\d+)',
            r'Tax[:\s]*[$€£]?(\d+\.\d+)',
            r'VAT[:\s]*[$€£]?(\d+\.\d+)'
        ]
        for pattern in tax_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    # Pattern with percentage
                    data["tax_rate"] = float(groups[0])
                    data["tax_amount"] = float(groups[1])
                else:
                    # Pattern without percentage
                    data["tax_amount"] = float(groups[0])
                break
        
        # Total
        total_patterns = [
            r'Total[:\s]*[$€£]?(\d+\.\d+)',
            r'Total amount[:\s]*[$€£]?(\d+[\.,]\d+)',
            r'Amount due[:\s]*[$€£]?(\d+[\.,]\d+)'
        ]
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["total"] = float(match.group(1))
                break
        
        # --- Extract Payment Information ---
        payment_info_match = re.search(r'Payment Information[:\s]*\n*([\s\S]*?)(?=\n\s*\n|\Z)', text, re.IGNORECASE)
        if payment_info_match:
            payment_info = payment_info_match.group(1).strip()
            
            # Extract payment method
            if re.search(r'Bank|IBAN|SWIFT', payment_info, re.IGNORECASE):
                data["payment_method"] = "bank_transfer"
                
                # Extract payment terms
                data["payment_terms"] = payment_info.replace('\n', ' ')
                
                # Extract bank details for legal mentions
                iban_match = re.search(r'IBAN[:\s]*([A-Z0-9\s]+)', payment_info, re.IGNORECASE)
                swift_match = re.search(r'SWIFT[:/\s]*([A-Z0-9\s]+)', payment_info, re.IGNORECASE)
                bank_match = re.search(r'Bank[:\s]*([^\n]+)', payment_info, re.IGNORECASE)
                
                legal_mentions = []
                if bank_match:
                    legal_mentions.append(f"Bank: {bank_match.group(1).strip()}")
                if iban_match:
                    legal_mentions.append(f"IBAN: {iban_match.group(1).strip()}")
                if swift_match:
                    legal_mentions.append(f"SWIFT: {swift_match.group(1).strip()}")
                    
                if legal_mentions:
                    data["legal_mentions"]["compliance"] = " - ".join(legal_mentions)
        
        # Set currency to USD if dollar sign is present
        if '$' in text:
            data["currency"] = "USD"
        elif '€' in text:
            data["currency"] = "EUR"
        elif '£' in text:
            data["currency"] = "GBP"
        
        # Calculate missing totals if possible
        if data["subtotal"] is not None and data["tax_amount"] is not None and data["total"] is None:
            data["total"] = data["subtotal"] + data["tax_amount"]
            
        if data["subtotal"] is not None and data["total"] is not None and data["tax_amount"] is None:
            data["tax_amount"] = data["total"] - data["subtotal"]
            
        if data["subtotal"] is not None and data["tax_amount"] is not None and data["subtotal"] > 0 and data["tax_rate"] is None:
            tax_rate = (data["tax_amount"] / data["subtotal"]) * 100
            # Only set if it's a reasonable tax rate (0-30%)
            if 0 <= tax_rate <= 30:
                data["tax_rate"] = round(tax_rate, 2)
        
        return data

    @staticmethod
    def _extract_invoice_number_generic(text):
        """Generic invoice number extraction for any invoice format"""
        patterns = [
            r'(?:invoice|facture)\s*(?:no|n[°o]|number|num[ée]ro|#)[:\s]*([0-9a-zA-Z\-_/]+)',
            r'(?:invoice|facture)[:\s]*([0-9a-zA-Z\-_/]+)',
            r'#\s*([0-9a-zA-Z\-_/]+)',
            r'(?:invoice|facture)\s*(?:ref|reference)[:\s]*([0-9a-zA-Z\-_/]+)',
            r'(?<!\S)([A-Z][0-9]{6,})(?!\S)',  # Standalone alphanumeric invoice numbers
            r'Facture\s*N[°o*:.]?\s*:?\s*([\w\-/]+)',
            r'BL\s*(?:No|N[°o])?\s*[:\s]*([0-9a-zA-Z\-_/]+)',  # Delivery notes
            r'Invoice\s+(?:#\s*)?([\w\-]+)',  # Captures "Invoice #YH45687"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    @staticmethod
    def _extract_date_generic(text):
        """Generic date extraction for any invoice format"""
        patterns = [
            r'date[:\s]*([\d]{1,2}[-/\.][\d]{1,2}[-/\.][\d]{2,4})',
            r'date[:\s]*(\d{4}-\d{1,2}-\d{1,2})',
            r'date:\s*([\d]{1,2}/[\d]{1,2}/[\d]{4})',
            r'date\s*d[\'e]?\s*[ée]mission[:\s]*([\d]{1,2}[-/\.][\d]{1,2}[-/\.][\d]{2,4})',
            r'date\s*d[\'e]?\s*facture[:\s]*([\d]{1,2}[-/\.][\d]{1,2}[-/\.][\d]{2,4})',
            r'Date\s*[:.]?\s*(\d{1,2}/\d{1,2}/\d{4})',
            r'Date\s*[:.]?\s*(\d{1,2}-\d{1,2}-\d{4})',
            r'le,?\s*(\d{1,2}/\d{1,2}/\d{4})',  # "le 06/09/2021"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Look for standalone date formats
        date_format_patterns = [
            r'\b(\d{2}/\d{2}/\d{4})\b',  # DD/MM/YYYY
            r'\b(\d{2}-\d{2}-\d{4})\b',  # DD-MM-YYYY
            r'\b(\d{4}/\d{2}/\d{2})\b',  # YYYY/MM/DD
            r'\b(\d{4}-\d{2}-\d{2})\b'   # YYYY-MM-DD
        ]
        
        for pattern in date_format_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
                
        return ""

    @staticmethod
    def _extract_total_generic(text):
        """Generic total extraction for any invoice format"""
        patterns = [
            r'total[:\s]*[$€£]?(\d+[\.,]\d+)',
            r'total\s+amount[:\s]*[$€£]?(\d+[\.,]\d+)',
            r'amount\s+due[:\s]*[$€£]?(\d+[\.,]\d+)',
            r'total\s+ttc[:\s]*[$€£]?(\d+[\.,]\d+)',
            r'total\s+[\w\s]*\s*[:]?\s*[$€£]?(\d+[\.,]\d+)',
            r'Total\s+TTC\s*[:.]?\s*([\d.,]+)\s*MAD',
            r'arrêtée\s+la\s+présente\s+facture\s+a\s+la\s+somme\s+de\s*:?\s*(?:[a-zA-Z\s]+)?\s*([\d\s.,]+)', # "arrêtée la présente facture a la somme de:"
            r'(?:TROIS|CINQ|DIX|DEUX|QUATRE|NEUF|HUIT|SEPT|SIX|UN)\s+(?:MILLE|CENT)(?:\s+[A-Z]+)?\s+(?:CINQ\s+CENT|DEUX\s+CENT|QUATRE\s+VINGT)?\s+DH\s*[.\n]\s*([\d\s.,]+)', # French spelled out amounts
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value_str = match.group(1).strip().replace(' ', '').replace(',', '.')
                try:
                    return float(value_str)
                except ValueError:
                    continue
        
        return None

    @staticmethod
    def _extract_subtotal_generic(text):
        """Generic subtotal extraction for any invoice format"""
        patterns = [
            r'sub[- ]?total[:\s]*[$€£]?(\d+[\.,]\d+)',
            r'total\s+ht[:\s]*[$€£]?(\d+[\.,]\d+)',
            r'total\s+hors\s+taxes?[:\s]*[$€£]?(\d+[\.,]\d+)',
            r'sous[- ]?total[:\s]*[$€£]?(\d+[\.,]\d+)',
            r'Total\s+HT\s*[:.]?\s*([\d.,]+)\s*MAD'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value_str = match.group(1).strip().replace(',', '.')
                return float(value_str)
        
        return None

    @staticmethod
    def _extract_tax_amount_generic(text):
        """Generic tax amount extraction for any invoice format"""
        patterns = [
            r'tax[:\s]*[$€£]?(\d+[\.,]\d+)',
            r'vat[:\s]*[$€£]?(\d+[\.,]\d+)',
            r'tva[:\s]*[$€£]?(\d+[\.,]\d+)',
            r'tax\s*(?:\(\d+%\))?[:\s]*[$€£]?(\d+[\.,]\d+)',
            r'vat\s*(?:\(\d+%\))?[:\s]*[$€£]?(\d+[\.,]\d+)',
            r'tva\s*(?:\(\d+%\))?[:\s]*[$€£]?(\d+[\.,]\d+)',
            r'TVA\s*\(\d+%\)\s*[:.]?\s*([\d.,]+)\s*MAD'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value_str = match.group(1).strip().replace(',', '.')
                return float(value_str)
        
        return None

    @staticmethod
    def _extract_tax_rate_generic(text):
        """Generic tax rate extraction for any invoice format"""
        patterns = [
            r'tax\s*\((\d+)%\)',
            r'vat\s*\((\d+)%\)',
            r'tva\s*\((\d+)%\)',
            r'tax rate[:\s]*(\d+)%',
            r'vat rate[:\s]*(\d+)%',
            r'tva rate[:\s]*(\d+)%',
            r'TVA\s*\((\d+)%\)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1))
        
        return None

    @staticmethod
    def _post_process(data):
        """Normalize, validate, and fill missing fields if possible"""
        # Ensure numeric fields are properly formatted
        numeric_fields = ['subtotal', 'tax_amount', 'tax_rate', 'total']
        for field in numeric_fields:
            if data.get(field) is not None:
                data[field] = round(float(data[field]), 2)
        
        # Calculate missing values if possible
        if data['subtotal'] is not None and data['tax_amount'] is not None and data['total'] is None:
            data['total'] = data['subtotal'] + data['tax_amount']
        
        if data['subtotal'] is not None and data['total'] is not None and data['tax_amount'] is None:
            data['tax_amount'] = data['total'] - data['subtotal']
        
        if data['subtotal'] is not None and data['tax_amount'] is not None and data['subtotal'] > 0 and data['tax_rate'] is None:
            tax_rate = (data['tax_amount'] / data['subtotal']) * 100
            # Only set if it's a reasonable tax rate (0-30%)
            if 0 <= tax_rate <= 30:
                data['tax_rate'] = round(tax_rate, 2)
        
        # Set country based on currency
        if data['currency'] == 'MAD':
            data['metadata']['country'] = 'MA'
        elif data['currency'] == 'EUR':
            # Could be various European countries
            if data['supplier_info'].get('address') and re.search(r'France|Paris|Lyon', data['supplier_info']['address'], re.IGNORECASE):
                data['metadata']['country'] = 'FR'
            elif data['supplier_info'].get('address') and re.search(r'Spain|Madrid|Barcelona', data['supplier_info']['address'], re.IGNORECASE):
                data['metadata']['country'] = 'ES'
            # Default to France if no specific country found
            else:
                data['metadata']['country'] = 'FR'
        elif data['currency'] == 'USD':
            data['metadata']['country'] = 'US'
        elif data['currency'] == 'GBP':
            data['metadata']['country'] = 'GB'
        
        # Set language if it hasn't been set
        if not data['metadata'].get('language'):
            if data['metadata'].get('country') in ['FR', 'MA']:
                data['metadata']['language'] = 'fr'
            else:
                data['metadata']['language'] = 'en'
                
        # Fill empty payment method if payment terms suggests one
        if not data['payment_method'] and data['payment_terms']:
            terms = data['payment_terms'].lower()
            if any(term in terms for term in ['bank', 'wire', 'transfer', 'iban', 'swift', 'bic', 'virement']):
                data['payment_method'] = 'bank_transfer'
            elif any(term in terms for term in ['check', 'cheque', 'chèque']):
                data['payment_method'] = 'cheque'
            elif any(term in terms for term in ['cash', 'espèces']):
                data['payment_method'] = 'cash'
            elif any(term in terms for term in ['card', 'credit', 'carte']):
                data['payment_method'] = 'card'
                
        return data

    @staticmethod
    def extract_expenditure_invoice_data(text):
        """
        Extract structured data from expenditure invoices.
        """
        # Detect language
        language = InvoiceParser.detect_language(text)
        
        # Initialize data structure
        data = InvoiceParser._init_data(language)
        
        # Call the appropriate extraction method based on language
        try:
            if language == 'fr':
                data = InvoiceParser._extract_french_invoice_data(text, data)
            else:
                data = InvoiceParser._extract_english_invoice_data(text, data)
                
            # Special handling for K.A. TECHNO SERVICES invoices with colored headers
            if "K.A" in text and "TECHNO" in text and not data["line_items"]:
                # Extract from invoice with colored headers where tables aren't visible
                # First look for the TOTAL TTC value
                total_ttc_match = re.search(r'TOTAL\s+TTC\s*([\d\s.,]+)', text, re.IGNORECASE)
                if total_ttc_match:
                    try:
                        total_value = InvoiceParser._parse_number(total_ttc_match.group(1))
                        if total_value > 0:
                            data["total"] = total_value
                    except Exception as e:
                        print(f"Error parsing TOTAL TTC: {e}")
                
                if data["total"] is not None and data["total"] > 0:
                    # Look for service descriptions in the text
                    service_patterns = [
                        r'(Installation|Reparation|Maintenance|Nettoyage|Travaux|Development|Hebergement|Service)\s+([^\n]+)',
                        r'(.*?[Ss]ervice.*?)'
                    ]
                    
                    service_desc = None
                    for pattern in service_patterns:
                        service_match = re.search(pattern, text, re.IGNORECASE)
                        if service_match:
                            if len(service_match.groups()) > 1:
                                service_desc = f"{service_match.group(1)} {service_match.group(2)}"
                            else:
                                service_desc = service_match.group(1)
                            break
                    
                    if service_desc is None:
                        service_desc = "Service professionnel"
                    
                    # Calculate VAT (assume 20% for Morocco)
                    subtotal = data["total"] / 1.2  # Assuming VAT rate is 20%
                    tax_amount = data["total"] - subtotal
                    
                    data["line_items"] = [{
                        "id": 1,
                        "description": service_desc,
                        "quantity": 1,
                        "unit_price": round(subtotal, 2),
                        "amount": round(subtotal, 2),
                        "tax_rate": 20.0,
                        "tax_amount": round(tax_amount, 2)
                    }]
                    
                    # Update the data with our calculated values
                    data["subtotal"] = round(subtotal, 2)
                    data["tax_amount"] = round(tax_amount, 2)
                    data["tax_rate"] = 20.0
            
            return data
            
        except Exception as e:
            logger.error(f"Error extracting invoice data: {e}")
            # Return empty data structure in case of error
            return InvoiceParser._init_data(language)

    @staticmethod
    def _preprocess_ocr_text(text):
        """
        Preprocesses OCR text to fix common issues and improve extraction.
        """
        # Fix common OCR errors
        text = text.replace('é', 'e').replace('è', 'e').replace('ê', 'e')
        text = text.replace('à', 'a').replace('â', 'a')
        text = text.replace('ô', 'o').replace('ù', 'u').replace('ç', 'c')
        text = text.replace('î', 'i').replace('ï', 'i')
        text = text.replace('°', 'o').replace('N°', 'No').replace('n°', 'no')
        
        # Fix spacing issues
        text = re.sub(r'(\d)\s+(\d)', r'\1\2', text)  # Remove spaces between digits
        
        # Fix brackets/braces that may be misinterpreted
        text = text.replace('[', '(').replace(']', ')')
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Clean up multiple spaces
        text = re.sub(r' {2,}', ' ', text)
        
        return text

    @staticmethod
    def _extract_french_invoice_data(text, data=None):
        """
        Robust extractor for French/Moroccan invoices: line items, totals, and TVA.
        Handles headers like 'Désignation | Quantité | Prix Unitaire HT | Total HT', tolerates OCR errors, and parses tables with whitespace or '|' as separators.
        Also extracts supplier and customer info, payment terms, and legal mentions.
        """
        import itertools
        import unicodedata
        import re
        if data is None:
            data = InvoiceParser._init_data('fr')
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        # Normalize text - fix common OCR errors
        text = text.replace('é', 'e').replace('è', 'e').replace('ê', 'e')
        text = text.replace('à', 'a').replace('â', 'a')
        text = text.replace('ô', 'o').replace('ù', 'u').replace('ç', 'c')
        text = text.replace('î', 'i').replace('ï', 'i')
        text = text.replace('°', 'o').replace('N°', 'No').replace('n°', 'no')
        
        # Helper function to parse numbers that may have commas as decimal or thousands separators
        def parse_number(num_str):
            try:
                # Remove currency symbols and whitespace
                num_str = re.sub(r'[$€£]', '', num_str.strip())
                # Remove "MAD" and other currency text
                num_str = re.sub(r'\s*MAD\s*', '', num_str, flags=re.IGNORECASE)
                num_str = re.sub(r'\s*WAD\s*', '', num_str, flags=re.IGNORECASE)
                num_str = re.sub(r'\s*DH\.?\s*', '', num_str, flags=re.IGNORECASE)
                # Remove spaces between digits
                num_str = re.sub(r'(\d)\s+(\d)', r'\1\2', num_str)
                
                # Fix improperly concatenated numbers (like "800,0011200,00")
                if len(num_str) > 8 and (',' in num_str or '.' in num_str):
                    # Try to split at a logical point
                    match = re.search(r'(\d+[.,]\d{2})(\d+[.,]\d{2})', num_str)
                    if match:
                        num_str = match.group(1)
                
                # Handle formats like "10,000.00" - comma as thousands separator
                if ',' in num_str and '.' in num_str:
                    return float(num_str.replace(',', ''))
                # Handle formats like "10.000,00" - period as thousands separator, comma as decimal
                elif ',' in num_str and not '.' in num_str:
                    return float(num_str.replace('.', '').replace(',', '.'))
                # Handle formats like "10000.00" - standard US format
                elif '.' in num_str and not ',' in num_str:
                    return float(num_str)
                # Handle formats like "10000,00" - comma as decimal
                elif ',' in num_str:
                    return float(num_str.replace(',', '.'))
                # Just a plain number
                else:
                    return float(num_str)
            except (ValueError, TypeError, AttributeError) as e:
                print(f"Error parsing number '{num_str}': {e}")
                return 0.0
        
        # --- Extract Supplier Info ---
        # Improved company name extraction
        if len(lines) > 0:
            potential_company_names = [
                lines[0],  # First line is often company name
                next((line for line in lines[:3] if re.search(r'S\.?A\.?R\.?L|S\.?A\.?S|S\.?A\.?', line)), None),
                next((line for line in lines[:3] if 'Société' in line or 'Societe' in line or 'SOCIETE' in line), None)
            ]
            company_name = next((name for name in potential_company_names if name), None)
            if company_name:
                data["supplier_info"]["name"] = company_name
                data["supplier_info"]["legal_name"] = company_name
            
        # --- Invoice Number and Date Extraction ---
        # Invoice number - Try enhanced patterns first
        invoice_patterns = [
            r'[Ff]acture\s*[Nn]?[°o]?\s*:?\s*(\w+[-/]?\d+)',
            r'[Ff]acture\s*[Nn]?[°o]?\s*:?\s*([A-Z0-9][-/]?\d+)',
            r'[Ff]acture\s*[Nn]?[°o]?\s*:?\s*(\d+)',
            r'[Nn][°o]?\s*:?\s*(\d+)',
            r'FACTURE\s*[Nn]?[°o]?\s*:?\s*(\w+[-/]?\d+)',
            r'FACTURE\s*[Nn]?[°o]?\s*(\d+)'
        ]
        
        for pattern in invoice_patterns:
            invoice_match = re.search(pattern, text)
            if invoice_match:
                data["invoice_number"] = invoice_match.group(1).strip()
                break
        
        # Date patterns - handle more formats including French format
        date_patterns = [
            r'[Dd]ate\s*:?\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})',
            r'[Dd]ate\s*:?\s*(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})',
            r'[Ff]es\s*le,?\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})',
            r'[Ll]e,?\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})',
            r'[Dd]ate\s*:?\s*(\d{8})',  # Format like 11052025
        ]
        
        for pattern in date_patterns:
            date_match = re.search(pattern, text)
            if date_match:
                date_str = date_match.group(1).strip()
                # Handle date without separators (e.g., 11052025 -> 11/05/2025)
                if len(date_str) == 8 and date_str.isdigit():
                    date_str = f"{date_str[:2]}/{date_str[2:4]}/{date_str[4:]}"
                data["date"] = date_str
                break
        
        # --- Line Item Extraction ---
        # Completely revamped line item extraction
        line_items = []
        line_item_id = 1
        
        # Process items that have clear quantity and value separation
        # Pattern 1: Look for "Travaux" style line items with quantity, unit price, amount
        travaux_pattern = r'(\d+[,.]?\d*)\s+(Travaux.*?|[A-Za-z][\w\s-]+(portable|service|maintenance|tractopelle|web))\s+(\d+[,.\s]*\d*)\s+(\d+[,.\s]*\d*)'
        for match in re.finditer(travaux_pattern, text, re.IGNORECASE):
            try:
                quantity_str = match.group(1).strip()
                description = match.group(2).strip()
                unit_price_str = match.group(4).strip()
                amount_str = match.group(5).strip()
                
                # Skip headers or if these look like totals
                if re.search(r'total|tva|montant\s+ttc|qte|designation', description, re.IGNORECASE):
                    continue
                
                quantity = float(quantity_str.replace(',', '.'))
                unit_price = parse_number(unit_price_str)
                amount = parse_number(amount_str)
                
                # Only add if values make sense
                if quantity > 0 and unit_price > 0 and amount > 0:
                    line_items.append({
                        "id": line_item_id,
                        "description": description,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "amount": amount,
                        "tax_rate": None,
                        "tax_amount": None
                    })
                    line_item_id += 1
            except Exception as e:
                print(f"Error parsing line item in travaux pattern: {e}")
                continue
                
        # Pattern 2: Computer hardware pattern for HP, DELL, etc.
        if not line_items:
            hardware_pattern = r'((?:HP|DELL|LENOVO|ASUS|ACER)[\\w\\s-]+?)\\s+(\\d+[,.]?\\d*)\\s+(\\d+[,.\\s]*\\d*)\\s+(\\d+[,.\\s]*\\d*)'
            for match in re.finditer(hardware_pattern, text, re.IGNORECASE):
                try:
                    description = match.group(1).strip()
                    quantity_str = match.group(2).strip()
                    unit_price_str = match.group(3).strip()
                    amount_str = match.group(4).strip()
                    
                    # Skip headers
                    if re.search(r'total|tva|montant\\s+ttc|qte|designation', description, re.IGNORECASE):
                        continue
                    
                    quantity = float(quantity_str.replace(',', '.'))
                    unit_price = parse_number(unit_price_str)
                    amount = parse_number(amount_str)
                    
                    if quantity > 0 and unit_price > 0 and amount > 0:
                        line_items.append({
                            "id": line_item_id,
                            "description": description,
                            "quantity": quantity,
                            "unit_price": unit_price,
                            "amount": amount,
                            "tax_rate": None,
                            "tax_amount": None
                        })
                        line_item_id += 1
                except Exception as e:
                    print(f"Error parsing hardware line item: {e}")
                    continue
                    
        # Pattern 3: More generic table extraction
        if not line_items:
            header_line_keywords = [
                r"D[eé]signation|Article|Description|Libell[eé]",
                r"Qt[eé]|Quantit[eé]|QTE|Unit[eé]|at[eé]", # 'até' is an OCR error for Qté
                r"P[.\s]*U[.\s]*H?T?|Prix\s*Unit",
                r"Montant|Total\s*H\.?T\.?",
            ]
            header_line_idx = -1
            lines_for_table_search = text.split('\\n')
            
            for i, line_content in enumerate(lines_for_table_search):
                line_content_normalized = line_content.lower()
                # Reduce false positives by checking line length and avoiding total lines as headers
                if len(line_content_normalized) < 10 or len(line_content_normalized) > 150 or "total" in line_content_normalized or "sous-total" in line_content_normalized :
                    continue

                matches = 0
                for kw_pattern in header_line_keywords:
                    if re.search(kw_pattern, line_content, re.IGNORECASE):
                        matches += 1
                if matches >= 3: # Require at least 3 keywords
                    # Further check: ensure it's not a line item itself by looking for too many numbers
                    numeric_parts = re.findall(r'[\d\s]+(?:[,.]\d+)?', line_content)
                    if len(numeric_parts) < 3 : # A header usually has fewer dense numeric parts than a full data row
                        header_line_idx = i
                        print(f"Potential header found at line {i}: {line_content}")
                        break

            if header_line_idx != -1:
                # More robust row pattern: Description Qty PU_HT Amt_HT (Optional TVA_Rate/Amt)
                # It tries to capture a description followed by 3 or 4 numeric groups.
                # The description part uses a negative lookahead to avoid consuming initial quantity if it's part of description.
                row_re = re.compile(
                    r"^(?P<desc>(?:(?!(?:\s|^)\d+(?:[,.]\d+)?\s+[\d\s.,]+).)*?)\s+"  # Description (non-greedy, stops before identifiable Qty pattern)
                    r"(?P<qty>\d+(?:[,.]\d+)?)\s+"                                   # Quantity
                    r"(?P<pu>[\d\s]+(?:[,.]\d+)?)\s+"                                # Unit Price
                    r"(?P<amt_ht>[\d\s]+(?:[,.]\d+)?)"                               # Amount HT
                    r"(?:\s+(?P<tva>[\d\s]+(?:[,.]\d+)?%?))?\s*$",                    # Optional TVA (rate or amount)
                    re.IGNORECASE
                )

                for line_content in lines_for_table_search[header_line_idx + 1:]:
                    line_content = line_content.strip()
                    if not line_content or re.match(r"^\s*(TOTAL|SOUS-TOTAL|ARR[ÊE]T[ÉE]E\s+LA\s+PR[ÉE]SENTE|Réference Réglement|ESPECE R[eé]ference)", line_content, re.IGNORECASE):
                        print(f"Stopping table parsing at: {line_content}")
                        break # Stop if we hit totals or summary lines

                    match = row_re.match(line_content)
                    if match:
                        try:
                            description = match.group("desc").strip()
                            quantity_str = match.group("qty")
                            unit_price_str = match.group("pu")
                            amount_ht_str = match.group("amt_ht")
                            tva_str = match.group("tva")

                            if not description and not quantity_str and not unit_price_str and not amount_ht_str: # All empty means likely not a valid match
                                continue

                            # Skip if description itself looks like a header fragment or is too short
                            if (re.search(r"designation|quantit|prix|montant|total|tva", description.lower(), re.IGNORECASE) and len(description) < 25) or len(description) < 3 :
                                # Check if the whole line is mostly non-alphanumeric, indicating it's not a real description
                                if not re.search(r'[a-zA-Z]{2,}', description): # if no word with at least 2 letters
                                     print(f"Skipping potential header-like/empty description row: {line_content}")
                                     continue


                            quantity = parse_number(quantity_str)
                            unit_price = parse_number(unit_price_str)
                            amount_ht = parse_number(amount_ht_str)

                            tva_rate = None
                            
                            if tva_str:
                                tva_str_cleaned = tva_str.strip()
                                if tva_str_cleaned.endswith('%'):
                                    tva_rate = parse_number(tva_str_cleaned.rstrip('%'))
                                elif parse_number(tva_str_cleaned) > 0 and amount_ht > 0: # If it's a number, and could be a tva_amount
                                    # Heuristic: if this tva_str is ~20% of amount_ht, it might be tva_amount, infer rate
                                    potential_tva_amount = parse_number(tva_str_cleaned)
                                    if abs(potential_tva_amount / amount_ht - 0.2) < 0.05: # If it's around 20%
                                        tva_rate = 20.0


                            # Basic validation
                            if quantity > 0: # PU or amount_ht must be present
                                calculated_amount = quantity * unit_price
                                # If unit_price is 0 but amount_ht is not, calculate unit_price
                                if unit_price == 0 and amount_ht > 0 and quantity > 0:
                                    unit_price = round(amount_ht / quantity, 2)
                                # If amount_ht is 0 but unit_price is not, calculate amount_ht
                                elif amount_ht == 0 and unit_price > 0 and quantity > 0:
                                    amount_ht = round(unit_price * quantity, 2)
                                # Or validate if both are present with tolerance
                                elif abs(calculated_amount - amount_ht) > max(1.0, 0.15 * amount_ht): # Increased tolerance to 15%
                                    print(f"Line item discrepancy: Qty({quantity})*PU({unit_price})={calculated_amount} != AmtHT({amount_ht}) for '{description}'")
                                    # Consider not skipping, but logging, as OCR can be imperfect

                                line_items.append({
                                    "id": line_item_id,
                                    "description": description,
                                    "quantity": quantity,
                                    "unit_price": unit_price,
                                    "amount": amount_ht,
                                    "tax_rate": tva_rate,
                                    "tax_amount": None 
                                })
                                line_item_id += 1
                        except Exception as e:
                            print(f"Error parsing table row with detailed pattern: '{line_content}', Error: {e}")
                            continue
                    else:
                        print(f"Row did not match detailed pattern: {line_content}")
            else:
                print("No suitable table header found for Pattern 3.")

        # If still no items, try different approach for Celatec style invoices with HP items (Original Pattern 3 / now a fallback)
        if not line_items:
            hp_pattern = r'(HP[\s\w-]+?(?:G\d|I\d)[\s\w-]+?(?:\d+GB|-\d+))\s+(\d+[,.]?\d*)\s+(\d+[,.\s]*\d*)\s+(\d+[,.\s]*\d*)'
            for match in re.finditer(hp_pattern, text, re.IGNORECASE):
                try:
                    description = match.group(1).strip()
                    quantity_str = match.group(2).strip() 
                    unit_price_str = match.group(3).strip()
                    amount_str = match.group(4).strip()
                    
                    quantity = float(quantity_str.replace(',', '.'))
                    unit_price = parse_number(unit_price_str)
                    amount = parse_number(amount_str)
                    
                    if quantity > 0 and unit_price > 0 and amount > 0:
                        line_items.append({
                            "id": line_item_id,
                            "description": description,
                            "quantity": quantity,
                            "unit_price": unit_price,
                            "amount": amount,
                            "tax_rate": None,
                            "tax_amount": None
                        })
                        line_item_id += 1
                except Exception as e:
                    print(f"Error parsing HP line item: {e}")
                    continue
        
        # Last resort pattern for looking at quantities and descriptions separated by multiple spaces
        if not line_items:
            for i, line in enumerate(lines):
                # Skip very short lines and headers
                if len(line) < 10 or re.search(r'total|tva|montant|ttc|qte', line, re.IGNORECASE):
                    continue
                    
                # Look for a line with a number at the beginning - might be quantity
                qty_match = re.match(r'^\s*(\d+[,.]?\d*)\s+([A-Za-z][\w\s-]+)$', line)
                if qty_match:
                    try:
                        quantity_str = qty_match.group(1).strip()
                        description = qty_match.group(2).strip()
                        
                        # Try to find price in next few lines
                        for j in range(1, 3):
                            if i + j < len(lines):
                                price_line = lines[i + j]
                                price_match = re.search(r'(\d+[,.\s]*\d*)\s+(\d+[,.\s]*\d*)', price_line)
                                if price_match:
                                    unit_price_str = price_match.group(1).strip()
                                    amount_str = price_match.group(2).strip()
                                    
                                    quantity = float(quantity_str.replace(',', '.'))
                                    unit_price = parse_number(unit_price_str)
                                    amount = parse_number(amount_str)
                                    
                                    if quantity > 0 and unit_price > 0 and amount > 0:
                                        line_items.append({
                                            "id": line_item_id,
                                            "description": description,
                                            "quantity": quantity,
                                            "unit_price": unit_price,
                                            "amount": amount,
                                            "tax_rate": None,
                                            "tax_amount": None
                                        })
                                        line_item_id += 1
                                        break
                    except Exception as e:
                        print(f"Error parsing line item from separated lines: {e}")
                        continue
        
        # --- Extract from K.A. TECHNO invoices with colored headers where line items are not visible ---
        # This handles cases where OCR cannot detect the line items due to colored backgrounds
        if not line_items and "K.A" in text and "TECHNO" in text:
            # Look for TOTAL TTC first (this is usually visible)
            total_ttc_values = re.finditer(r'TOTAL TTC\s*([\d\s.,]+)', text, re.IGNORECASE)
            for match in total_ttc_values:
                try:
                    total_value = parse_number(match.group(1))
                    if total_value > 0:
                        data["total"] = total_value
                        break
                except Exception as e:
                    print(f"Error parsing TOTAL TTC value: {e}")
            
            # If we found a total, try to extract or derive line items
            if data["total"] is not None and data["total"] > 0:
                # Look for service descriptions in the text
                service_patterns = [
                    r'(Installation|Reparation|Maintenance|Nettoyage|Travaux|Development|Hebergement|Service)\s+([^\n]+)',
                    r'(.*?[Ss]ervice.*?)'
                ]
                
                service_desc = None
                for pattern in service_patterns:
                    service_match = re.search(pattern, text, re.IGNORECASE)
                    if service_match:
                        if len(service_match.groups()) > 1:
                            service_desc = f"{service_match.group(1)} {service_match.group(2)}"
                        else:
                            service_desc = service_match.group(1)
                        break
                
                if service_desc is None:
                    # Look for anything that might be a service description
                    potential_desc = re.search(r'ICE\s*:.*?\n(.*?)\n', text, re.IGNORECASE | re.DOTALL)
                    if potential_desc:
                        for line in potential_desc.group(1).split('\n'):
                            if len(line.strip()) > 5 and not re.search(r'total|tva|montant|ttc|prix|unit|qte', line, re.IGNORECASE):
                                service_desc = line.strip()
                                break
                
                # Use a default if we couldn't find anything
                if service_desc is None:
                    service_desc = "Service professionnel"
                
                # Calculate VAT (assume 20% for Morocco)
                subtotal = data["total"] / 1.2  # Assuming VAT rate is 20%
                tax_amount = data["total"] - subtotal
                
                line_items.append({
                    "id": 1,
                    "description": service_desc,
                    "quantity": 1,
                    "unit_price": round(subtotal, 2),
                    "amount": round(subtotal, 2),
                    "tax_rate": 20.0,
                    "tax_amount": round(tax_amount, 2)
                })
                
                # Update the data with our calculated values
                data["subtotal"] = round(subtotal, 2)
                data["tax_amount"] = round(tax_amount, 2)
                data["tax_rate"] = 20.0
        
        data["line_items"] = line_items

        # Try to extract supplier name if it's still missing
        if not data["supplier_info"]["name"] and "ICE" in text:
            # Look for company name near ICE number
            ice_context = re.search(r'(?:.*?)(?:ICE\s*:\s*\d+)(?:.*?)(?:\n|$)', text)
            if ice_context:
                ice_text = ice_context.group(0)
                company_patterns = [
                    r'^\s*([\w\s\.]+)\s*$',  # Company name on its own line
                    r'([\w\s\.]+)\s+ICE\s*:'  # Company name before ICE
                ]
                for pattern in company_patterns:
                    company_match = re.search(pattern, ice_text, re.MULTILINE)
                    if company_match:
                        company = company_match.group(1).strip()
                        if len(company) > 3 and not re.search(r'ICE|RC|IF|Total|Date', company, re.IGNORECASE):
                            data["supplier_info"]["name"] = company
                            data["supplier_info"]["legal_name"] = company
                            break
        
        # --- Improved Totals Extraction ---
        # First try direct pattern matching for totals
        
        # 1. Look for Total HT
        total_ht_patterns = [
            r'TOTAL\s+H\.?T\.?\s*:?\s*([\d\s.,]+)',
            r'Total\s+H\.?T\.?\s*:?\s*([\d\s.,]+)',
            r'TOTAL\s+H\.?T\.?\s*([\d\s.,]+)',
            r'Total\s+H\.?T\.?\s*([\d\s.,]+)',
            r'TOTAL\s+H\.T\s*([\d\s.,]+)',
            r'T\.?\s*H\.?\s*T\.?\s*:?\s*([\d\s.,]+)'
        ]
        
        for pattern in total_ht_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    data["subtotal"] = parse_number(match.group(1))
                    break
                except Exception as e:
                    print(f"Error parsing Total HT: {e}")
        
        # 2. Look for TVA
        tva_patterns = [
            r'T\.?V\.?A\.?\s*\(?(\d+)%\)?\s*:?\s*([\d\s.,]+)',
            r'TVA\s*\(?(\d+)%\)?\s*:?\s*([\d\s.,]+)',
            r'TVA\s*:?\s*([\d\s.,]+)',
            r'T\.?V\.?A\.?\s*:?\s*([\d\s.,]+)',
            r'T\.?V\.?A\.?\s*([\d\s.,]+)'
        ]
        
        for pattern in tva_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) >= 2:
                        # Pattern with percentage and amount
                        data["tax_rate"] = float(groups[0])
                        data["tax_amount"] = parse_number(groups[1])
                    else:
                        # Pattern with just amount
                        data["tax_amount"] = parse_number(groups[0])
                        # If we have a subtotal, compute tax rate
                        if data["subtotal"] and data["subtotal"] > 0:
                            tax_rate = round((data["tax_amount"] / data["subtotal"]) * 100)
                            if 0 <= tax_rate <= 30:  # Sanity check
                                data["tax_rate"] = tax_rate
                    break
                except Exception as e:
                    print(f"Error parsing TVA: {e}")
        
        # 3. Look for Total TTC
        total_ttc_patterns = [
            r'TOTAL\s+T\.?T\.?C\.?\s*:?\s*([\d\s.,]+)',
            r'Total\s+T\.?T\.?C\.?\s*:?\s*([\d\s.,]+)',
            r'TOTAL\s+T\.?T\.?C\.?\s*([\d\s.,]+)',
            r'Total\s+T\.?T\.?C\.?\s*([\d\s.,]+)',
            r'T\.?T\.?C\.?\s*:?\s*([\d\s.,]+)'
        ]
        
        for pattern in total_ttc_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    data["total"] = parse_number(match.group(1))
                    break
                except Exception as e:
                    print(f"Error parsing Total TTC: {e}")
        
        # If totals are missing, look for specific text patterns common in Moroccan invoices
        if data["total"] is None:
            # Pattern for "arrêtée la présente facture à la somme de..."
            arretee_pattern = r'[Aa]rr[êe]t[ée]e\s+la\s+pr[ée]sente\s+facture\s+[aà]\s+la\s+somme\s+de\s*:?\s*(?:\()?(\d+[,.\s]*\d+)'
            match = re.search(arretee_pattern, text)
            if match:
                try:
                    data["total"] = parse_number(match.group(1))
                except Exception as e:
                    print(f"Error parsing 'arretee la presente': {e}")
        
        # If still missing, try numeric patterns that look like totals near bottom of invoice
        if data["total"] is None:
            # Look at the last third of the document for numbers that might be totals
            last_part = text[len(text)//2:]
            total_amount_candidates = []
            
            # Find all numbers that could be amounts
            amount_pattern = r'(\d{1,3}(?:[,.\s]\d{3})*(?:[,.]\d{2}))'
            for match in re.finditer(amount_pattern, last_part):
                try:
                    amount = parse_number(match.group(1))
                    if amount > 100:  # Arbitrary threshold to filter small numbers
                        total_amount_candidates.append(amount)
                except Exception:
                    continue
            
            # Use the largest amount as total, second largest as subtotal
            if total_amount_candidates:
                sorted_amounts = sorted(total_amount_candidates, reverse=True)
                if data["total"] is None and len(sorted_amounts) >= 1:
                    data["total"] = sorted_amounts[0]
                if data["subtotal"] is None and len(sorted_amounts) >= 2:
                    data["subtotal"] = sorted_amounts[1]
                if data["tax_amount"] is None and len(sorted_amounts) >= 3:
                    data["tax_amount"] = sorted_amounts[2]
        
        # Infer missing values based on what we have
        if data["subtotal"] is not None and data["tax_amount"] is not None and data["total"] is None:
            data["total"] = data["subtotal"] + data["tax_amount"]
        
        if data["subtotal"] is not None and data["total"] is not None and data["tax_amount"] is None:
            data["tax_amount"] = data["total"] - data["subtotal"]
            
        if data["subtotal"] is not None and data["tax_amount"] is not None and data["tax_rate"] is None and data["subtotal"] > 0:
            tax_rate = round((data["tax_amount"] / data["subtotal"]) * 100, 0)
            if 0 <= tax_rate <= 30:  # Sanity check
                data["tax_rate"] = tax_rate
            
        # Default values for Morocco
        if data["currency"] != "EUR" and data["currency"] != "USD":
            data["currency"] = "MAD"
            data["metadata"]["country"] = "MA"
            
        # Set default tax rate for Morocco if we have other tax info
        if data["tax_amount"] is not None and data["tax_rate"] is None:
            data["tax_rate"] = 20.0  # Default VAT in Morocco
        
        # Extract ICE - more flexible patterns
        ice_patterns = [
            r'ICE\s*:?\s*(\d+)',
            r'ICE\s*:?\s*N?o?\.?\s*:?\s*(\d+)',
            r'N[°o]?\s*ICE\s*:?\s*(\d+)',
            r'I\.?C\.?E\.?\s*:?\s*(\d+)'
        ]
        for pattern in ice_patterns:
            ice_match = re.search(pattern, text, re.IGNORECASE)
            if ice_match:
                data["supplier_info"]["ice"] = ice_match.group(1).strip()
                data["supplier_info"]["tax_id"] = ice_match.group(1).strip()
                break
        
        # Extract client ICE
        client_ice_pattern = r'(?:Client|CLIENT).*?ICE\s*:?\s*(\d+)'
        client_ice_match = re.search(client_ice_pattern, text, re.IGNORECASE | re.DOTALL)
        if client_ice_match:
            data["customer_info"]["ice"] = client_ice_match.group(1).strip()
            data["customer_info"]["tax_id"] = client_ice_match.group(1).strip()
        
        # Extract address
        address_patterns = [
            r'(?:Adresse|ADRESSE)\s*:?\s*([^,]+,\s*[^,]+(?:,\s*[^,]+)?)',
            r'(?:Rue|Avenue|Av\.|Lot|Route|ROUTE)[^\n]+'
        ]
        for pattern in address_patterns:
            address_match = re.search(pattern, text, re.IGNORECASE)
            if address_match:
                address = address_match.group(0) if 'Rue' in pattern else address_match.group(1)
                data["supplier_info"]["address"] = address.strip()
                break
        
        # Extract phone numbers
        phone_patterns = [
            r'[tT][ée]l(?:ephone)?\s*:?\s*(\+?\d+[\d\s]+\d+)',
            r'GSM\s*:?\s*(\+?\d+[\d\s]+\d+)',
            r'TELE\s*:?\s*(\+?\d+[\d\s]+\d+)'
        ]
        for pattern in phone_patterns:
            phone_match = re.search(pattern, text, re.IGNORECASE)
            if phone_match:
                data["supplier_info"]["phone"] = phone_match.group(1).strip()
                break
        
        # Extract email
        email_pattern = r'[eE]-?[mM]ail\s*:?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        email_match = re.search(email_pattern, text, re.IGNORECASE)
        if email_match:
            data["supplier_info"]["email"] = email_match.group(1).strip()
        
        # Payment method - defaults for Moroccan invoices
        payment_method_pattern = r'(?:Référence|Reference)\s+Règlement\s*:?\s*([^:]+?)(?:\n|$)'
        payment_match = re.search(payment_method_pattern, text, re.IGNORECASE)
        if payment_match:
            payment_info = payment_match.group(1).strip()
            data["payment_terms"] = payment_info
            
            # Try to identify payment method
            if re.search(r'ESPECE|espece|Espèce|ESPÈCE', payment_info, re.IGNORECASE):
                data["payment_method"] = "cash"
            elif re.search(r'virement|VIREMENT', payment_info, re.IGNORECASE):
                data["payment_method"] = "bank_transfer"
            elif re.search(r'chèque|CHEQUE|Chèque', payment_info, re.IGNORECASE):
                data["payment_method"] = "cheque"
        
        # Add a default tax rate for Morocco (20%) if we still don't have one
        if data["currency"] == "MAD" and data["tax_rate"] is None:
            data["tax_rate"] = 20.0
            
        # Try to extract supplier name if it's still missing
        if not data["supplier_info"]["name"] and "ICE" in text:
            # Look for company name near ICE number
            ice_context = re.search(r'(?:.*?)(?:ICE\s*:\s*\d+)(?:.*?)(?:\n|$)', text)
            if ice_context:
                ice_text = ice_context.group(0)
                company_patterns = [
                    r'^\s*([\w\s\.]+)\s*$',  # Company name on its own line
                    r'([\w\s\.]+)\s+ICE\s*:'  # Company name before ICE
                ]
                for pattern in company_patterns:
                    company_match = re.search(pattern, ice_text, re.MULTILINE)
                    if company_match:
                        company = company_match.group(1).strip()
                        if len(company) > 3 and not re.search(r'ICE|RC|IF|Total|Date', company, re.IGNORECASE):
                            data["supplier_info"]["name"] = company
                            data["supplier_info"]["legal_name"] = company
                            break
        
        # --- Robust Two-Pass Line Item Extraction for French Invoices ---
        if not line_items:
            # First pass: Try to find a header and extract table rows as before
            header_keywords = [
                "designation", "désignation", "article", "description", "libellé", "libelle",
                "qté", "qte", "quantité", "quantite", "até", "qte.",
                "p.u.", "pu", "prix unitaire", "prix unit", "prix u", "p u",
                "montant", "total", "montant ht", "total ht"
            ]
            header_idx = -1
            for i, line in enumerate(lines):
                found = sum(1 for kw in header_keywords if kw in line.lower())
                if found >= 2:
                    header_idx = i
                    break
            if header_idx != -1:
                current_desc = []
                for line in lines[header_idx+1:]:
                    if re.search(r'total|arr[êe]t[ée]e|réference|reglement|signature', line, re.IGNORECASE):
                        break
                    # Improved number extraction: split numbers like '11200,002 240,00' into two
                    numbers = re.findall(r'\d{1,3}(?:[\s.,]\d{3})*(?:[.,]\d{2})', line)
                    if len(numbers) >= 2:
                        description = " ".join(current_desc).strip()
                        quantity = parse_number(numbers[0]) if len(numbers) > 0 else 1
                        unit_price = parse_number(numbers[1]) if len(numbers) > 1 else 0
                        amount = parse_number(numbers[2]) if len(numbers) > 2 else unit_price * quantity
                        tva = parse_number(numbers[3]) if len(numbers) > 3 else None
                        if description and quantity > 0 and (unit_price > 0 or amount > 0):
                            line_items.append({
                                "id": line_item_id,
                                "description": description,
                                "quantity": quantity,
                                "unit_price": unit_price,
                                "amount": amount if amount > 0 else unit_price * quantity,
                                "tax_rate": tva,
                                "tax_amount": None
                            })
                            line_item_id += 1
                        current_desc = []
                    else:
                        if line.strip():
                            current_desc.append(line)
            # Second pass: If no header found, scan all lines for those with at least two numbers
            if not line_items:
                current_desc = []
                for i, line in enumerate(lines):
                    # Improved number extraction: split numbers like '11200,002 240,00' into two
                    numbers = re.findall(r'\d{1,3}(?:[\s.,]\d{3})*(?:[.,]\d{2})', line)
                    if len(numbers) >= 2:
                        # Use previous non-empty lines as description
                        j = i - 1
                        desc_lines = []
                        while j >= 0 and len(desc_lines) < 2:
                            prev_line = lines[j].strip()
                            if prev_line and not re.search(r'\d{1,3}(?:[\s.,]\d{3})*(?:[.,]\d{2})', prev_line):
                                desc_lines.insert(0, prev_line)
                            j -= 1
                        description = " ".join(desc_lines).strip()
                        quantity = parse_number(numbers[0]) if len(numbers) > 0 else 1
                        unit_price = parse_number(numbers[1]) if len(numbers) > 1 else 0
                        amount = parse_number(numbers[2]) if len(numbers) > 2 else unit_price * quantity
                        tva = parse_number(numbers[3]) if len(numbers) > 3 else None
                        if description and quantity > 0 and (unit_price > 0 or amount > 0):
                            line_items.append({
                                "id": line_item_id,
                                "description": description,
                                "quantity": quantity,
                                "unit_price": unit_price,
                                "amount": amount if amount > 0 else unit_price * quantity,
                                "tax_rate": tva,
                                "tax_amount": None
                            })
                            line_item_id += 1
                        current_desc = []
        data["line_items"] = line_items

        return data
    
    @staticmethod
    def _extract_line_items(text, lang):
        """
        Simplified line items extraction focused on robust pattern detection
        Works with multiple invoice formats by using simple row-based patterns
        """
        line_items = []
        line_item_id = 1
        data = {}
        
        # Step 1: Find the actual ORDER LINES section (for YH45687 format)
        # Look specifically for the table structure with the header pattern
        order_table_section = re.search(r'ORDER\s+LINES.*?(?:Description\s+Quantity\s+Unit\s+Price\s+Amount).*?(?:Subtotal|Total|Payment)', text, re.IGNORECASE | re.DOTALL)
        
        if order_table_section:
            section_text = order_table_section.group(0)
            # Find rows in the table - these are the actual line items
            # Look for lines with text followed by numbers and currency symbols
            row_matches = re.findall(r'([a-zA-Z][^\n$]+?)\s+(\d+(?:\.\d+)?)\s+(\w+)\s+\$(\d+\.\d+)\s+\$(\d+\.\d+)', section_text)
            
            for match in row_matches:
                # Only process rows that appear to be valid line items
                # Skip rows containing payment info like "IBAN", "Bank", etc.
                description = match[0].strip()
                if any(payment_term in description.lower() for payment_term in ["iban", "bank", "swift", "payment", "account"]):
                    continue
                    
                try:
                    quantity = float(match[1])
                    unit = match[2].strip()
                    price = float(match[3])
                    amount = float(match[4])
                    
                    # Validate: amount should be approximately quantity * price
                    calculated_amount = quantity * price
                    if abs(calculated_amount - amount) > 0.1 * calculated_amount:
                        # Skip if amount doesn't match quantity * price within 10% tolerance
                        continue
                    
                    # Only add items with positive values
                    if quantity > 0 and price > 0 and amount > 0:
                        line_items.append({
                            "description": description,
                            "quantity": quantity,
                            "unit": unit,
                            "price": price,
                            "amount": amount
                        })
                except (ValueError, IndexError):
                    continue
        
        # If no line items found using the structured approach, try the general approach
        if not line_items:
            # Look for any lines with Description + numbers pattern
            # This is more general and works with various formats  
            # Split the text into lines for processing
            lines = text.split('\n')
            
            # Define a section to ignore at the bottom of the invoice (payment details, footer info)
            footer_section_start = False
            for line in lines:
                # Skip lines that are too short or don't have numbers
                if len(line) < 5 or not re.search(r'\d+', line):
                    continue
                
                # Skip footer sections with payment info
                if any(term in line.lower() for term in ["payment", "iban", "bank", "swift", "bic"]):
                    footer_section_start = True
                    continue
                
                if footer_section_start:
                    continue
                
                # Try different patterns:
                
                # Pattern 1: Text followed by number, currency+number, currency+number
                # Example: "Item description 5 $10.00 $50.00"
                p1 = re.match(r'([a-zA-Z].*?)\s+(\d+(?:\.\d+)?)\s+[$€£]?(\d+(?:\.\d+)?)\s+[$€£]?(\d+(?:\.\d+)?)', line)
                if p1:
                    try:
                        quantity = float(p1.group(2))
                        price = float(p1.group(3))
                        amount = float(p1.group(4))
                        
                        # Validate quantity * price ≈ amount
                        if abs(quantity * price - amount) > 0.1 * (quantity * price):
                            continue
                            
                        line_items.append({
                            "description": p1.group(1).strip(),
                            "quantity": quantity,
                            "unit": "unit",  # Default unit
                            "price": price,
                            "amount": amount
                        })
                        continue
                    except (ValueError, IndexError):
                        pass
                
                # Pattern 2: Text followed by number, text (unit), currency+number, currency+number
                # Example: "Item description 5 each $10.00 $50.00"
                p2 = re.match(r'([a-zA-Z].*?)\s+(\d+(?:\.\d+)?)\s+([a-zA-Z]+)\s+[$€£]?(\d+(?:\.\d+)?)\s+[$€£]?(\d+(?:\.\d+)?)', line)
                if p2:
                    try:
                        quantity = float(p2.group(2))
                        price = float(p2.group(4))
                        amount = float(p2.group(5))
                        
                        # Validate quantity * price ≈ amount
                        if abs(quantity * price - amount) > 0.1 * (quantity * price):
                            continue
                            
                        line_items.append({
                            "description": p2.group(1).strip(),
                            "quantity": quantity,
                            "unit": p2.group(3),
                            "price": price,
                            "amount": amount
                        })
                        continue
                    except (ValueError, IndexError):
                        pass
                
                # Pattern 3: Number (reference), text, number, number, number
                # Example: "12345 Item description 5 10.00 50.00"
                p3 = re.match(r'(\d+)\s+([a-zA-Z].*?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)', line)
                if p3:
                    try:
                        quantity = float(p3.group(3))
                        price = float(p3.group(4))
                        amount = float(p3.group(5))
                        
                        # Validate quantity * price ≈ amount
                        if abs(quantity * price - amount) > 0.1 * (quantity * price):
                            continue
                            
                        line_items.append({
                            "description": f"{p3.group(1)} - {p3.group(2).strip()}",
                            "quantity": quantity,
                            "unit": "unit",
                            "price": price,
                            "amount": amount
                        })
                        continue
                    except (ValueError, IndexError):
                        pass
        
        # --- Improved Line Item Extraction ---
        # Try to match lines like: Description Quantity UnitPrice MAD Total MAD (tolerant to , and .)
        improved_lineitem_pattern = re.compile(r'(.+?)\s+(\d+)\s+([\d.,]+)\s*MAD\s+([\d.,]+)\s*MAD', re.IGNORECASE)
        for match in improved_lineitem_pattern.finditer(text):
            try:
                description = match.group(1).strip()
                quantity = float(match.group(2))
                unit_price = float(match.group(3).replace(',', '').replace('.', ''))
                amount = float(match.group(4).replace(',', '').replace('.', ''))
                if quantity > 0 and unit_price > 0 and amount > 0:
                    line_items.append({
                        "id": line_item_id,
                        "description": description,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "amount": amount,
                        "tax_rate": None,
                        "tax_amount": None
                    })
                    line_item_id += 1
            except Exception:
                continue
        # Remove duplicates
        seen = set()
        unique_line_items = []
        for item in line_items:
            key = (item['description'], item['quantity'], item['unit_price'], item['amount'])
            if key not in seen:
                unique_line_items.append(item)
                seen.add(key)
        line_items = unique_line_items
        data["line_items"] = line_items
        # --- Improved Totals Extraction ---
        # Only use fallback if these fail
        data["subtotal"] = None
        data["tax_amount"] = None
        data["total"] = None
        total_ht_match = re.search(r'Total HT\s*[:.]?\s*([\d.,]+)\s*MAD', text, re.IGNORECASE)
        if total_ht_match:
            data["subtotal"] = float(total_ht_match.group(1).replace(',', '').replace('.', ''))
        tva_match = re.search(r'TVA\s*\(\d+%\)\s*[:.]?\s*([\d.,]+)\s*MAD', text, re.IGNORECASE)
        if tva_match:
            data["tax_amount"] = float(tva_match.group(1).replace(',', '').replace('.', ''))
            # Extract tax rate
            rate_match = re.search(r'TVA\s*\((\d+)%\)', text, re.IGNORECASE)
            if rate_match:
                data["tax_rate"] = float(rate_match.group(1))
        total_ttc_match = re.search(r'Total TTC\s*[:.]?\s*([\d.,]+)\s*MAD', text, re.IGNORECASE)
        if total_ttc_match:
            data["total"] = float(total_ttc_match.group(1).replace(',', '').replace('.', ''))
        # --- Improved Invoice Number and Date Extraction ---
        if not data.get("invoice_number"):
            m = re.search(r'Facture\s*N[°o*:.]?\s*([\w\-/]+)', text, re.IGNORECASE)
            if not m:
                m = re.search(r'Facure\s*N[°o*:.]?\s*([\w\-/]+)', text, re.IGNORECASE)
            if m:
                data["invoice_number"] = m.group(1).strip()
        if not data.get("date"):
            m = re.search(r'Date\s*[:.]?\s*([\d]{2}/[\d]{2}/[\d]{4})', text)
            if not m:
                m = re.search(r'Date\s*[:.]?\s*([\d]{8})', text)
            if m:
                date_str = m.group(1)
                if re.match(r'\d{8}', date_str):
                    date_str = f"{date_str[:2]}/{date_str[2:4]}/{date_str[4:]}"
                data["date"] = date_str
        # --- Only use fallback for totals if main patterns fail ---
        if (data["subtotal"] is None or data["tax_amount"] is None or data["total"] is None):
            # Fallback: Extract all lines with numbers and 'MAD' (or common OCR variants) if nothing else worked
            mad_variants = r'(MAD|WAD|map|wad|mad|MaD|mad)'
            mad_lines = [l for l in lines if re.search(r'\d+[\d,. ]*\s*' + mad_variants, l, re.IGNORECASE)]
            amounts = []
            for l in mad_lines:
                for m in re.finditer(r'([\d ]+[,.]?\d*)\s*' + mad_variants, l, re.IGNORECASE):
                    try:
                        val = float(m.group(1).replace(' ', '').replace(',', '.'))
                        amounts.append((val, l))
                    except Exception:
                        continue
            amounts = sorted(amounts, key=lambda x: -x[0])
            if amounts:
                if data["total"] is None:
                    data["total"] = amounts[0][0]
                if len(amounts) > 1 and data["tax_amount"] is None:
                    data["tax_amount"] = amounts[1][0]
                if len(amounts) > 2 and data["subtotal"] is None:
                    data["subtotal"] = amounts[2][0]
        # Remove items with nonsense values (again)
        line_items = [li for li in line_items if li['quantity'] > 0 and li['unit_price'] > 0 and li['amount'] > 0]
        data["line_items"] = line_items
        return data
    
    @classmethod
    def check_dependencies(cls):
        """
        Check if required dependencies (Tesseract, Poppler) are properly installed
        
        Returns:
            tuple: (is_tesseract_installed, is_poppler_installed)
        """
        is_tesseract_installed = False
        is_poppler_installed = False
        
        # Check Tesseract
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            is_tesseract_installed = True
        except (ImportError, pytesseract.TesseractNotFoundError):
            is_tesseract_installed = False
            
        # Check Poppler
        try:
            # Create a tiny test PDF
            test_pdf_bytes = b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%EOF"
            convert_from_bytes(test_pdf_bytes, size=1)
            is_poppler_installed = True
        except Exception:
            is_poppler_installed = False
            
        return is_tesseract_installed, is_poppler_installed
    
    @classmethod
    def get_dependency_installation_instructions(cls):
        """
        Get installation instructions for Tesseract and Poppler
        
        Returns:
            dict: Installation instructions for different platforms
        """
        return {
            "tesseract": {
                "windows": "1. Download and install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki\n"
                          "2. Add the Tesseract installation directory to your PATH environment variable",
                "linux": "sudo apt-get install tesseract-ocr",
                "mac": "brew install tesseract"
            },
            "poppler": {
                "windows": "1. Download and install Poppler from https://github.com/oschwartz10612/poppler-windows/releases\n"
                          "2. Add the Poppler bin directory to your PATH environment variable",
                "linux": "sudo apt-get install poppler-utils",
                "mac": "brew install poppler"
            }
        }