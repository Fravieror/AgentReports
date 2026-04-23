import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_SESSION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'whatsapp_session')

options = Options()
options.add_argument(f"--user-data-dir={WHATSAPP_SESSION_DIR}")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get("https://web.whatsapp.com")

print("WhatsApp Web is open.")
print("If you see a QR code, scan it with your phone now.")
print("Waiting up to 60 seconds for login...")

try:
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.XPATH, '//div[@aria-label="Chat list"]'))
    )
    print("Session saved successfully. You can close this window.")
    time.sleep(3)
except Exception:
    print("Timed out waiting for login. Please re-run and scan the QR code faster.")

driver.quit()
