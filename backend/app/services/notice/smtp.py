import smtplib
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from typing import Any, Dict, Optional, List
from app.core.config import settings

logger = logging.getLogger(__name__)

def send_email(
    email_to: str,
    subject: str = "",
    html_content: str = "",
    attachments: Optional[List[str]] = None
) -> None:
    """Send an email using SMTP with optional attachments."""
    
    # Check if SMTP is configured
    is_configured = all([
        settings.SMTP_HOST,
        settings.SMTP_USER,
        settings.SMTP_PASS,
        settings.EMAILS_FROM_EMAIL
    ])

    if not is_configured:
        msg = f"SMTP is not fully configured. Missing: {[k for k,v in {'HOST': settings.SMTP_HOST, 'USER': settings.SMTP_USER, 'PASS': settings.SMTP_PASS, 'FROM': settings.EMAILS_FROM_EMAIL}.items() if not v]}"
        logger.error(msg)
        raise ValueError(msg)

    message = MIMEMultipart("mixed") # Use mixed to support attachments
    message["Subject"] = subject
    message["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    message["To"] = email_to

    # Body part
    body_part = MIMEMultipart("alternative")
    part_html = MIMEText(html_content, "html")
    body_part.attach(part_html)
    message.attach(body_part)

    # Attachments
    if attachments:
        for file_path in attachments:
            if not os.path.exists(file_path):
                logger.warning(f"Attachment file not found: {file_path}")
                continue
            
            try:
                with open(file_path, "rb") as f:
                    file_data = f.read()
                    file_name = os.path.basename(file_path)
                    
                    # Determine subtype based on extension
                    ext = os.path.splitext(file_name)[1].lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.gif']:
                        attachment = MIMEImage(file_data, name=file_name)
                    else:
                        attachment = MIMEBase("application", "octet-stream")
                        attachment.set_payload(file_data)
                        encoders.encode_base64(attachment)
                    
                    attachment.add_header("Content-Disposition", f"attachment; filename={file_name}")
                    message.attach(attachment)
                    logger.info(f"Attached file: {file_name}")
            except Exception as e:
                logger.error(f"Failed to attach file {file_path}: {str(e)}")

    try:
        logger.info(f"Attempting to send email to {email_to} via {settings.SMTP_HOST}:{settings.SMTP_PORT}")
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.EMAILS_FROM_EMAIL, email_to, message.as_string())
        logger.info(f"Email successfully sent to {email_to}")
    except Exception as e:
        logger.error(f"SMTP dispatch failed: {str(e)}")
        raise e
