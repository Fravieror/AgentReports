from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import tempfile
import os
import yagmail
import shutil
from urllib.parse import urljoin
from dotenv import load_dotenv, dotenv_values 
import pandas as pd
from twilio.rest import Client
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import csv

load_dotenv()


# Twilio credentials (store securely in Colab or environment)
TWILIO_ACCOUNT_SID = os.getenv('twilio_sid')
TWILIO_AUTH_TOKEN = os.getenv('twilio_token')
TWILIO_WHATSAPP_NUMBER = 'whatsapp:+14155238886'  # Twilio sandbox sender
RECIPIENT_WHATSAPP_NUMBERS = [
    'whatsapp:+573204665867'
]  # Replace with verified number

# Step 3: Define email credentials and config
EMAIL_ACCOUNT = os.getenv('gmail_us')
EMAIL_PASSWORD = os.getenv('gmail_pw')  # Use app password if 2FA is enabled
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
RECIPIENT_EMAIL = os.getenv('recipient_email')

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


# Prices (Aug 2025 Colombia averages)
PRICE_PER_GALLON_COP_GASOLINE = 15869
PRICE_PER_GGE_COP_NATURAL_GAS = 8500

# Efficiencies
FUEL_EFFICIENCY_KM_PER_GALLON_GASOLINE = 45.0
FUEL_EFFICIENCY_KM_PER_GGE_NATURAL_GAS = 96.5

# Natural Gas Tank Capacity in GGE
CNG_TANK_CAPACITY_GGE = 3.11
CNG_MAX_RANGE_KM = CNG_TANK_CAPACITY_GGE * FUEL_EFFICIENCY_KM_PER_GGE_NATURAL_GAS

# === Google Sheets setup ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client_gs = gspread.authorize(creds)

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
    }
}

# Map your device names to vehicle types
DEVICE_TYPE_MAP = {
    'HW #3527 FRANSISCO D. GUX075 4.5G #1348': "Duster 2021 1.0 TCe (Gasolina)",
    'HW #3052 SANTIAGO D. LZO633 4.5G #714': "Duster 2021 1.0 TCe (Gasolina)",
    'HW #3637 SANTIAGO D. GET266 4.5G #1450': "Duster 2021 1.0 TCe (Gasolina)",
}

MAINTENANCE_CSV = "maintenance_log.csv"

# Create a temporary directory for user data
user_data_dir = tempfile.mkdtemp()

options = Options()
options.binary_location = shutil.which("chromium-browser") or shutil.which("chromium")
options.add_argument(f"--user-data-dir={user_data_dir}")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--headless")

options.add_experimental_option("prefs", {
    "download.default_directory": user_data_dir,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
})

chromedriver_path = shutil.which("chromedriver")
if not chromedriver_path:
    raise RuntimeError("chromedriver not found in PATH. Install it with: sudo apt install chromium-chromedriver")

service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=options)

url = urljoin(os.getenv("GPS_REALTIME_WEB_URL"), "/login")
driver.get(url)

wait = WebDriverWait(driver, 10)

# Wait and fill in the email field
email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
email_input.clear()
email_input.send_keys(os.getenv("GPS_REALTIME_USER"))

# Wait and fill in the password field
password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
password_input.clear()
password_input.send_keys(os.getenv("GPS_REALTIME_PW"))

# Wait and click the login button
login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
login_button.click()

print("Logged in successfully")

def get_last_maintenance(device, component):
    try:
        with open(MAINTENANCE_CSV, mode="r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["device"] == device and row["component"] == component:
                    return float(row["odometer"])
    except FileNotFoundError:
        pass
    return None

def update_maintenance(device, component, odometer):
    rows = []
    found = False
    try:
        with open(MAINTENANCE_CSV, mode="r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["device"] == device and row["component"] == component:
                    row["odometer"] = str(odometer)
                    found = True
                rows.append(row)
    except FileNotFoundError:
        pass
    if not found:
        rows.append({"device": device, "component": component, "odometer": str(odometer)})
    with open(MAINTENANCE_CSV, mode="w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["device", "component", "odometer"])
        writer.writeheader()
        writer.writerows(rows)

def send_email(subject, body):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ACCOUNT
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ACCOUNT, RECIPIENT_EMAIL, msg.as_string())
        print(f"Email sent: {subject}")
    except Exception as e:
        print(f"Email failed: {e}")


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
            

def extract_float(value):
    if isinstance(value, str):
        return float(value.split()[0])
    return float(value)

# Open the dropdown (using ARIA role is more reliable than CSS class)

# === 4. Select Device ===
devices = ['HW #3527 FRANSISCO D. GUX075 4.5G #1348', 'HW #3052 SANTIAGO D. LZO633 4.5G #714', 'HW #3637 SANTIAGO D. GET266 4.5G #1450']

alerts_email_body = []
alerts_whatsapp_body = []

# Open the sheet (by name or by URL)
sheet = client_gs.open("Vehicle Daily Report").sheet1  # Change to your Google Sheet name

for devi in devices:
    
    # Navigate to download section
    url = urljoin(os.getenv("GPS_REALTIME_WEB_URL"), "/reports/summary")
    driver.get(url)
    time.sleep(5)

    print("Navigated to download section")

    
    device_dropdown = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//div[@role='combobox' and contains(@class, 'MuiSelect-multiple')]"))
    )

    device_dropdown.click()

    device_option = wait.until(
        EC.presence_of_element_located((By.XPATH, f"//li[contains(text(), '{devi}')]"))
    )

    device_option.click()
    ActionChains(driver).send_keys(Keys.ESCAPE).perform()

    time.sleep(1)

    print("Dropdown opened")

    try:
        wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "MuiBackdrop-root")))
    except:
        print("No backdrop found, proceeding")

    # Click the dropdown button
    dropdown_button = wait.until(
        EC.element_to_be_clickable((
            By.XPATH, "//div[@role='group' and contains(@class, 'MuiButtonGroup')]//button[contains(@class, 'MuiButtonGroup-lastButton')]"
        ))
    )
    try:
        dropdown_button.click()
    except Exception as ex:
        print("Standard click failed, attempting JavaScript click")
        driver.execute_script("arguments[0].click();", dropdown_button)
    print("Dropdown button clicked")

    time.sleep(3)

    # Select export option
    try:
        export_option = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//li[normalize-space()='Export']"))
        )
        export_option.click()
        print("Export option clicked")
    except TimeoutException:
        print("Export option not found within the timeout window.")
        driver.quit()
        exit()
    print("Export option clicked")

    # Click the final Export button inside the export dialog
    export_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//div[@role='group']//button[.//span[normalize-space()='Export']]"))
    )
    export_button.click()
    print("Final Export button clicked")


    # === 8. Wait for file download ===
    downloaded_file = None
    for _ in range(30):
        files = [f for f in os.listdir(user_data_dir) if f.endswith(".xlsx")]
        if files:
            downloaded_file = os.path.join(user_data_dir, files[0])
            break
        time.sleep(1)

    if not downloaded_file:
        print("Download failed.")
        driver.quit()
        exit()

    print("Download successful:", downloaded_file)

    xlsx_file = downloaded_file
    if xlsx_file:
        try:
            alerts_email_body.append(
                f"{'='*30}\n"  # separator line
                f"📍 Dispositivo: {devi}\n"
                f"{'-'*30}\n"

            )
            
            df = pd.read_excel(xlsx_file, skiprows=5)

            # Clean column names: strip spaces, lowercase
            df.columns = df.columns.str.strip().str.lower()

            top_speed = extract_float(df.loc[0, 'top speed'])
            distance = extract_float(df.loc[0, 'distance'])
            odometer = extract_float(df.loc[0, 'end odometer'])

            # --- SPEED CHECK ---
            if top_speed > 80:
                alerts_email_body.append(
                    f"⚠️ Límite de velocidad excedido - {devi}\n"
                    f"Velocidad máxima: {top_speed} km/h\n"
                )

            # --- DISTANCE CHECK ---
            if distance > 150:
                alerts_email_body.append(
                    f"⚠️ Distancia excesiva - {devi}\n"
                    f"Distancia: {distance} km\n"
                )

            # --- MAINTENANCE CHECK ---
            maintenance_due = []
            vehicle_type = DEVICE_TYPE_MAP.get(devi)
            if vehicle_type:
                for component, interval in MAINTENANCE_SCHEDULE[vehicle_type].items():
                    last_maint = get_last_maintenance(devi, component)
                    if last_maint is None or (odometer - last_maint) >= interval:
                        maintenance_due.append(f"🔧 {component} (cada {interval:,} km) - ¡Revisar!")
                        update_maintenance(devi, component, odometer)

            # Add maintenance_due to email body
            if maintenance_due:
                alerts_email_body.append("🚗 *Mantenimientos requeridos:*\n" + "\n".join(maintenance_due) + "\n")
            
            # --- FUEL SPLIT CALCULATION ---
            PRICE_PER_GALLON_COP_GASOLINE = 15869
            PRICE_PER_GGE_COP_NATURAL_GAS = 8500
            FUEL_EFFICIENCY_KM_PER_GALLON_GASOLINE = 47.0
            FUEL_EFFICIENCY_KM_PER_GGE_NATURAL_GAS = 53.0
            CNG_TANK_CAPACITY_GGE = 13.1
            CNG_MAX_RANGE_KM = CNG_TANK_CAPACITY_GGE * FUEL_EFFICIENCY_KM_PER_GGE_NATURAL_GAS

            if distance <= CNG_MAX_RANGE_KM:
                fuel_gge_cng = distance / FUEL_EFFICIENCY_KM_PER_GGE_NATURAL_GAS
                fuel_cost_cng = fuel_gge_cng * PRICE_PER_GGE_COP_NATURAL_GAS
                fuel_gallons_gasoline = 0
                fuel_cost_gasoline = 0
            else:
                fuel_gge_cng = CNG_TANK_CAPACITY_GGE
                fuel_cost_cng = fuel_gge_cng * PRICE_PER_GGE_COP_NATURAL_GAS
                remaining_km = distance - CNG_MAX_RANGE_KM
                fuel_gallons_gasoline = remaining_km / FUEL_EFFICIENCY_KM_PER_GALLON_GASOLINE
                fuel_cost_gasoline = fuel_gallons_gasoline * PRICE_PER_GALLON_COP_GASOLINE

            alerts_email_body.append(
                f"⛽ Consumo estimado - {devi}\n"
                f"Distancia: {distance:.1f} km\n"
                f"CNG: {fuel_gge_cng:.2f} gal (GGE), {fuel_cost_cng:,.0f} COP\n"
                f"Gasolina: {fuel_gallons_gasoline:.2f} gal, {fuel_cost_gasoline:,.0f} COP\n"
            )
            
            # --- Inside your loop after you calculate fuel usage ---
            report_date = datetime.now().date()
            month_year = report_date.strftime("%m-%Y")
            daily_consumption = fuel_gge_cng + fuel_gallons_gasoline

            # Append data to the Google Sheet
            sheet.append_row([
                month_year,                 # Month-Year
                devi,
                str(report_date),           # Date
                round(fuel_gge_cng, 2),     # CNG consumption (gal)
                round(fuel_gallons_gasoline, 2),  # Gasoline consumption (gal)
                round(fuel_cost_cng, 0),    # CNG cost (COP)
                round(fuel_cost_gasoline, 0),  # Gasoline cost (COP)
                round(distance, 2),         # Distance (km)
                top_speed,                  # Top speed (km/h)
                odometer                   # Odometer (km)         # Oil change required (bool)
            ])
            
        except Exception as e:
            print(e)
        

    else:
        print("No valid Excel file found to process.")
    
    # After processing df
    if downloaded_file and os.path.exists(downloaded_file):
        os.remove(downloaded_file)

        
# --- SEND ONLY ONCE ---
if alerts_email_body:
    combined_body = "\n".join(alerts_email_body)
    send_email("Reporte diario de alertas y consumo", combined_body)

# === Cleanup ===

try:
    shutil.rmtree(user_data_dir)
    print(f"Temporary directory '{user_data_dir}' deleted.")
except Exception as e:
    print(f"Failed to delete temporary directory: {e}")

driver.quit()

