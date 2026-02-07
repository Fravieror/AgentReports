from twilio.rest import Client
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER, RECIPIENT_WHATSAPP_NUMBERS

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def send_whatsapp(subject, body):
    message = f"*{subject}*\n{body}"
    for number in RECIPIENT_WHATSAPP_NUMBERS:
        try:
            message = client.messages.create(
                body=message,
                from_=TWILIO_WHATSAPP_NUMBER,
                to=number
            )
            print(f"Message sent to {number}: {message.sid}")
        except Exception as e:
            print(f"Failed to send to {number}: {e}")
