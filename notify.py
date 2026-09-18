"""
notify.py — sends email notifications via smtplib.

Reads SMTP credentials from environment variables so nothing sensitive is
hardcoded. If they're not set, notify_by_email() silently no-ops and returns
False — the app still works, it just won't send real emails (useful for
local testing before you wire up real SMTP creds).

Required env vars for real sending:
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
"""

import os
import smtplib
from email.mime.text import MIMEText


def is_configured() -> bool:
    return all(
        os.getenv(k) for k in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM")
    )


def notify_by_email(to_email: str, subject: str, body: str) -> bool:
    if not is_configured():
        return False

    host = os.environ["SMTP_HOST"]
    port = int(os.environ["SMTP_PORT"])
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    sender = os.environ["SMTP_FROM"]

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email

    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(sender, [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"[notify] email send failed: {e}")
        return False