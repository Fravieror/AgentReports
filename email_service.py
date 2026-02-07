import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import EMAIL_ACCOUNT, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT, RECIPIENT_EMAIL


def send_email(subject, body):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ACCOUNT
    recipients = [email.strip() for email in RECIPIENT_EMAIL.split(",")]
    msg["To"] = ",".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ACCOUNT, recipients, msg.as_string())
        print(f"Email sent: {subject}")
    except Exception as e:
        print(f"Email failed: {e}")
