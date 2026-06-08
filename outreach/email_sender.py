"""
Cold email outreach engine.
Uses Gmail SMTP (free) or SendGrid (better deliverability).
Set SMTP_EMAIL, SMTP_PASSWORD (or SENDGRID_API_KEY) in .env.
"""

import os
import time
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SENDER_NAME = os.getenv("SENDER_NAME", "Your Name")

TEMPLATES_DIR = Path(__file__).parent / "templates"
LOG_FILE = Path(__file__).parent / "outreach_log.json"


def load_template(business_type: str) -> tuple[str, str]:
    """Return (subject, body) for a business type. Falls back to generic."""
    btype = business_type.lower().replace(" ", "_")
    template_path = TEMPLATES_DIR / f"{btype}.txt"
    if not template_path.exists():
        template_path = TEMPLATES_DIR / "generic.txt"
    content = template_path.read_text()
    lines = content.strip().split("\n")
    subject = lines[0].replace("Subject: ", "").strip()
    body = "\n".join(lines[2:]).strip()
    return subject, body


def render(text: str, lead: dict) -> str:
    return text.format(
        business_name=lead.get("business_name", "your business"),
        contact_name=lead.get("contact_name", "there"),
        city=lead.get("city", "your city"),
        sender_name=SENDER_NAME,
    )


def send_email(to_email: str, subject: str, body: str) -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{SENDER_NAME} <{SMTP_EMAIL}>"
        msg["To"] = to_email
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[email] Failed to send to {to_email}: {e}")
        return False


def run_campaign(leads: list[dict], delay_seconds: int = 30) -> dict:
    """
    Send cold emails to a list of leads.
    leads: list of dicts with keys: email, business_name, business_type, contact_name, city
    delay_seconds: pause between emails to avoid spam filters
    """
    log = []
    sent, failed, skipped = 0, 0, 0

    for lead in leads:
        email = lead.get("email", "").strip()
        if not email:
            skipped += 1
            continue

        btype = lead.get("business_type", "generic")
        subject_tpl, body_tpl = load_template(btype)
        subject = render(subject_tpl, lead)
        body = render(body_tpl, lead)

        print(f"[email] Sending to {email} ({lead.get('business_name')})...")
        ok = send_email(email, subject, body)
        status = "sent" if ok else "failed"
        if ok:
            sent += 1
        else:
            failed += 1

        log.append({
            "email": email,
            "business": lead.get("business_name"),
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        })

        if delay_seconds > 0:
            time.sleep(delay_seconds)

    summary = {"sent": sent, "failed": failed, "skipped": skipped, "log": log}
    LOG_FILE.write_text(json.dumps(summary, indent=2))
    print(f"\n[campaign] Done — sent:{sent} failed:{failed} skipped:{skipped}")
    print(f"[campaign] Log saved to {LOG_FILE}")
    return summary


if __name__ == "__main__":
    import sys

    leads_file = sys.argv[1] if len(sys.argv) > 1 else None
    if not leads_file:
        print("Usage: python email_sender.py leads.json")
        sys.exit(1)

    with open(leads_file) as f:
        leads = json.load(f)

    print(f"Loaded {len(leads)} leads from {leads_file}")
    confirm = input(f"Send emails to {len([l for l in leads if l.get('email')])} leads with emails? [y/N] ")
    if confirm.lower() != "y":
        print("Aborted.")
        sys.exit(0)

    run_campaign(leads, delay_seconds=30)
