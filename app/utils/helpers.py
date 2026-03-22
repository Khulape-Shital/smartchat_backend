from fastapi import HTTPException
from app.core.config import settings
import smtplib
import logging
from email.mime.text import MIMEText


def send_email(to_email: str, link: str, email_type: str = "password_reset"):
    """
    Send email using SMTP credentials from environment variables.
    
    Args:
        to_email: Recipient email address
        link: Link to include in email (verification or reset link)
        email_type: Type of email - "verification" or "password_reset" (default)
    """
    sender_email = settings.SMTP_EMAIL
    app_password = settings.SMTP_PASSWORD
    
    logger = logging.getLogger(__name__)

    if not sender_email or not app_password:
        logger.error(f"SMTP config missing - Email: {bool(sender_email)}, Password: {bool(app_password)}")
        raise HTTPException(
            status_code=500,
            detail="Email service not configured. Please set SMTP_EMAIL and SMTP_PASSWORD in .env"
        )
    
    logger.info(f"Attempting SMTP login with email: {sender_email}")

    # Customize email content based on type
    if email_type == "verification":
        subject = "Verify Your Email"
        body = f"Welcome! Please verify your email by clicking this link:\n{link}"
    else:  # password_reset
        subject = "Password Reset"
        body = f"Click to reset password:\n{link}"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email

    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        logger = logging.getLogger(__name__)
        logger.error(f"SMTP Authentication failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Email service authentication failed. Check SMTP_EMAIL and SMTP_PASSWORD in .env"
        )
    except smtplib.SMTPException as e:
        logger = logging.getLogger(__name__)
        logger.error(f"SMTP error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Email service error. Please try again later."
        )



