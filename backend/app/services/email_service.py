"""Email delivery with pluggable backends.

- ``console`` (default): logs the message — perfect for local/dev so flows like
  password reset are fully testable without an email provider.
- ``smtp``: sends via SMTP using stdlib ``smtplib`` (set SMTP_* env vars).

Selected by ``EMAIL_BACKEND``. Failures are swallowed and logged so a mail
outage never breaks the request that triggered the email.
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("email")


def send_email(to: str, subject: str, body: str) -> bool:
    backend = (settings.email_backend or "console").lower()
    if backend == "smtp" and settings.smtp_host:
        return _send_smtp(to, subject, body)
    # console backend
    logger.info("email_console", to=to, subject=subject, body=body)
    return True


def _send_smtp(to: str, subject: str, body: str) -> bool:
    try:
        msg = EmailMessage()
        msg["From"] = settings.email_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        logger.info("email_sent", to=to, subject=subject)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("email_send_failed", to=to, error=str(exc))
        return False
