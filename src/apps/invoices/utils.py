from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
import logging
import os
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

def send_invoice_email(invoice, recipient_email, subject, content, from_email=None, attachments=None):
    """
    Send an email for an invoice with optional PDF attachment.
    
    Args:
        invoice: The Invoice model instance
        recipient_email: Email address of the recipient
        subject: Email subject
        content: HTML content of the email
        from_email: Sender email (defaults to settings.DEFAULT_FROM_EMAIL)
        attachments: List of attachments (file paths or file objects)
    
    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    try:
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
        
        # Add the generated PDF invoice if available
        if invoice.generated_pdf and os.path.exists(invoice.generated_pdf.path):
            email.attach_file(invoice.generated_pdf.path)
        
        # Add the original invoice document if available
        if invoice.original_document and os.path.exists(invoice.original_document.path):
            email.attach_file(invoice.original_document.path)
        
        # Add any additional attachments
        if attachments:
            for attachment in attachments:
                if isinstance(attachment, str) and os.path.exists(attachment):
                    email.attach_file(attachment)
                else:
                    # Assuming this is a File object with name and content
                    email.attach(attachment.name, attachment.read())
        
        # Send the email
        email.send()
        
        # Log success
        logger.info(f"Invoice email sent to {recipient_email} for invoice {invoice.invoice_number}")
        return True
        
    except Exception as e:
        # Log error
        logger.error(f"Failed to send invoice email: {str(e)}")
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