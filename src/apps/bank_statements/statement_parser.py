import re
import csv
import logging
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, List
import tempfile
import os

logger = logging.getLogger(__name__)


class StatementParser:
    """
    Unified parser for bank statements that can handle different file types
    and switch between traditional and GPT-based parsing
    """

    @staticmethod
    def parse_statement(file, use_gpt=True):
        """
        Main entry point for parsing bank statements
        
        Args:
            file: Uploaded file object
            use_gpt: Whether to use GPT parser (default: True)
            
        Returns:
            dict: Parsed statement data
        """
        try:
            # Determine file type
            file_name = file.name.lower()
            if file_name.endswith('.pdf'):
                file_type = 'pdf'
            elif file_name.endswith(('.jpg', '.jpeg', '.png')):
                file_type = 'image'
            elif file_name.endswith('.csv'):
                file_type = 'csv'
            elif file_name.endswith(('.xls', '.xlsx')):
                file_type = 'excel'
            else:
                raise ValueError(f"Unsupported file type: {file_name}")
            
            # Extract text from file
            text_content = StatementParser._extract_text_from_file(file, file_type)
            
            # Use GPT parser if requested and available
            if use_gpt:
                try:
                    from .gpt_statement_parser import GPTStatementParser
                    parser = GPTStatementParser()
                    result = parser.extract_statement_data(text_content)
                    return result
                except ImportError as e:
                    logger.warning(f"GPT parser not available: {e}, falling back to traditional parser")
                except Exception as e:
                    logger.warning(f"GPT parsing failed: {str(e)}, falling back to traditional parser")
            
            # Fall back to traditional parser
            return StatementParser._traditional_parse(text_content, file_type)
            
        except Exception as e:
            logger.error(f"Error parsing statement: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    @staticmethod
    def _extract_text_from_file(file, file_type):
        """Extract text from various file types"""
        if file_type == 'pdf':
            return StatementParser._extract_from_pdf(file)
        elif file_type == 'image':
            return StatementParser._extract_from_image(file)
        elif file_type == 'csv':
            return StatementParser._extract_from_csv(file)
        elif file_type == 'excel':
            return StatementParser._extract_from_excel(file)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    @staticmethod
    def _extract_from_pdf(file):
        """Extract text from PDF"""
        try:
            import PyPDF2
            text = ""
            
            # Save uploaded file to temp location
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                for chunk in file.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name
            
            try:
                with open(temp_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
            finally:
                os.unlink(temp_path)
            
            # If text extraction failed, try OCR
            if not text.strip():
                logger.info("PDF text extraction failed, trying OCR")
                return StatementParser._ocr_extract(file)
            
            return text
        except Exception as e:
            logger.warning(f"PDF text extraction failed: {str(e)}, trying OCR")
            return StatementParser._ocr_extract(file)

    @staticmethod
    def _extract_from_image(file):
        """Extract text from image using OCR"""
        return StatementParser._ocr_extract(file)

    @staticmethod
    def _ocr_extract(file):
        """OCR extraction using pytesseract - only used as fallback"""
        try:
            import pytesseract
            from PIL import Image
            from pdf2image import convert_from_bytes
            
            # Save uploaded file to temp location
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                for chunk in file.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name
            
            try:
                # Check if it's a PDF or image
                if file.name.lower().endswith('.pdf'):
                    # Convert PDF to images
                    images = convert_from_bytes(open(temp_path, 'rb').read())
                    text = ""
                    for image in images:
                        text += pytesseract.image_to_string(image) + "\n"
                else:
                    # Process image directly
                    image = Image.open(temp_path)
                    text = pytesseract.image_to_string(image)
                
                return text
            finally:
                os.unlink(temp_path)
                
        except ImportError as e:
            logger.error("Required OCR libraries not installed")
            raise ValueError(
                "Poppler and Tesseract are required for processing image files and scanned PDFs. "
                "However, most PDFs with text can be processed without these dependencies."
            )
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            # Return empty string instead of raising - GPT might still work with PDF text
            return ""

    @staticmethod
    def _extract_from_csv(file):
        """Extract and format CSV data"""
        text = ""
        try:
            # Decode the file content
            content = file.read().decode('utf-8')
            file.seek(0)  # Reset file pointer
            
            csv_reader = csv.reader(content.splitlines())
            for row in csv_reader:
                text += ", ".join(row) + "\n"
            return text
        except Exception as e:
            logger.error(f"CSV extraction failed: {str(e)}")
            raise

    @staticmethod
    def _extract_from_excel(file):
        """Extract data from Excel file"""
        try:
            import openpyxl
            
            # Save uploaded file to temp location
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
                for chunk in file.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name
            
            try:
                workbook = openpyxl.load_workbook(temp_path)
                sheet = workbook.active
                
                text = ""
                for row in sheet.iter_rows(values_only=True):
                    text += ", ".join(str(cell) if cell is not None else "" for cell in row) + "\n"
                
                return text
            finally:
                os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"Excel extraction failed: {str(e)}")
            raise

    @staticmethod
    def _traditional_parse(text: str, file_type: str) -> Dict[str, Any]:
        """
        Traditional rule-based parsing (fallback method)
        Returns basic structure - GPT is preferred
        """
        # This is a simple fallback - implement specific bank format parsers as needed
        return {
            "statement": {
                "account_holder": None,
                "account_number": None,
                "branch": None,
                "period_start": None,
                "period_end": None,
                "opening_balance": None,
                "closing_balance": None,
                "transactions": []
            },
            "parser": "traditional",
            "note": "Traditional parser returned minimal data. Use GPT parser for better results."
        }

    @staticmethod
    def check_dependencies():
        """Check if required dependencies are installed"""
        tesseract_installed = False
        poppler_installed = False
        
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            tesseract_installed = True
        except:
            pass
        
        try:
            from pdf2image import convert_from_bytes
            # Try a minimal test
            test_pdf = b"%PDF-1.0\n%%EOF"
            convert_from_bytes(test_pdf, size=1)
            poppler_installed = True
        except:
            pass
        
        return tesseract_installed, poppler_installed

    @staticmethod
    def get_dependency_installation_instructions():
        """Get installation instructions for missing dependencies"""
        return {
            "tesseract": {
                "windows": "Download from https://github.com/UB-Mannheim/tesseract/wiki and add to PATH",
                "mac": "brew install tesseract",
                "linux": "sudo apt-get install tesseract-ocr"
            },
            "poppler": {
                "windows": "Download from https://github.com/oschwartz10612/poppler-windows/releases/ and add bin/ to PATH",
                "mac": "brew install poppler",
                "linux": "sudo apt-get install poppler-utils"
            }
        }
