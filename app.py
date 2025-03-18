from flask import Flask, jsonify, request
import threading
import os
import json
import time
import re
import gspread
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# Global variable to track script status
script_running = False


def run_selenium_script():
    """Function that runs Selenium to scrape job details"""
    global script_running
    script_running = True

    try:
        # ✅ SETUP SELENIUM
        options = Options()
        options.add_argument("--headless")  # ✅ Run in headless mode for the server
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        # ✅ Open login page
        driver.get("https://pro.proconnect.com/login")
        time.sleep(10)

        # ✅ Click "Sign In" button
        try:
            sign_in_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "button-interactive"))
            )
            sign_in_button.click()
            time.sleep(3)
        except Exception:
            print("❌ Failed to click 'Sign In' button!")

        # ✅ Enter login credentials
        try:
            username_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "loginId"))
            )
            password_field = driver.find_element(By.ID, "password")
            login_button = driver.find_element(By.ID, "login-btn")

            username_field.send_keys("office@gardnerplumbingco.com")
            password_field.send_keys("Job13:14!")
            login_button.click()
            time.sleep(10)
        except Exception:
            print("❌ Failed to enter credentials!")

        # ✅ Extract job data (Shortened for simplicity)
        jobs_data = []
        job_elements = driver.find_elements(By.XPATH,
                                            "//div[contains(@class, '_statusPill_dzcst_42') and contains(text(), 'Assign Pro')]")

        for job in job_elements[:5]:  # Limit to first 5 jobs
            job_text = job.text.strip()
            jobs_data.append({"Job": job_text})

        driver.quit()

    try: # ✅ Load credentials from environment variable
        json_creds = os.getenv("GOOGLE_SERVICE_ACCOUNT")

    if json_creds:
        creds = Credentials.from_service_account_info(json.loads(json_creds))
        client = gspread.authorize(creds)
    else:
        raise ValueError("❌ GOOGLE_SERVICE_ACCOUNT environment variable not set!")
       
    # ✅ Google Sheets Setup (This should be outside of the if-else)
    SHEET_NAME = "AcceptedJobsFDPtoST"
    SHEET_TAB = "ASSIGNPROJOBS"

    sheet = client.open(SHEET_NAME).worksheet(SHEET_TAB)
    new_jobs_df = pd.DataFrame(jobs_data)
    sheet.append_rows(new_jobs_df.values.tolist())

    print("✅ Jobs added to Google Sheets!")

    except Exception as e:
        print(f"⚠️ Error: {e}")

    finally:
        script_running = False


@app.route('/run-script', methods=['GET'])
def start_script():
    """API Endpoint to start the Selenium script"""
    if script_running:
        return jsonify({"message": "Script is already running!"}), 400

    thread = threading.Thread(target=run_selenium_script)
    thread.start()

    return jsonify({"message": "Script started successfully!"})


@app.route('/status', methods=['GET'])
def check_status():
    """API Endpoint to check if the script is running"""
    return jsonify({"script_running": script_running})


if __name__ == '__main__':
    app.run(debug=True)
