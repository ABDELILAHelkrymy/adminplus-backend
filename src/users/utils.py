from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from twilio.rest import Client

def send_password_reset_email(user):
    """Send password reset email with reset link"""
    # Generate token and encode user ID
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # Create reset URL
    reset_url = f"{settings.FRONTEND_URL}/authentication/reset-password/reset-password-confirm/{uid}/{token}"
    
    # Email content
    subject = 'Reset Your Password'
    message = f"""
    Hello {user.first_name},
    
    You requested to reset your password. Click the link below to set a new password:
    
    {reset_url}
    
    If you didn't request this, please ignore this email.
    
    This link will expire in 24 hours.
    
    Best regards,
    Your Application Team
    """
    
    # Send email
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

    return token

def send_verification_email(user):
    """
    Send email verification link to user
    """
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # Create verification URL
    verify_url = f"{settings.FRONTEND_URL}/authentication/email-verification/EmailVerification/{uid}/{token}"
    
    # Email content
    subject = 'Verify Your Email Address'
    message = f"""
    Hello {user.first_name},
    
    Thank you for registering with us. Please verify your email address by clicking the link below:
    
    {verify_url}
    
    This link will expire in 24 hours.
    
    If you didn't register on our platform, please ignore this email.
    
    Best regards,
    The Compta-Go Team
    """
    
    # Send email
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

def send_otp_via_sms(phone_number, otp):
    """
    Send OTP via SMS using Twilio
    """
    try:
        # Initialize Twilio client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        # Format message
        message_body = f"Your ComptaGo verification code is: {otp}. This code will expire in 10 minutes."
        
        # Send SMS
        message = client.messages.create(
            body=message_body,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        
        # Return message SID on success
        return {
            'success': True,
            'message_sid': message.sid
        }
    except Exception as e:
        # Return error details
        return {
            'success': False,
            'error': str(e)
        }