import logging
import smtplib
import json
from email.mime.text import MIMEText

logger = logging.getLogger()


def get_email_credentials() -> dict:
    """Load email credentials from a JSON file."""
    with open("credentials/email_account.json", "r") as f:
        return json.load(f)


def send_email_alert(
    subject: str,
    body: str,
    sender_email: str = None,
    sender_password: str = None,
    recipient_emails: list[str] | None = None,
) -> None:
    """Send an email alert using SMTP."""
    cred = get_email_credentials()
    if recipient_emails is None:
        recipient_emails = []
    if sender_email is None:
        sender_email = cred["sender_email"]
    if sender_password is None:
        sender_password = cred["sender_password"]
    for email in cred.get("recipient_emails", []):
        recipient_emails.append(email)
    if len(recipient_emails) == 0:
        logger.warning("No recipient emails provided.")
        return
    for recipient_email in recipient_emails:
        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = sender_email
            msg["To"] = recipient_email

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipient_email, msg.as_string())
            logger.info("Email alert sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")


if __name__ == "__main__":
    send_email_alert("Test Subject", "Test Body")
