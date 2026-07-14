import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
from app.core.config import SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, RESEND_API_KEY, SENDGRID_API_KEY

def send_email(to_email: str, subject: str, body: str, is_html: bool = False) -> bool:
    """Send an email using Resend API (HTTP POST) if RESEND_API_KEY is configured,
    otherwise fallback to standard SMTP/SMTP_SSL."""
    if SENDGRID_API_KEY:
        try:
            print("[DEBUG SENDGRID] Attempting to send email via SendGrid API...")
            url = "https://api.sendgrid.com/v3/mail/send"
            headers = {
                "Authorization": f"Bearer {SENDGRID_API_KEY}",
                "Content-Type": "application/json"
            }
            from_sender = SMTP_USERNAME.strip() if SMTP_USERNAME else "bengalurugaurav2188@gmail.com"
            data = {
                "personalizations": [
                    {
                        "to": [{"email": to_email}]
                    }
                ],
                "from": {
                    "email": from_sender,
                    "name": "PES University Onboarding"
                },
                "subject": subject,
                "content": [
                    {
                        "type": "text/html" if is_html else "text/plain",
                        "value": body
                    }
                ]
            }
            res = requests.post(url, headers=headers, json=data, timeout=15)
            if res.status_code in [200, 201, 202]:
                logging.info(f"Successfully dispatched email via SendGrid to {to_email}")
                return True
            else:
                logging.error(f"Failed to dispatch email via SendGrid (status code {res.status_code}): {res.text}")
        except Exception as e:
            logging.error(f"Failed to dispatch email via SendGrid API: {e}")

    if RESEND_API_KEY:
        try:
            print("[DEBUG RESEND] Attempting to send email via Resend API...")
            url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            }
            from_sender = SMTP_USERNAME.strip() if SMTP_USERNAME else "onboarding@resend.dev"
            data = {
                "from": from_sender,
                "to": to_email,
                "subject": subject
            }
            if is_html:
                data["html"] = body
            else:
                data["text"] = body
                
            res = requests.post(url, headers=headers, json=data, timeout=15)
            if res.status_code in [200, 201, 202]:
                logging.info(f"Successfully dispatched email via Resend to {to_email}")
                return True
            elif res.status_code == 403 and "You can only send testing emails to" in res.text:
                import re
                match = re.search(r"email address \(([^)]+)\)", res.text)
                if match:
                    allowed_email = match.group(1)
                    print(f"[DEBUG RESEND] Rerouting sandbox email from {to_email} to verified email {allowed_email}...")
                    data["to"] = allowed_email
                    data["subject"] = f"[{to_email}] {subject}"
                    res_retry = requests.post(url, headers=headers, json=data, timeout=15)
                    if res_retry.status_code in [200, 201, 202]:
                        logging.info(f"Successfully dispatched rerouted email via Resend to {allowed_email}")
                        return True
                    else:
                        logging.error(f"Failed to dispatch rerouted email via Resend (status code {res_retry.status_code}): {res_retry.text}")
            else:
                logging.error(f"Failed to dispatch email via Resend (status code {res.status_code}): {res.text}")
                # Attempt to fallback to SMTP if Resend returns an error code
        except Exception as e:
            logging.error(f"Failed to dispatch email via Resend API: {e}")
            # Attempt to fallback to SMTP if Resend throws an exception
            
    # SMTP Fallback
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_USERNAME
        msg["To"] = to_email
        msg.attach(MIMEText(body, "html" if is_html else "plain"))
        
        print(f"[DEBUG SMTP] Destination email address: {to_email}")
        
        if SMTP_PORT == 465:
            print("SMTP_SSL Connection Attempting...")
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.sendmail(SMTP_USERNAME, to_email, msg.as_string())
        else:
            print("SMTP STARTTLS Connection Attempting...")
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.sendmail(SMTP_USERNAME, to_email, msg.as_string())
                
        logging.info(f"Successfully dispatched email to {to_email}")
        return True
    except Exception as e:
        logging.error(f"Failed to dispatch email to {to_email}: {e}")
        return False
