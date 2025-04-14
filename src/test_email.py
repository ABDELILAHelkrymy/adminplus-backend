#!/usr/bin/env python
"""
Script to test email sending from the command line.

Usage: python test_email.py
"""

import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from decouple import config

def test_smtp_connection():
    """Test direct SMTP connection without Django."""
    print("Testing SMTP connection...")
    
    # Get configuration from environment
    host = config('EMAIL_HOST', default='smtp.gmail.com')
    port = config('EMAIL_PORT', default=587, cast=int)
    username = config('EMAIL_HOST_USER', default='')
    password = config('EMAIL_HOST_PASSWORD', default='')
    use_tls = config('EMAIL_USE_TLS', default=True, cast=bool)
    
    # Show configuration (hide password)
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")
    print(f"Use TLS: {use_tls}")
    
    # Test connection
    try:
        print("\nEstablishing connection...")
        server = smtplib.SMTP(host, port)
        server.set_debuglevel(1)  # Enable debug output
        
        print("Starting TLS...")
        server.starttls()
        
        print("Logging in...")
        server.login(username, password)
        
        print("Login successful!")
        
        # Send a test email
        sender = username
        recipient = username  # Send to yourself for testing
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = 'AdminPlus Test Email'
        
        body = 'This is a test email sent from the AdminPlus application.'
        msg.attach(MIMEText(body, 'plain'))
        
        print(f"Sending email from {sender} to {recipient}...")
        server.sendmail(sender, recipient, msg.as_string())
        print("Email sent successfully!")
        
        # Close connection
        server.quit()
        print("Connection closed.")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    if test_smtp_connection():
        print("\nEmail test successful! Check your inbox.")
        sys.exit(0)
    else:
        print("\nEmail test failed. See error message above.")
        sys.exit(1) 