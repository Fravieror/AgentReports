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


# Create a temporary directory for user data
user_data_dir = tempfile.mkdtemp()

options = Options()
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


EMAIL_TO = "lfravierl@gmail.com"

# === 9. Send Email ===
yag = yagmail.SMTP(os.getenv("GMAIL_USER"), os.getenv("GMAIL_APP_PASSWORD"))
yag.send(
    to=EMAIL_TO,
    subject="Daily TEDA operation report",
    contents="FYI",
    attachments=downloaded_file
)

print(f"Report sent to {EMAIL_TO}")

# === Cleanup ===

try:
    shutil.rmtree(user_data_dir)
    print(f"Temporary directory '{user_data_dir}' deleted.")
except Exception as e:
    print(f"Failed to delete temporary directory: {e}")

driver.quit()

