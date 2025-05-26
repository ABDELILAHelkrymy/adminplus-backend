from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.files.storage import default_storage
import logging
import os
import boto3
import requests

logger = logging.getLogger(__name__)

def send_invoice_email(invoice, recipient_email, subject, content, from_email=None, attachments=None, attach_pdf=True):
    """
    Send an email for an invoice with optional PDF attachment.
    
    Args:
        invoice: The Invoice model instance
        recipient_email: Email address of the recipient
        subject: Email subject
        content: HTML content of the email
        from_email: Sender email (defaults to settings.DEFAULT_FROM_EMAIL)
        attachments: List of attachments (file paths or file objects)
        attach_pdf: Whether to attempt to attach the PDF (defaults to True)
    
    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    try:
        # Ensure attach_pdf is a boolean
        if isinstance(attach_pdf, str):
            attach_pdf = attach_pdf.lower() in ('true', 't', 'yes', 'y', '1')
        else:
            attach_pdf = bool(attach_pdf)
            
        logger.info(f"Sending invoice email to {recipient_email} with attach_pdf={attach_pdf}")
        
        # Use default sender email from settings if not provided
        if not from_email:
            from_email = settings.DEFAULT_FROM_EMAIL
            
        # Create email message
        email = EmailMessage(
            subject=subject,
            body=content,
            from_email=from_email,
            to=[recipient_email]
        )
        
        # Set email content type to HTML
        email.content_subtype = "html"
        
        # Add the generated PDF invoice if available and attachment is requested
        pdf_attached = False
        if attach_pdf and invoice.generated_pdf:
            logger.info(f"PDF attachment requested for invoice {invoice.invoice_number}")
            pdf_content = None
            pdf_filename = f'invoice_{invoice.invoice_number}.pdf'
            
            try:
                # Check if we're using S3 storage first (most likely scenario for this deployment)
                if hasattr(settings, 'AWS_STORAGE_BUCKET_NAME') and settings.AWS_STORAGE_BUCKET_NAME:
                    logger.info("Detected S3 storage configuration, trying S3 methods first")
                    
                    # Method 1: Try direct S3 access
                    try:
                        s3_client = boto3.client(
                            's3',
                            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                            region_name=settings.AWS_S3_REGION_NAME
                        )
                        
                        # Clean up the key to avoid absolute path issues
                        s3_key = invoice.generated_pdf.name
                        if s3_key.startswith('/'):
                            s3_key = s3_key[1:]
                        
                        # Get the file directly from S3
                        logger.info(f"Trying direct S3 access for bucket: {settings.AWS_STORAGE_BUCKET_NAME}, key: {s3_key}")
                        response = s3_client.get_object(
                            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                            Key=s3_key
                        )
                        pdf_content = response['Body'].read()
                        logger.info(f"Successfully read PDF content using direct S3 access, size: {len(pdf_content)} bytes")
                    except Exception as s3_error:
                        logger.warning(f"Direct S3 access failed: {str(s3_error)}")
                    
                    # Method 2: Try to download from the signed URL if S3 direct access failed
                    if pdf_content is None and hasattr(invoice.generated_pdf, 'url'):
                        try:
                            pdf_url = invoice.generated_pdf.url
                            logger.info(f"Attempting to download PDF from S3 URL: {pdf_url}")
                            
                            # Use requests with proper headers for S3
                            response = requests.get(pdf_url, timeout=30)
                            if response.status_code == 200:
                                pdf_content = response.content
                                logger.info(f"Successfully downloaded PDF from S3 URL, size: {len(pdf_content)} bytes")
                            else:
                                logger.warning(f"Failed to download PDF from S3 URL, status code: {response.status_code}")
                        except Exception as url_error:
                            logger.warning(f"Failed to download PDF from S3 URL: {str(url_error)}")
                
                else:
                    # Local storage methods (fallback for non-S3 deployments)
                    logger.info("Using local storage methods")
                    
                    # Method 1: Try direct file access (for local storage)
                    if hasattr(invoice.generated_pdf, 'path'):
                        try:
                            file_path = invoice.generated_pdf.path
                            if os.path.exists(file_path):
                                with open(file_path, 'rb') as f:
                                    pdf_content = f.read()
                                logger.info(f"Successfully read PDF content from file path: {file_path}")
                            else:
                                logger.warning(f"PDF file path exists but file not found: {file_path}")
                        except Exception as file_error:
                            logger.warning(f"Failed to read PDF file directly: {str(file_error)}")
                    
                    # Method 2: Try through Django storage
                    if pdf_content is None and hasattr(invoice.generated_pdf, 'name'):
                        try:
                            # Get the file name without any leading slashes to avoid absolute path issues
                            pdf_path = invoice.generated_pdf.name
                            if pdf_path.startswith('/'):
                                pdf_path = pdf_path[1:]
                                
                            logger.info(f"Attempting to open file with default_storage: {pdf_path}")
                            
                            if default_storage.exists(pdf_path):
                                with default_storage.open(pdf_path, 'rb') as f:
                                    pdf_content = f.read()
                                logger.info(f"Successfully read PDF content using default_storage: {pdf_path}")
                            else:
                                logger.warning(f"PDF file not found in storage: {pdf_path}")
                        except Exception as storage_error:
                            logger.warning(f"Failed to read PDF using default_storage: {str(storage_error)}")
                    
                    # Method 3: Try to get the file through a public URL if available
                    if pdf_content is None and hasattr(invoice.generated_pdf, 'url'):
                        try:
                            pdf_url = invoice.generated_pdf.url
                            # If the URL is relative, prepend the base URL
                            if pdf_url.startswith('/'):
                                if hasattr(settings, 'SITE_URL'):
                                    base_url = f"{settings.SITE_URL.rstrip('/')}"
                                    pdf_url = f"{base_url}{pdf_url}"
                                else:
                                    logger.warning("PDF URL is relative but SITE_URL not configured")
                                    pdf_url = None
                            
                            if pdf_url:
                                logger.info(f"Attempting to download PDF from URL: {pdf_url}")
                                response = requests.get(pdf_url, timeout=30)
                                if response.status_code == 200:
                                    pdf_content = response.content
                                    logger.info(f"Successfully downloaded PDF from URL, size: {len(pdf_content)} bytes")
                                else:
                                    logger.warning(f"Failed to download PDF from URL, status code: {response.status_code}")
                        except Exception as url_error:
                            logger.warning(f"Failed to download PDF from URL: {str(url_error)}")
                
                # If we got the content, attach it
                if pdf_content and len(pdf_content) > 0:
                    # Use the original filename if available
                    if hasattr(invoice.generated_pdf, 'name') and invoice.generated_pdf.name:
                        original_filename = os.path.basename(invoice.generated_pdf.name)
                        if original_filename and original_filename.lower().endswith('.pdf'):
                            pdf_filename = original_filename
                    
                    logger.info(f"Attaching PDF with filename: {pdf_filename} and size: {len(pdf_content)} bytes")
                    email.attach(pdf_filename, pdf_content, 'application/pdf')
                    pdf_attached = True
                else:
                    logger.error("Could not get PDF content from any method or content is empty")
                    
            except Exception as e:
                logger.error(f"Could not attach generated PDF: {str(e)}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
                # Log diagnostic information
                if hasattr(invoice.generated_pdf, 'name'):
                    logger.error(f"PDF field name: {invoice.generated_pdf.name}")
                if hasattr(invoice.generated_pdf, 'url'):
                    logger.error(f"PDF field URL: {invoice.generated_pdf.url}")
        
        # Log attachment status
        if attach_pdf and not pdf_attached:
            if not invoice.generated_pdf:
                logger.warning(f"No PDF was attached - invoice.generated_pdf is None/empty for invoice {invoice.invoice_number}")
            else:
                logger.error(f"No PDF was attached despite file existing for invoice {invoice.invoice_number}")
        
        # Add the original invoice document if available
        if hasattr(invoice, 'original_document') and invoice.original_document:
            try:
                original_content = None
                original_filename = f'original_{invoice.invoice_number}'
                
                # Try to get the original document content
                if hasattr(invoice.original_document, 'path') and os.path.exists(invoice.original_document.path):
                    with open(invoice.original_document.path, 'rb') as f:
                        original_content = f.read()
                    original_filename = os.path.basename(invoice.original_document.path)
                elif hasattr(invoice.original_document, 'name'):
                    # For cloud storage
                    doc_path = invoice.original_document.name
                    if doc_path.startswith('/'):
                        doc_path = doc_path[1:]
                    
                    if default_storage.exists(doc_path):
                        with default_storage.open(doc_path, 'rb') as f:
                            original_content = f.read()
                        original_filename = os.path.basename(doc_path)
                
                if original_content:
                    # Determine content type based on file extension
                    content_type = 'application/pdf'  # Default to PDF
                    if original_filename.lower().endswith(('.jpg', '.jpeg')):
                        content_type = 'image/jpeg'
                    elif original_filename.lower().endswith('.png'):
                        content_type = 'image/png'
                    
                    email.attach(original_filename, original_content, content_type)
                    logger.info(f"Attached original document: {original_filename}")
                        
            except Exception as e:
                logger.warning(f"Could not attach original document: {str(e)}")
        
        # Add any additional attachments
        if attachments:
            for attachment in attachments:
                try:
                    if isinstance(attachment, str) and os.path.exists(attachment):
                        email.attach_file(attachment)
                        logger.info(f"Attached file: {attachment}")
                    else:
                        # Assuming this is a File object with name and content
                        attachment_content = attachment.read()
                        email.attach(attachment.name, attachment_content)
                        logger.info(f"Attached uploaded file: {attachment.name}")
                except Exception as attach_error:
                    logger.warning(f"Failed to attach file: {str(attach_error)}")
        
        # Send the email
        email.send()
        
        # Log success
        logger.info(f"Invoice email sent successfully to {recipient_email} for invoice {invoice.invoice_number}")
        return True
        
    except Exception as e:
        # Log error with full traceback
        import traceback
        logger.error(f"Failed to send invoice email: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False

def generate_invoice_email_content(invoice, template_name=None, context=None):
    """
    Generate HTML content for invoice email
    
    Args:
        invoice: The Invoice model instance
        template_name: Optional custom template name
        context: Additional context for the template
    
    Returns:
        str: HTML content for the email
    """
    # Log what we're working with
    logger.info(f"Generating email content for invoice: {invoice.invoice_number}")
    
    # Debug business account data
    if hasattr(invoice, 'business_account'):
        logger.info(f"Business account: {invoice.business_account.business_name}")
        logger.info(f"Business address: {invoice.business_account.business_address}")
        logger.info(f"Business email: {invoice.business_account.email}")
    else:
        logger.error("Invoice does not have business_account attribute")
    
    # Default context with safe attribute access
    default_context = {
        'invoice': invoice,
        'business_name': getattr(invoice.business_account, 'business_name', '') if hasattr(invoice, 'business_account') else '',
        'business_address': getattr(invoice.business_account, 'business_address', '') if hasattr(invoice, 'business_account') else '',
        'business_phone': getattr(invoice.business_account, 'phone_number', '') if hasattr(invoice, 'business_account') else '',
        'business_email': getattr(invoice.business_account, 'email', '') if hasattr(invoice, 'business_account') else '',
        'invoice_number': invoice.invoice_number,
        'invoice_date': invoice.date,
        'invoice_due_date': invoice.due_date,
        'invoice_total': invoice.total,
        'invoice_currency': invoice.currency,
        'recipient': invoice.customer.corporate_name if invoice.customer else '',
        'payment_reference': invoice.reference or '',
        'bank_account_number': invoice.supplier_iban or '',
    }
    
    # Log context keys for debugging
    logger.info(f"Email template context keys: {default_context.keys()}")
    logger.info(f"Business address in context: {default_context['business_address']}")
    logger.info(f"Business email in context: {default_context['business_email']}")
    
    # Merge with additional context if provided
    if context:
        default_context.update(context)
    
    # Use default template if none specified
    if not template_name:
        template_name = 'invoices/email/invoice_email.html'
    
    # Log the template path being used
    logger.info(f"Attempting to load email template: {template_name}")
    
    # Render the template
    try:
        html_content = render_to_string(template_name, default_context)
        logger.info("Email template rendered successfully")
        return html_content
    except Exception as e:
        logger.error(f"Failed to generate invoice email content: {str(e)}")
        # Fallback to basic content
        return f"""
        <html>
        <body>
            <h2>Invoice {invoice.invoice_number}</h2>
            <p>Dear {invoice.customer.corporate_name if invoice.customer else 'Customer'},</p>
            <p>Please find attached invoice {invoice.invoice_number} dated {invoice.date}.</p>
            <p>Total amount: {invoice.currency} {invoice.total}</p>
            <p>Due date: {invoice.due_date if invoice.due_date else 'Not specified'}</p>
            <p>Thank you for your business!</p>
            <p>{invoice.business_account.business_name if hasattr(invoice.business_account, 'business_name') else ''}</p>
        </body>
        </html>
        """