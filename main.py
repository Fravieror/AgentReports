"""Orchestrator script: login, export reports, process and notify.

This file is the simplified orchestrator that uses the service modules
for email/WhatsApp and the data processing module for alert logic.
"""

import os
import time
import tempfile
import shutil
from urllib.parse import urljoin
from datetime import datetime

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

from config import DEVICE_TYPE_MAP
from email_service import send_email
from whatsapp_service import send_whatsapp
from data_processing import process_data

import gspread
from oauth2client.service_account import ServiceAccountCredentials


def extract_float(value):
    if isinstance(value, str):
        try:
            return float(value.split()[0])
        except Exception:
            return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def setup_driver(download_dir: str):
    options = Options()
    options.add_argument(f"--user-data-dir={download_dir}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless=new")
    options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })

    chromedriver_path = ChromeDriverManager().install()
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def setup_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    return gspread.authorize(creds)


def main():
    devices = list(DEVICE_TYPE_MAP.keys())
    user_data_dir = tempfile.mkdtemp()
    driver = None
    alerts_email_body = []

    try:
        driver = setup_driver(user_data_dir)

        # Login
        url = urljoin(os.getenv("GPS_REALTIME_WEB_URL"), "/login")
        driver.get(url)
        wait = WebDriverWait(driver, 15)
        email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
        email_input.clear()
        email_input.send_keys(os.getenv("GPS_REALTIME_USER"))
        password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        password_input.clear()
        password_input.send_keys(os.getenv("GPS_REALTIME_PW"))
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
        login_button.click()

        # Google Sheets client
        client_gs = setup_sheets()
        sheet = client_gs.open("Vehicle Daily Report").sheet1

        for devi in devices:
            # Navigate to report and export
            url = urljoin(os.getenv("GPS_REALTIME_WEB_URL"), "/reports/summary")
            driver.get(url)
            time.sleep(4)

            wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@role='combobox' and contains(@class, 'MuiSelect-multiple')]"))).click()
            device_option = wait.until(EC.presence_of_element_located((By.XPATH, f"//li[contains(text(), '{devi}')]")))
            device_option.click()
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()

            # Open export menu
            dropdown_button = wait.until(EC.element_to_be_clickable((
                By.XPATH, "//div[@role='group' and contains(@class, 'MuiButtonGroup')]//button[contains(@class, 'MuiButtonGroup-lastButton')]")
            ))
            try:
                dropdown_button.click()
            except Exception:
                driver.execute_script("arguments[0].click();", dropdown_button)

            # Click Export
            try:
                export_option = wait.until(EC.element_to_be_clickable((By.XPATH, "//li[normalize-space()='Export']")))
                export_option.click()
                export_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@role='group']//button[.//span[normalize-space()='Export']]") ))
                export_button.click()
            except TimeoutException:
                print("Export UI not found for device", devi)
                continue

            # Wait for download
            downloaded_file = None
            for _ in range(30):
                files = [f for f in os.listdir(user_data_dir) if f.endswith('.xlsx')]
                if files:
                    downloaded_file = os.path.join(user_data_dir, files[0])
                    break
                time.sleep(2)

            if not downloaded_file:
                print("Download failed for", devi)
                continue

            try:
                df = pd.read_excel(downloaded_file, skiprows=5)
                df.columns = df.columns.str.strip().str.lower()
                top_speed = extract_float(df.loc[0, 'top speed'])
                distance = extract_float(df.loc[0, 'distance'])
                odometer = extract_float(df.loc[0, 'end odometer'])
                engine_hours = 0
                try:
                    engine_hours = df.loc[0, 'engine hours'].total_seconds() / 3600
                except Exception:
                    engine_hours = float(df.loc[0].get('engine hours', 0) or 0)

                alerts_email_body = process_data(devi, distance, top_speed, odometer, engine_hours, alerts_email_body)

                # Fuel & sheet data (keep previous logic concise)
                AC_FACTOR = 1.20
                TERRAIN_FACTOR = 1.15
                FUEL_EFF_KM_GAS = 47.0 / (TERRAIN_FACTOR * AC_FACTOR)
                FUEL_EFF_KM_CNG = 53.0 / (TERRAIN_FACTOR * AC_FACTOR)
                CNG_TANK_GGE = 3.7
                CNG_MAX_RANGE = CNG_TANK_GGE * FUEL_EFF_KM_CNG

                if distance <= CNG_MAX_RANGE:
                    fuel_gge_cng = distance / FUEL_EFF_KM_CNG
                    fuel_gallons_gasoline = (distance * 0.1) / FUEL_EFF_KM_GAS
                else:
                    fuel_gge_cng = CNG_TANK_GGE
                    remaining_km = max(0, distance - CNG_MAX_RANGE)
                    fuel_gallons_gasoline = remaining_km / FUEL_EFF_KM_GAS

                fuel_cost_cng = fuel_gge_cng * float(os.getenv('PRICE_PER_GGE', 8500))
                fuel_cost_gasoline = fuel_gallons_gasoline * float(os.getenv('PRICE_PER_GALLON', 15869))

                report_date = datetime.now().date()
                month_year = report_date.strftime("%m-%Y")
                sheet.append_row([
                    month_year,
                    devi,
                    str(report_date),
                    round(fuel_gge_cng, 2),
                    round(fuel_gallons_gasoline, 2),
                    round(fuel_cost_cng, 0),
                    round(fuel_cost_gasoline, 0),
                    round(distance, 2),
                    top_speed,
                    odometer
                ])

            except Exception as e:
                print("Processing error for", devi, e)
            finally:
                try:
                    if downloaded_file and os.path.exists(downloaded_file):
                        os.remove(downloaded_file)
                except Exception:
                    pass

        # Send notifications once
        if alerts_email_body:
            combined = "\n".join(alerts_email_body)
            send_email("Reporte diario de alertas y consumo", combined)
            try:
                send_whatsapp("Reporte diario de alertas y consumo", combined)
            except Exception:
                print("WhatsApp send failed (continuing)")

    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
        try:
            shutil.rmtree(user_data_dir)
        except Exception:
            pass


if __name__ == '__main__':
    main()

