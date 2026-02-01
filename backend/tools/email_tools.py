"""
Zero Me - Email Tools
Tools for sending and managing emails using Resend API
No OAuth required - just an API key
"""

import os
from typing import Optional, List
from langchain.tools import tool
from loguru import logger

# Import colorful logging
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from logging_utils import log_tool_call, log_tool_result

try:
    import resend
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False
    logger.warning("resend not installed. Email tools will be disabled.")


def init_resend():
    """Initialize Resend with API key."""
    if not RESEND_AVAILABLE:
        return False
    
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        logger.warning("RESEND_API_KEY not found")
        return False
    
    resend.api_key = api_key
    return True


@tool
def send_email(
    to: str,
    subject: str,
    body: str,
    from_email: Optional[str] = None,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
) -> str:
    """
    Send an email using Resend.
    
    Args:
        to: Recipient email address (can be comma-separated for multiple)
        subject: Email subject line
        body: Email body content (plain text)
        from_email: Sender email (optional, uses default if not provided)
        cc: CC recipients (comma-separated)
        bcc: BCC recipients (comma-separated)
    
    Returns:
        Success message with email ID or error message
    """
    log_tool_call("send_email", {"to": to, "subject": subject})
    
    if not init_resend():
        result = "Error: Email service is not configured. Please set RESEND_API_KEY."
        log_tool_result("send_email", result, success=False)
        return result
    
    try:
        # Parse recipients
        to_list = [email.strip() for email in to.split(",")]
        
        # Default from email (you'll need a verified domain on Resend)
        sender = from_email or os.getenv("RESEND_FROM_EMAIL", "Zero Me <onboarding@resend.dev>")
        
        params = {
            "from": sender,
            "to": to_list,
            "subject": subject,
            "text": body,
        }
        
        if cc:
            params["cc"] = [email.strip() for email in cc.split(",")]
        if bcc:
            params["bcc"] = [email.strip() for email in bcc.split(",")]
        
        # Send the email
        response = resend.Emails.send(params)
        
        email_id = response.get("id", "unknown")
        
        result = f"Successfully sent email to {to}. Subject: '{subject}'. Email ID: {email_id}"
        log_tool_result("send_email", result, success=True)
        return result
        
    except Exception as e:
        result = f"Error sending email: {str(e)}"
        log_tool_result("send_email", result, success=False)
        return result


@tool
def draft_email(
    to: str,
    subject: str,
    body: str,
    from_email: Optional[str] = None,
) -> str:
    """
    Draft an email for review (does not send).
    
    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body content
        from_email: Sender email (optional)
    
    Returns:
        Formatted draft email for review
    """
    log_tool_call("draft_email", {"to": to, "subject": subject})
    
    sender = from_email or os.getenv("RESEND_FROM_EMAIL", "Zero Me <onboarding@resend.dev>")
    
    draft = f"""
=== EMAIL DRAFT ===
From: {sender}
To: {to}
Subject: {subject}

{body}
===================

This is a draft. Say "send it" to send, or ask me to modify it.
"""
    
    log_tool_result("draft_email", f"Draft created for {to}", success=True)
    return draft


# Note: Resend is a send-only service. To read emails, you would need:
# - IMAP integration (complex)
# - Gmail API (requires OAuth)
# - Nylas API (paid but easy)
# 
# For now, we focus on sending. Reading can be added later with a different service.

@tool
def check_email_status(email_id: str) -> str:
    """
    Check the delivery status of a sent email.
    
    Args:
        email_id: The email ID returned when sending
    
    Returns:
        Email status information
    """
    log_tool_call("check_email_status", {"email_id": email_id})
    
    if not init_resend():
        result = "Error: Email service is not configured. Please set RESEND_API_KEY."
        log_tool_result("check_email_status", result, success=False)
        return result
    
    try:
        email = resend.Emails.get(email_id)
        
        result = f"""
Email Status:
- ID: {email.get('id')}
- To: {email.get('to')}
- Subject: {email.get('subject')}
- Status: {email.get('last_event', 'unknown')}
- Created: {email.get('created_at')}
"""
        log_tool_result("check_email_status", f"Status: {email.get('last_event', 'unknown')}", success=True)
        return result
        
    except Exception as e:
        result = f"Error checking email status: {str(e)}"
        log_tool_result("check_email_status", result, success=False)
        return result
