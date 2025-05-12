import re
import io
import traceback
from PIL import Image
from pdf2image import convert_from_bytes
import pytesseract
from decimal import Decimal, DecimalException, InvalidOperation
import langdetect


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
                r'(?<!\S)([A-Z][0-9]{6,})(?!\S)'
            ],
            'date': [
                r'date[:\s]*([\d]{1,2}[-/\.][\d]{1,2}[-/\.][\d]{2,4})',
                r'date[:\s]*(\d{4}-\d{1,2}-\d{1,2})',
                r'date:\s*([\d]{1,2}/[\d]{1,2}/[\d]{4})'
            ],
            'due_date': [
                r'\b[ée]ch[ée]ance[:\s]*([\d]{1,2}[-/\.][\d]{1,2}[-/\.][\d]{2,4})',
                r'\b[ée]ch[ée]ance[:\s]*(\d{4}-\d{1,2}-\d{1,2})',
                r'\b[ée]ch[ée]ance:\s*([\d]{1,2}/[\d]{1,2}/[\d]{4})'
            ],
            'from': r'de[:\s]*\n*([\s\S]*?)(?=\n\s*\n|\n[aà] l[ae][:\s]*|\Z)',
            'to': r'[aà] l[ae][:\s]*\n*([\s\S]*?)(?=\n\s*\n|\nlignes de commande|\Z)',
            'order_lines': r'lignes de commande.*?\n([\s\S]*?)(?=\n\s*\n|\nsous-total|\ntotal|\Z)',
            'subtotal': [r'sous-total[:\s]*€?(\d+\.\d+)', r'sous[ -]?total[:\s]*€?(\d+\.\d+)'],
            'tax': [r'tva\s*(?:\((\d+)%\))?[:\s]*€?(\d+\.\d+)', r'taxe\s*(?:\((\d+)%\))?[:\s]*€?(\d+\.\d+)'],
            'total': [r'total[:\s]*€?(\d+\.\d+)', r'montant total[:\s]*€?(\d+\.\d+)', r'montant dû[:\s]*€?(\d+\.\d+)'],
            'line_headers': [
                ['désignation', 'quantité', 'unité', 'prix', 'montant'],
                ['article', 'qté', 'uom', 'tarif', 'total']
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
        
        Args:
            invoice_file: The uploaded file object
            
        Returns:
            tuple: (extracted_text, file_extension)
            
        Raises:
            Exception: If file format is unsupported or extraction fails
        """
        file_extension = invoice_file.name.split('.')[-1].lower()
        
        if file_extension == 'pdf':
            # Convert PDF to images
            images = convert_from_bytes(invoice_file.read())
            text = ""
            for img in images:
                img_byte_array = io.BytesIO()
                img.save(img_byte_array, format='PNG')
                img_byte_array.seek(0)
                text += pytesseract.image_to_string(Image.open(img_byte_array))
            return text, file_extension
        elif file_extension in ['jpg', 'jpeg', 'png']:
            text = pytesseract.image_to_string(Image.open(invoice_file))
            return text, file_extension
        else:
            raise ValueError("Unsupported file format. Please upload PDF, JPG, or PNG.")
    
    @staticmethod
    def extract_invoice_data(text):
        """
        Extract structured data from regular invoice text
        
        Args:
            text: The extracted text from the invoice file
            
        Returns:
            dict: Structured data extracted from the invoice
        """
        # Default empty data structure
        data = {
            "invoice_number": "",
            "date": "",
            "due_date": "",
            "supplier_info": {
                "name": "",
                "address": "",
                "email": "",
                "phone": ""
            },
            "customer_info": {
                "name": "",
                "address": "",
                "email": "",
                "phone": ""
            },
            "line_items": [],
            "subtotal": None,
            "tax_amount": None,
            "tax_rate": None,
            "total": None,
            "currency": "$"
        }
        
        # Implement your invoice data extraction logic here
        # This is a placeholder - actual implementation would depend on
        # what the original _extract_invoice_data method did
        
        return data
    
    @staticmethod
    def extract_expenditure_invoice_data(text):
        """
        Extract structured data from expenditure invoice text
        Specifically tailored for expenditure invoices from suppliers
        
        Args:
            text: The extracted text from the invoice file
            
        Returns:
            dict: Structured data extracted from the invoice
        """
        # First, check if this looks like a French invoice
        if re.search(r'Facture\s+N[°o]|Société|Désignation|Total\s+HT', text, re.IGNORECASE):
            return InvoiceParser._extract_french_invoice_data(text)
            
        # If not a French invoice, proceed with the regular extraction
        lang = InvoiceParser.detect_language(text)
        patterns = InvoiceParser.FIELD_PATTERNS[lang]
        data = {
            "invoice_number": "",
            "status": "",
            "date": "",
            "due_date": "",
            "paid_date": "",
            "supplier_info": {"name": "", "tax_id": "", "address": "", "email": "", "phone": ""},
            "customer_info": {"name": "", "tax_id": "", "address": "", "reference": "", "email": "", "phone": ""},
            "line_items": [],
            "subtotal": None,
            "tax_amount": None,
            "tax_rate": None,
            "total": None,
            "currency": "$",
            "invoice_type": "purchase"
        }
        
        # Extract invoice number
        for pattern in patterns['invoice_number']:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                data["invoice_number"] = m.group(1).strip()
                break
        
        # Extract date
        for pattern in patterns['date']:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                data["date"] = m.group(1).strip()
                break
        
        # Extract due date
        for pattern in patterns['due_date']:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                data["due_date"] = m.group(1).strip()
                break
        
        # Extract parties
        from_section = re.search(patterns['from'], text, re.IGNORECASE)
        if from_section:
            supplier_text = from_section.group(1).strip()
            lines = supplier_text.split('\n')
            if lines:
                data["supplier_info"]["name"] = lines[0].strip()
                for line in lines[1:]:
                    if re.match(r'^\d+$', line) or 'ice' in line.lower():
                        data["supplier_info"]["tax_id"] = line
        
        to_section = re.search(patterns['to'], text, re.IGNORECASE)
        if to_section:
            customer_text = to_section.group(1).strip()
            lines = customer_text.split('\n')
            if lines:
                data["customer_info"]["name"] = lines[0].strip()
                email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', customer_text)
                if email_match:
                    data["customer_info"]["email"] = email_match.group(1).strip()
                phone_match = re.search(r'tel[:\s]*([0-9\s\-\+]+)', customer_text, re.IGNORECASE)
                if phone_match:
                    data["customer_info"]["phone"] = phone_match.group(1).strip()
        
        # Extract line items
        data["line_items"] = InvoiceParser._extract_line_items(text)
        
        # Extract totals
        for pattern in patterns['subtotal']:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                try:
                    data["subtotal"] = float(m.group(1))
                    break
                except Exception:
                    pass
        
        for pattern in patterns['tax']:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                try:
                    if m.group(1):
                        data["tax_rate"] = float(m.group(1))
                    data["tax_amount"] = float(m.group(2))
                    break
                except Exception:
                    pass
        
        for pattern in patterns['total']:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                try:
                    data["total"] = float(m.group(1))
                    break
                except Exception:
                    pass
        
        # Calculate missing values
        if data["subtotal"] is None and data["line_items"]:
            try:
                data["subtotal"] = sum(item["amount"] for item in data["line_items"])
            except Exception:
                pass
        
        if data["total"] is None and data["subtotal"] is not None and data["tax_amount"] is not None:
            data["total"] = data["subtotal"] + data["tax_amount"]
        
        if data["tax_amount"] is None and data["subtotal"] is not None and data["tax_rate"] is not None:
            data["tax_amount"] = data["subtotal"] * (data["tax_rate"] / 100)
            if data["total"] is None:
                data["total"] = data["subtotal"] + data["tax_amount"]
        
        return data
    
    @staticmethod
    def _extract_french_invoice_data(text):
        """
        Specialized extractor for French invoices with format:
        - Company name at top
        - Client section
        - Facture N° and Date
        - Désignation/Quantité/Prix Unitaire HT/Total HT table
        - Total HT, TVA and Total TTC at bottom
        """
        # Default empty data
        data = {
            "invoice_number": "",
            "status": "",
            "date": "",
            "due_date": "",
            "paid_date": "",
            "supplier_info": {"name": "", "tax_id": "", "address": "", "email": "", "phone": ""},
            "customer_info": {"name": "", "tax_id": "", "address": "", "reference": "", "email": "", "phone": ""},
            "line_items": [],
            "subtotal": None,
            "tax_amount": None,
            "tax_rate": None,
            "total": None,
            "currency": "€",  # Default to EUR for French invoices, will be updated if MAD or other currency found
            "invoice_type": "purchase" 
        }
        
        # Split into lines for processing
        lines = text.split('\n')
        
        # First line is usually the company name (supplier)
        if lines:
            data["supplier_info"]["name"] = lines[0].strip()
        
        # Extract invoice number - look for "Facture N°"
        invoice_number_match = re.search(r'Facture\s+N[°o]\s*[:.]?\s*([0-9a-zA-Z\-_/]+)', text, re.IGNORECASE)
        if invoice_number_match:
            data["invoice_number"] = invoice_number_match.group(1).strip()
        
        # Extract date - look for "Date :"
        date_match = re.search(r'Date\s*[:.]?\s*([\d]{1,2}[-/\.][\d]{1,2}[-/\.][\d]{2,4})', text, re.IGNORECASE)
        if date_match:
            data["date"] = date_match.group(1).strip()
        
        # Extract supplier tax ID (ICE)
        ice_match = re.search(r'ICE\s*[:.]?\s*([0-9]+)', text, re.IGNORECASE)
        if ice_match:
            data["supplier_info"]["tax_id"] = ice_match.group(1).strip()
        
        # Extract supplier contact info
        email_match = re.search(r'Email\s*[:.]?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text, re.IGNORECASE)
        if email_match:
            data["supplier_info"]["email"] = email_match.group(1).strip()
        
        phone_match = re.search(r'T[ée]l[ée]phone\s*[:.]?\s*([0-9\s\-\+]+)', text, re.IGNORECASE)
        if phone_match:
            data["supplier_info"]["phone"] = phone_match.group(1).strip()
        
        # Extract supplier address - typically second line
        if len(lines) > 1:
            # Look for address pattern (street, city)
            address_lines = []
            for i in range(1, min(3, len(lines))):
                if re.search(r'Rue|Avenue|Boulevard|Place|Route', lines[i], re.IGNORECASE):
                    address_lines.append(lines[i].strip())
            
            if address_lines:
                data["supplier_info"]["address"] = " ".join(address_lines)
        
        # Extract customer info - look for "Client :" section
        client_section_match = re.search(r'Client\s*:?\s*\n(.*?)(?=\n\s*\n|\nFacture|\nDésignation|\Z)', text, re.IGNORECASE | re.DOTALL)
        if client_section_match:
            client_text = client_section_match.group(1).strip()
            client_lines = client_text.split('\n')
            
            if client_lines:
                data["customer_info"]["name"] = client_lines[0].strip()
            
            if len(client_lines) > 1:
                # Address is usually second line
                data["customer_info"]["address"] = client_lines[1].strip()
            
            # Look for customer ICE
            client_ice_match = re.search(r'ICE\s*[:.]?\s*([0-9]+)', client_text, re.IGNORECASE)
            if client_ice_match:
                data["customer_info"]["tax_id"] = client_ice_match.group(1).strip()
        
        # Extract currency - look for currency code in the text
        currency_match = re.search(r'(\bMAD\b|\bEUR\b|\b€\b|\$)', text)
        if currency_match:
            currency_code = currency_match.group(1).upper()
            if currency_code == 'MAD':
                data["currency"] = 'MAD'
            elif currency_code == 'EUR' or currency_code == '€':
                data["currency"] = '€'
            elif currency_code == '$':
                data["currency"] = '$'
        
        # Extract line items - look for table with Désignation/Quantité/Prix/Total columns
        # First find the header line
        header_match = re.search(r'Désignation\s+Quantité\s+Prix.*?\s+Total', text, re.IGNORECASE)
        
        if header_match:
            # Get the content after the header until "Total HT"
            header_pos = text.find(header_match.group(0))
            table_section = text[header_pos:]
            end_pos = table_section.find('Total HT')
            if end_pos > 0:
                table_section = table_section[:end_pos]
            
            # Split by lines and skip the header
            table_lines = table_section.split('\n')
            table_lines = table_lines[1:] if len(table_lines) > 1 else []
            
            # Process each non-empty line
            for line in table_lines:
                if not line.strip():
                    continue
                
                # Try to match our specific line item pattern
                # For "Développement Web 1 10,000.00 MAD 10,000.00 MAD"
                item_match1 = re.search(r'([a-zA-Z].*?)\s+(\d+(?:[,.]\d+)?)\s+(?:an)?\s*(\d+(?:[,.]\d+)?)\s*(?:MAD|EUR|€|\$)?\s+(\d+(?:[,.]\d+)?)', line)
                
                # For "Hébergement 1 an 1,200.00 MAD 1,200.00 MAD"
                item_match2 = re.search(r'([a-zA-Z].*?)\s+(\d+)\s+(an|jour|mois|heure|heures)\s+(\d+(?:[,.]\d+)?)\s*(?:MAD|EUR|€|\$)?\s+(\d+(?:[,.]\d+)?)', line)
                
                try:
                    if item_match2:  # Match with unit like "an"
                        description = item_match2.group(1).strip()
                        quantity = float(item_match2.group(2))
                        unit = item_match2.group(3).strip()
                        # Convert price and amount - handling French format with commas
                        price_str = item_match2.group(4).replace('.', '').replace(',', '.')
                        price = float(price_str)
                        amount_str = item_match2.group(5).replace('.', '').replace(',', '.')
                        amount = float(amount_str)
                        
                        data["line_items"].append({
                            "description": description,
                            "quantity": quantity,
                            "unit": unit,
                            "price": price,
                            "amount": amount
                        })
                    elif item_match1:  # Standard match
                        description = item_match1.group(1).strip()
                        quantity = float(item_match1.group(2))
                        # Convert price and amount - handling French format with commas
                        price_str = item_match1.group(3).replace('.', '').replace(',', '.')
                        price = float(price_str)
                        amount_str = item_match1.group(4).replace('.', '').replace(',', '.')
                        amount = float(amount_str)
                        
                        data["line_items"].append({
                            "description": description,
                            "quantity": quantity,
                            "unit": "unit", # Default unit if none specified
                            "price": price,
                            "amount": amount
                        })
                except (ValueError, IndexError) as e:
                    print(f"Error parsing line item: {e}")
                    continue
        
        # Extract totals
        # Total HT (Subtotal)
        total_ht_match = re.search(r'Total\s+HT\s*:\s*([\d\s,.]+)', text, re.IGNORECASE)
        if total_ht_match:
            try:
                # Clean up value and handle French number format
                subtotal_str = total_ht_match.group(1).strip()
                subtotal_str = subtotal_str.replace(' ', '').replace('.', '').replace(',', '.')
                data["subtotal"] = float(subtotal_str)
            except (ValueError, IndexError):
                pass
        
        # TVA (Tax)
        tva_match = re.search(r'TVA\s*\((\d+)%\)\s*:\s*([\d\s,.]+)', text, re.IGNORECASE)
        if tva_match:
            try:
                data["tax_rate"] = float(tva_match.group(1))
                # Clean up value and handle French number format
                tax_str = tva_match.group(2).strip()
                tax_str = tax_str.replace(' ', '').replace('.', '').replace(',', '.')
                data["tax_amount"] = float(tax_str)
            except (ValueError, IndexError):
                pass
        
        # Total TTC (Total with tax)
        total_ttc_match = re.search(r'Total\s+TTC\s*:\s*([\d\s,.]+)', text, re.IGNORECASE)
        if total_ttc_match:
            try:
                # Clean up value and handle French number format
                total_str = total_ttc_match.group(1).strip()
                total_str = total_str.replace(' ', '').replace('.', '').replace(',', '.')
                data["total"] = float(total_str)
            except (ValueError, IndexError):
                pass
        
        # If we have subtotal and tax rate but no tax amount, calculate it
        if data["subtotal"] is not None and data["tax_rate"] is not None and data["tax_amount"] is None:
            data["tax_amount"] = data["subtotal"] * (data["tax_rate"] / 100)
        
        # If we have subtotal and tax amount but no total, calculate it
        if data["subtotal"] is not None and data["tax_amount"] is not None and data["total"] is None:
            data["total"] = data["subtotal"] + data["tax_amount"]
        
        return data
    
    @staticmethod
    def _extract_line_items(text):
        """
        Simplified line items extraction focused on robust pattern detection
        Works with multiple invoice formats by using simple row-based patterns
        """
        line_items = []
        
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
        
        return line_items
    
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