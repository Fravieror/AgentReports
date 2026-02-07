import os
from dotenv import load_dotenv

load_dotenv()

# Twilio credentials
TWILIO_ACCOUNT_SID = os.getenv('twilio_sid')
TWILIO_AUTH_TOKEN = os.getenv('twilio_token')
TWILIO_WHATSAPP_NUMBER = 'whatsapp:+14155238886'
RECIPIENT_WHATSAPP_NUMBERS = ['whatsapp:+570']

# Email credentials
EMAIL_ACCOUNT = os.getenv('gmail_us')
EMAIL_PASSWORD = os.getenv('gmail_pw')
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
RECIPIENT_EMAIL = os.getenv('recipient_email')

# Prices
PRICE_PER_GALLON_COP_GASOLINE = 15869
PRICE_PER_GGE_COP_NATURAL_GAS = 8500

# Maintenance schedule
MAINTENANCE_SCHEDULE = {
    "Duster 2021 1.0 TCe (Gasolina)": {
        "Aceite de motor": 10000,
        "Filtro de aire (motor)": 15000,
        "Filtro de combustible": 15000,
        "Bujías": 30000,
        "Correa serpentina / alternador": 60000,
        "Refrigerante": 90000,
        "Aceite de caja de cambios (manual)": 45000,
        "Filtro de cabina": 15000,
        "Discos freno": 80000,
        "Pastillas freno": 30000,
        "Bateria": 90000,
        "Revision Preventiva": 3000,
    }
}

MAINTENANCE_CSV = "maintenance_log.csv"

# Map your device names to vehicle types
DEVICE_TYPE_MAP = {
    'HW #3527 FRANSISCO D. GUX075 4.5G #1348': "Duster 2021 1.0 TCe (Gasolina)",
    'HW #3052 SANTIAGO D. LZO633 4.5G #714': "Duster 2021 1.0 TCe (Gasolina)",
    'HW #3637 SANTIAGO D. GET266 4.5G #1450': "Duster 2021 1.0 TCe (Gasolina)",
}