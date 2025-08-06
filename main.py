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
import tempfile
import os
import yagmail
import shutil
from urllib.parse import urljoin
from dotenv import load_dotenv, dotenv_values 
import pandas as pd
from twilio.rest import Client

load_dotenv()

# Create a temporary directory for user data
user_data_dir = tempfile.mkdtemp()

options = Options()
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

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

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

# Navigate to download section
url = urljoin(os.getenv("GPS_REALTIME_WEB_URL"), "/reports/summary")
driver.get(url)
time.sleep(5)

print("Navigated to download section")

# Open the dropdown (using ARIA role is more reliable than CSS class)

# === 4. Select Device ===

device_dropdown = wait.until(
    EC.element_to_be_clickable((By.XPATH, "//div[@role='combobox' and contains(@class, 'MuiSelect-multiple')]"))
)

device_dropdown.click()

device_option = wait.until(
    EC.presence_of_element_located((By.XPATH, "//li[contains(text(), 'HW #3527 FRANSISCO D. GUX075 4.5G #1348')]"))
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

# Twilio credentials (store securely in Colab or environment)
TWILIO_ACCOUNT_SID = os.getenv('twilio_sid')
TWILIO_AUTH_TOKEN = os.getenv('twilio_token')
TWILIO_WHATSAPP_NUMBER = 'whatsapp:+14155238886'  # Twilio sandbox sender
RECIPIENT_WHATSAPP_NUMBERS = [
    'whatsapp:+573204665867'
]  # Replace with verified number

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
            

def extract_float(value):
    if isinstance(value, str):
        return float(value.split()[0])
    return float(value)

xlsx_file = downloaded_file
if xlsx_file:
    df = pd.read_excel(xlsx_file, skiprows=5)

    # Clean column names: strip spaces, lowercase
    df.columns = df.columns.str.strip().str.lower()

    top_speed = extract_float(df.loc[0, 'top speed'])
    distance = extract_float(df.loc[0, 'distance'])
    device = df.loc[0, 'device']

    if top_speed > 80:
        send_whatsapp(
            "⚠️ Alerta: Límite de velocidad excedido",
            f"Dispositivo: {device}\nLa velocidad máxima registrada hoy fue de {top_speed} km/h, lo cual excede el límite de 80 km/h."
        )

    if distance > 150:
        send_whatsapp(
            "⚠️ Alerta: Distancia recorrida excesiva",
            f"Dispositivo: {device}\nLa distancia registrada hoy fue de {distance} km, lo cual excede el límite de 150 km."
        )
else:
    print("No valid Excel file found to process.")



# === Cleanup ===

try:
    shutil.rmtree(user_data_dir)
    print(f"Temporary directory '{user_data_dir}' deleted.")
except Exception as e:
    print(f"Failed to delete temporary directory: {e}")

driver.quit()

