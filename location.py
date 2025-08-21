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

def extract_float(value):
    if isinstance(value, str):
        return float(value.split()[0])
    return float(value)

# Step 3: Define email credentials and config
EMAIL_ACCOUNT = os.getenv('gmail_us')
EMAIL_PASSWORD = os.getenv('gmail_pw')  # Use app password if 2FA is enabled
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
RECIPIENT_EMAIL = os.getenv('recipient_email')

def send_email(subject, body):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ACCOUNT
    recipients = [email.strip() for email in RECIPIENT_EMAIL.split(",")]
    print(recipients)
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

# Create a temporary directory for user data
user_data_dir = tempfile.mkdtemp()

options = Options()
options.binary_location = shutil.which("chromium-browser") or shutil.which("chromium")
options.add_argument(f"--user-data-dir={user_data_dir}")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
# options.add_argument("--headless")

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
# Open the dropdown (using ARIA role is more reliable than CSS class)

# === 4. Select Device ===
devices = ['HW #3527 FRANSISCO D. GUX075 4.5G #1348']

alerts_email_body = []
alerts_whatsapp_body = []

for devi in devices:
    
    # Navigate to download section
    url = urljoin(os.getenv("GPS_REALTIME_WEB_URL"), "/reports/stop")
    driver.get(url)
    time.sleep(5)

    print("Navigated to download section")

    device_dropdown = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//label[normalize-space()='Device']/following-sibling::div//input"))
    )

    device_dropdown.click()

    # Type the device name (helps filtering options in MUI Autocomplete)
    device_dropdown.send_keys(devi)
    time.sleep(1)

    device_option = wait.until(
        EC.presence_of_element_located((By.XPATH, f"//li[contains(text(), '{devi}')]"))
    )
    driver.execute_script("arguments[0].click();", device_option)
    print(f"✅ Selected device: {devi}")
    time.sleep(1)

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
        time.sleep(2)

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
            
            # Get the last row for the address
            if df.empty:
                print(f"No data found in the report for device {devi}.")
                continue
            
            last_row = df.iloc[-1]
            end_address = last_row.get('start address', 'N/A')

            if end_address != 'Ricaurte, Alto Magdalena, Cundinamarca, RAP (Especial) Central, 252431, Colombia':
                alerts_email_body.append(f"Alerta: El dispositivo {devi} terminó en una ubicación inesperada: {end_address}\n")
            
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

