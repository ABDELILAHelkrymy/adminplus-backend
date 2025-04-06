from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

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
    verify_url = f"{settings.FRONTEND_URL}/verify-email/{uid}/{token}"
    
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