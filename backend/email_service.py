"""Minimal email service for update verification codes.

Uses SMTP if configured, otherwise prints the code to the console.
"""

import os
import smtplib
from email.message import EmailMessage


SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "noreply@researchtwin.net")


def send_update_code(to_email: str, slug: str, code: str) -> bool:
    """Send the 6-digit update code. Returns True on success."""
    subject = f"ResearchTwin update code for {slug}"
    body = (
        f"Your verification code for updating your ResearchTwin profile ({slug}) is:\n\n"
        f"    {code}\n\n"
        f"This code expires in 1 hour. If you did not request this, ignore this email."
    )

    if not SMTP_HOST:
        print(f"[email_service] SMTP not configured. Code for {slug} ({to_email}): {code}")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            if SMTP_USER:
                server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[email_service] Failed to send to {to_email}: {e}")
        return False
