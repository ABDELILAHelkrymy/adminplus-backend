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
    reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}"
    
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