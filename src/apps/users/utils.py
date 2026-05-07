from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.conf import settings
import logging

# Set up loggers
email_logger = logging.getLogger('apps.email')

def send_password_reset_email(user):
    """
    Send a password reset email to the user.
    """
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    reset_link = f"{settings.FRONTEND_URL}/authentication/reset-password/{uid}/{token}/"
    
    email_logger.info(f"Sending password reset email to {user.email}", extra={
        'to': user.email,
        'from': settings.EMAIL_HOST_USER,
        'link': reset_link
    })
    
    subject = "Reset your password"
    message = f"""
    Hello {user.first_name},
    
    You requested a password reset for your account. Please click the link below to reset your password:
    
    {reset_link}
    
    If you did not request this password reset, please ignore this email.
    
    Best regards,
    The AdminPlus Accounting Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
        email_logger.info(f"Password reset email sent successfully to {user.email}", extra={
            'to': user.email,
            'from': settings.EMAIL_HOST_USER
        })
        return True
    except Exception as e:
        email_logger.error(f"Failed to send password reset email to {user.email}: {str(e)}", extra={
            'to': user.email,
            'from': settings.EMAIL_HOST_USER,
            'error': str(e)
        })
        return False


def send_verification_email(user):
    """
    Send an email verification link to the user.
    Uses direct SMTP connection with timeout handling.
    """
    import smtplib
    import socket
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    verification_link = f"{settings.FRONTEND_URL}/authentication/email-verification/{uid}/{token}/"
    
    # Log email information
    email_logger.info(f"Preparing verification email for {user.email}", extra={
        'to': user.email,
        'from': settings.EMAIL_HOST_USER,
        'link': verification_link
    })
    
    from_email = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER

    try:
        # Set up the email
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = user.email
        msg['Subject'] = "Verify your email address"
        
        # Create message body
        body = f"""
Hello {user.first_name},

Thank you for registering with AdminPlus Accounting. Please click the link below to verify your email address:

{verification_link}

If you did not register for an account, please ignore this email.

Best regards,
The AdminPlus Accounting Team
        """
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to the SMTP server with timeout
        email_logger.debug(f"Connecting to SMTP server: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}", extra={
            'to': user.email,
            'from': from_email,
            'host': settings.EMAIL_HOST,
            'port': settings.EMAIL_PORT
        })
        
        # Use SMTP_SSL for port 465 (Resend), plain SMTP + STARTTLS for port 587 (Gmail)
        if settings.EMAIL_USE_SSL:
            server = smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=30)
        else:
            server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=30)
            if settings.EMAIL_USE_TLS:
                email_logger.debug("Starting TLS encryption", extra={
                    'to': user.email,
                    'from': from_email
                })
                server.starttls()
        
        server.set_debuglevel(0)  # Disable debugging output
        
        # Login with credentials
        email_logger.debug(f"Logging in with username: {settings.EMAIL_HOST_USER}", extra={
            'to': user.email,
            'from': from_email
        })
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        
        # Send the email
        email_logger.debug("Sending email", extra={
            'to': user.email,
            'from': from_email
        })
        server.send_message(msg)
        
        # Close the connection
        server.quit()
        
        email_logger.info(f"Verification email sent successfully to {user.email}", extra={
            'to': user.email,
            'from': from_email
        })
        return True
        
    except (smtplib.SMTPException, socket.timeout, socket.error) as e:
        email_logger.error(f"SMTP/Network error sending verification email: {str(e)}", extra={
            'to': user.email,
            'from': settings.EMAIL_HOST_USER,
            'error': str(e)
        })
        
        # Try fallback to Django's send_mail with timeout
        email_logger.info("Attempting fallback to Django's send_mail", extra={
            'to': user.email,
            'from': settings.EMAIL_HOST_USER
        })
        try:
            subject = "Verify your email address"
            message = f"""
Hello {user.first_name},

Thank you for registering with AdminPlus Accounting. Please click the link below to verify your email address:

{verification_link}

If you did not register for an account, please ignore this email.

Best regards,
The AdminPlus Accounting Team
            """
            
            send_mail(
                subject,
                message,
                from_email,
                [user.email],
                fail_silently=False,
            )
            email_logger.info(f"Verification email sent via Django's send_mail to {user.email}", extra={
                'to': user.email,
                'from': settings.EMAIL_HOST_USER
            })
            return True
        except Exception as fallback_error:
            email_logger.error(f"Fallback error with Django's send_mail: {str(fallback_error)}", extra={
                'to': user.email,
                'from': settings.EMAIL_HOST_USER,
                'error': str(fallback_error)
            })
            return False
    except Exception as e:
        email_logger.error(f"Unexpected error sending verification email: {str(e)}", extra={
            'to': user.email,
            'from': settings.EMAIL_HOST_USER,
            'error': str(e)
        })
        return False


def send_otp_via_sms(phone_number, otp):
    """
    Send OTP via SMS using a third-party service.
    
    This is a placeholder function that would be implemented with an actual
    SMS provider like Twilio, Vonage, etc.
    
    Returns True if SMS was sent successfully, False otherwise.
    """
    logger = logging.getLogger('apps.sms')
    try:
        # In a real implementation, this would call the SMS provider's API
        
        # Log the OTP for debugging
        logger.info(f"Sending OTP {otp} to {phone_number}")
        
        # Pretend it was sent successfully
        return True
    except Exception as e:
        logger.error(f"Error sending SMS to {phone_number}: {str(e)}")
        return False 