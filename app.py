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
import subprocess
import chromedriver_autoinstaller

app = Flask(__name__)

# Global variable to track script status
script_running = False

def run_selenium_script():
    """Function that runs Selenium to scrape job details"""
    global script_running
    script_running = True

    try:
        # ✅ Install Chrome manually before running Selenium
        chrome_url = "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
        chromedriver_url = "https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip"

        os.system(f"wget {chrome_url} -O /tmp/chrome.deb")
        os.system("dpkg -i /tmp/chrome.deb || apt-get -f install -y")
        
        os.system(f"wget {chromedriver_url} -O /tmp/chromedriver.zip")
        os.system("unzip /tmp/chromedriver.zip -d /tmp/")  # ✅ Extract to /tmp/
        os.system("chmod +x /tmp/chromedriver")  # ✅ Ensure it's executable

        # ✅ Define the Chrome binary path explicitly
        chrome_path = "/usr/bin/google-chrome"  # Path to pre-installed Chrome on Render
        chromedriver_path = "/tmp/chromedriver"  # ✅ Use the extracted path in /tmp/

        options = Options()
        options.binary_location = chrome_path  # ✅ Use the pre-installed Chrome
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # ✅ Use installed chromedriver from /tmp/
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)

        # ✅ Open login page
        driver.get("https://pro.proconnect.com/login")
        time.sleep(10)

        try:
            # ✅ Click "Sign In" button
            sign_in_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "button-interactive"))
            )
            sign_in_button.click()
            time.sleep(3)
        except Exception:
            print("❌ Failed to click 'Sign In' button!")

        try:
            # ✅ Enter login credentials
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

        # ✅ Extract job data
        jobs_data = []
        base_url = "https://pro.proconnect.com/jobs"
        driver.get(base_url)
        time.sleep(5)

        def get_job_list():
            """ Re-fetch job elements to avoid stale element errors """
            return driver.find_elements(By.XPATH, "//div[contains(@class, '_statusPill_dzcst_42') and contains(text(), 'Assign Pro')]")

        job_elements = get_job_list()

        for index in range(len(job_elements)):
            try:
                job_elements = get_job_list()
                job_status = job_elements[index]
                job_entry = job_status.find_element(By.XPATH, "./ancestor::div[contains(@data-testid, 'appointment-list-item')]")
                job_entry.click()
                time.sleep(5)

                def extract_text_with_js(xpath):
                    """ Extracts text using JavaScript execution """
                    try:
                        element = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, xpath))
                        )
                        text = driver.execute_script("return arguments[0].innerText;", element).strip()
                        return text if text else "N/A"
                    except Exception:
                        return "N/A"

                # ✅ Extract Data
                job_service = extract_text_with_js("//div[@id='jobPage.jobDetails']//div[h6[contains(text(), 'Service:')]]").replace("Service:", "").strip()
                job_work_order = extract_text_with_js("//div[@id='jobPage.jobDetails']//div[h6[contains(text(), 'Work Order:')]]").replace("Work Order:", "").strip()
                customer_name = extract_text_with_js("//div[@id='jobPage.customerInfo']//div[h6[contains(text(), 'Name:')]]").replace("Name:", "").strip()
                customer_phone = extract_text_with_js("//div[@id='jobPage.customerInfo']//div[h6[contains(text(), 'Phone:')]]").replace("Phone:", "").strip()
                job_description = extract_text_with_js("//div[@id='jobPage.description']//div[contains(@class, 'text-body-long')]")

                appointment_date = extract_text_with_js("//div[@data-testid='jobDetail.appointmentTime']//div[1]")
                appointment_time = extract_text_with_js("//div[@data-testid='jobDetail.appointmentTime']//div[2]")

                street_address = extract_text_with_js("//div[@data-testid='address.street']")
                city_state_zip = extract_text_with_js("//div[contains(@class, '_cityStateZip')]")

                jobs_data.append({
                    "Service": job_service,
                    "Work Order": job_work_order,
                    "Name": customer_name,
                    "Phone": customer_phone,
                    "Street Address": street_address,
                    "City": city_state_zip,
                    "Appointment Date": appointment_date,
                    "Appointment Time": appointment_time,
                    "Job Description": job_description
                })

                driver.get(base_url)
                time.sleep(5)

            except Exception as e:
                print(f"⚠️ Error processing job {index+1}: {e}")

        # ✅ Google Sheets Integration
        json_creds = os.getenv("GOOGLE_SERVICE_ACCOUNT")
        if json_creds:
            creds = Credentials.from_service_account_info(json.loads(json_creds))
            client = gspread.authorize(creds)
            sheet = client.open("AcceptedJobsFDPtoST").worksheet("ASSIGNPROJOBS")
            new_jobs_df = pd.DataFrame(jobs_data)
            sheet.append_rows(new_jobs_df.values.tolist())
        else:
            print("❌ GOOGLE_SERVICE_ACCOUNT environment variable not set!")

    except Exception as e:
        print(f"❌ Chrome setup failed: {e}")
        driver = None  # Prevent errors if Chrome fails

    finally:
        script_running = False
        if driver:
            driver.quit()  # ✅ Now quitting at the correct point

@app.route('/run-script', methods=['GET'])
def start_script():
    global script_running
    if script_running:
        return jsonify({"message": "Script is already running!"}), 400
    try:
        script_running = True
        thread = threading.Thread(target=run_selenium_script)
        thread.start()
        return jsonify({"message": "Script started successfully!"})
    except Exception as e:
        script_running = False
        return jsonify({"error": f"Failed to start script: {str(e)}"}), 500

@app.route('/status', methods=['GET'])
def check_status():
    return jsonify({"script_running": script_running, "status": "Running" if script_running else "Idle"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)

