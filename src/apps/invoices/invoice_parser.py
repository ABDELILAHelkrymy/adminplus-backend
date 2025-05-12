import re
import io
import traceback
from PIL import Image
from pdf2image import convert_from_bytes
import pytesseract
from decimal import Decimal, DecimalException, InvalidOperation


class InvoiceParser:
    """
    Class responsible for parsing and extracting data from invoice files
    """
    
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
        # Default empty data
        data = {
            "invoice_number": "",
            "status": "",
            "date": "",
            "due_date": "",
            "paid_date": "",
            "supplier_info": {
                "name": "",
                "tax_id": "",
                "address": "",
                "email": "",
                "phone": ""
            },
            "customer_info": {
                "name": "",
                "tax_id": "",
                "address": "",
                "reference": "",
                "email": "",
                "phone": ""
            },
            "line_items": [],
            "subtotal": None,
            "tax_amount": None,
            "tax_rate": None,
            "total": None,
            "currency": "$",  # Default currency
            "invoice_type": "purchase"  # Default to purchase for expenditure invoices
        }
        
        # Extract invoice number - using a more flexible pattern
        invoice_number_patterns = [
            r'invoice\s*(?:#|no|number|num)[:\s]*([0-9a-zA-Z\-_/]+)',
            r'invoice[:\s]*([0-9a-zA-Z\-_/]+)',
            r'#\s*([0-9a-zA-Z\-_/]+)',
            r'\binvoice\b.*?([A-Z][0-9]+)',
            r'(?<!\S)([A-Z][0-9]{6,})(?!\S)'  # Pattern like U45844566
        ]
        
        for pattern in invoice_number_patterns:
            invoice_number_match = re.search(pattern, text, re.IGNORECASE)
            if invoice_number_match:
                data["invoice_number"] = invoice_number_match.group(1).strip()
                break
        
        # Extract invoice status
        status_match = re.search(r'status[:\s]*(\w+)', text, re.IGNORECASE)
        if status_match:
            data["status"] = status_match.group(1).strip().upper()
        
        # Extract date formats (DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD)
        date_patterns = [
            r'date[:\s]*([\d]{1,2}[-/\.][\d]{1,2}[-/\.][\d]{2,4})',
            r'date[:\s]*(\d{4}-\d{1,2}-\d{1,2})',
            r'date:\s*([\d]{1,2}/[\d]{1,2}/[\d]{4})'
        ]
        
        for pattern in date_patterns:
            date_match = re.search(pattern, text, re.IGNORECASE)
            if date_match:
                data["date"] = date_match.group(1).strip()
                break
        
        # Extract due date
        due_date_patterns = [
            r'due\s*date[:\s]*([\d]{1,2}[-/\.][\d]{1,2}[-/\.][\d]{2,4})',
            r'due\s*date[:\s]*(\d{4}-\d{1,2}-\d{1,2})',
            r'due\s*date:\s*([\d]{1,2}/[\d]{1,2}/[\d]{4})'
        ]
        
        for pattern in due_date_patterns:
            due_date_match = re.search(pattern, text, re.IGNORECASE)
            if due_date_match:
                data["due_date"] = due_date_match.group(1).strip()
                break
        
        # Extract paid date if available
        paid_date_patterns = [
            r'paid\s*date[:\s]*([\d]{1,2}[-/\.][\d]{1,2}[-/\.][\d]{2,4})',
            r'paid\s*date[:\s]*(\d{4}-\d{1,2}-\d{1,2})',
            r'paid\s*date:\s*([\d]{1,2}/[\d]{1,2}/[\d]{4})'
        ]
        
        for pattern in paid_date_patterns:
            paid_date_match = re.search(pattern, text, re.IGNORECASE)
            if paid_date_match:
                data["paid_date"] = paid_date_match.group(1).strip()
                break
        
        # Extract supplier name - first look for "From:" section
        from_section = re.search(r'from[:\s]*\n*([\s\S]*?)(?=\n\s*\n|\nto[:\s]*|\Z)', text, re.IGNORECASE)
        if from_section:
            supplier_text = from_section.group(1).strip()
            lines = supplier_text.split('\n')
            if lines:
                data["supplier_info"]["name"] = lines[0].strip()
                
                # Try to extract additional supplier info from subsequent lines
                for line in lines[1:]:
                    line = line.strip()
                    # Look for potential tax ID patterns
                    if re.match(r'^\d+$', line) or 'ice' in line.lower():
                        data["supplier_info"]["tax_id"] = line
        
        # Extract customer info - look for "To:" section
        to_section = re.search(r'to[:\s]*\n*([\s\S]*?)(?=\n\s*\n|\norder\s+lines|\Z)', text, re.IGNORECASE)
        if to_section:
            customer_text = to_section.group(1).strip()
            lines = customer_text.split('\n')
            if lines:
                data["customer_info"]["name"] = lines[0].strip()
                
                # Look for email in customer section
                email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', customer_text)
                if email_match:
                    data["customer_info"]["email"] = email_match.group(1).strip()
                
                # Try to extract phone number
                phone_match = re.search(r'tel[:\s]*([0-9\s\-\+]+)', customer_text, re.IGNORECASE)
                if phone_match:
                    data["customer_info"]["phone"] = phone_match.group(1).strip()
        
        # Extract order lines table
        line_items = []
        
        # Look for tabular data in various formats
        tables = re.findall(r'(?:description|item|product)\s+(?:quantity|qty)\s+(?:unit|uom)?\s+(?:price|rate)\s+(?:amount|total|sum).*?\n([\s\S]*?)(?=\n\s*\n|\nsubtotal|\ntotal|\Z)', text, re.IGNORECASE)
        
        if not tables:  # If no table headers found, try to find ORDER LINES section
            order_section = re.search(r'order\s+lines.*?\n([\s\S]*?)(?=\n\s*\n|\nsubtotal|\ntotal|\Z)', text, re.IGNORECASE)
            if order_section:
                tables = [order_section.group(1).strip()]
        
        for table_text in tables:
            lines = table_text.strip().split('\n')
            for line in lines:
                if not line.strip():
                    continue
                
                # Pattern to match: description, quantity, unit, price, amount
                # Example: "test 2 15 unit $30.00 $450.00"
                row_match = re.match(r'([^\d]+)\s+(\d+(?:\.\d+)?)\s+(\w+)\s+\$?(\d+\.\d+)\s+\$?(\d+\.\d+)', line)
                if row_match:
                    description = row_match.group(1).strip()
                    quantity = row_match.group(2).strip()
                    unit = row_match.group(3).strip()
                    price = row_match.group(4).strip()
                    amount = row_match.group(5).strip()
                    
                    try:
                        line_items.append({
                            "description": description,
                            "quantity": float(quantity),
                            "unit": unit,
                            "price": float(price),
                            "amount": float(amount)
                        })
                    except (ValueError, DecimalException, InvalidOperation):
                        # Skip if conversion fails
                        continue
                else:
                    # Try alternative pattern with just numbers and descriptions
                    # Look for quantity, price, and amount
                    qty_match = re.search(r'\b(\d+(?:\.\d+)?)\b', line)
                    price_match = re.search(r'\$?(\d+\.\d+)', line)
                    
                    if qty_match and price_match and line.count('$') >= 1:
                        try:
                            # Try to extract description, quantity, price
                            quantity = float(qty_match.group(1))
                            price_index = line.find(price_match.group(0))
                            description = line[:price_index].replace(qty_match.group(0), '', 1).strip()
                            price = float(price_match.group(1))
                            
                            # Check for second price which would be the amount
                            amount_match = re.search(r'\$?(\d+\.\d+)', line[price_index + len(price_match.group(0)):])
                            if amount_match:
                                amount = float(amount_match.group(1))
                            else:
                                amount = quantity * price
                            
                            line_items.append({
                                "description": description,
                                "quantity": quantity,
                                "unit": "unit",  # Default when not specified
                                "price": price,
                                "amount": amount
                            })
                        except (ValueError, DecimalException, InvalidOperation, AttributeError):
                            # Skip if extraction fails
                            continue
        
        data["line_items"] = line_items
        
        # Extract totals
        # Subtotal extraction
        subtotal_patterns = [
            r'subtotal[:\s]*\$?(\d+\.\d+)',
            r'sub[ -]?total[:\s]*\$?(\d+\.\d+)'
        ]
        
        for pattern in subtotal_patterns:
            subtotal_match = re.search(pattern, text, re.IGNORECASE)
            if subtotal_match:
                try:
                    data["subtotal"] = float(subtotal_match.group(1))
                    break
                except (ValueError, DecimalException, InvalidOperation):
                    pass
        
        # VAT/tax extraction with rate
        tax_patterns = [
            r'vat\s*(?:\((\d+)%\))?[:\s]*\$?(\d+\.\d+)',
            r'tax\s*(?:\((\d+)%\))?[:\s]*\$?(\d+\.\d+)'
        ]
        
        for pattern in tax_patterns:
            tax_match = re.search(pattern, text, re.IGNORECASE)
            if tax_match:
                try:
                    if tax_match.group(1):  # If tax rate is captured
                        data["tax_rate"] = float(tax_match.group(1))
                    data["tax_amount"] = float(tax_match.group(2))
                    break
                except (ValueError, DecimalException, InvalidOperation):
                    pass
        
        # Look for tax rate separately
        if data["tax_rate"] is None:
            tax_rate_match = re.search(r'(?:vat|tax)[:\s]*\((\d+)%\)', text, re.IGNORECASE)
            if tax_rate_match:
                try:
                    data["tax_rate"] = float(tax_rate_match.group(1))
                except (ValueError, DecimalException, InvalidOperation):
                    pass
        
        # Total extraction
        total_patterns = [
            r'total[:\s]*\$?(\d+\.\d+)',
            r'total amount[:\s]*\$?(\d+\.\d+)',
            r'amount due[:\s]*\$?(\d+\.\d+)'
        ]
        
        for pattern in total_patterns:
            total_match = re.search(pattern, text, re.IGNORECASE)
            if total_match:
                try:
                    data["total"] = float(total_match.group(1))
                    break
                except (ValueError, DecimalException, InvalidOperation):
                    pass
        
        # If we still don't have the subtotal but have line items, calculate it
        if data["subtotal"] is None and line_items:
            try:
                data["subtotal"] = sum(item["amount"] for item in line_items)
            except (KeyError, TypeError):
                pass
        
        # If we have subtotal and tax amount but no total, calculate it
        if data["total"] is None and data["subtotal"] is not None and data["tax_amount"] is not None:
            data["total"] = data["subtotal"] + data["tax_amount"]
        
        # If we have subtotal and tax rate but no tax amount, calculate it
        if data["tax_amount"] is None and data["subtotal"] is not None and data["tax_rate"] is not None:
            data["tax_amount"] = data["subtotal"] * (data["tax_rate"] / 100)
            
            # And if we don't have total, calculate it too
            if data["total"] is None:
                data["total"] = data["subtotal"] + data["tax_amount"]
        
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