"""
Example of using the invoice parser with the switcher functionality.
This file demonstrates how to parse invoices using either the regex-based parser
or the GPT parser based on the USE_GPT_INVOICE_PARSER environment variable.
"""

import os
import json
from .invoice_parser import InvoiceParser
from django.core.files.uploadedfile import InMemoryUploadedFile
import io

def parse_invoice_file(invoice_file):
    """
    Parse an invoice using either the regex-based parser or the GPT parser
    based on the USE_GPT_INVOICE_PARSER environment variable.
    
    Args:
        invoice_file: File object (or Django UploadedFile) containing the invoice
        
    Returns:
        dict: The parsed invoice data
    """
    # Use the switcher method which will automatically choose the correct parser
    return InvoiceParser.parse_invoice(invoice_file)


# Example usage:
if __name__ == "__main__":
    # This is just for demonstration purposes
    # In a real Django app, you'd get the file from a request
    
    # For local testing, you can open a file like this:
    file_path = "path/to/your/invoice/file.pdf"  # Update with your file path
    
    with open(file_path, "rb") as f:
        file_content = f.read()
    
    # Create a simple file-like object
    file_obj = io.BytesIO(file_content)
    
    # Create an UploadedFile object (similar to what Django would provide)
    uploaded_file = InMemoryUploadedFile(
        file=file_obj,
        field_name="invoice_file",
        name=os.path.basename(file_path),
        content_type="application/pdf",
        size=len(file_content),
        charset=None
    )
    
    # Parse the invoice
    try:
        parsed_data = parse_invoice_file(uploaded_file)
        print(json.dumps(parsed_data, indent=2, default=str))
    except Exception as e:
        print(f"Error parsing invoice: {e}")