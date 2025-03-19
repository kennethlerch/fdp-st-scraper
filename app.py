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
    print("🚀 Selenium script started!")  # Debug log

    try:
        print("🔄 Installing Chrome and Chromedriver...")  # Debug log
        
        # ✅ Install Chrome manually before running Selenium
        chrome_url = "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
        chromedriver_url = "https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip"

        os.system(f"wget {chrome_url} -O /tmp/chrome.deb")
        print("📥 Chrome downloaded!")  # Debug log
        
        os.system("dpkg -i /tmp/chrome.deb || apt-get -f install -y")
        print("✅ Chrome installed!")  # Debug log
        
        os.system(f"wget {chromedriver_url} -O /tmp/chromedriver.zip")
        print("📥 Chromedriver downloaded!")  # Debug log
        
        os.system("unzip /tmp/chromedriver.zip -d /tmp/")  # ✅ Extract to /tmp/
        print("✅ Chromedriver extracted!")  # Debug log
        
        os.system("chmod +x /tmp/chromedriver")  # ✅ Ensure it's executable
        print("🔧 Chromedriver permissions set!")  # Debug log
        

        print("🔄 Setting up WebDriver options...")  # Debug log
        chrome_path = "/opt/google/chrome/google-chrome"  # Default path in Render
        chromedriver_path = "/tmp/chromedriver"  # Extracted Chromedriver

        options = Options()
        options.binary_location = chrome_path  # ✅ Use the pre-installed Chrome
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        print("✅ WebDriver options configured!")  # Debug log

        # ✅ Use installed chromedriver from /tmp/
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)

        # ✅ Open login page
        print("📌 Navigating to login page...")  # Debug log
        driver.get("https://pro.proconnect.com/login")
        print("🟢 Login page opened")  # Debug log
        time.sleep(10)

        try:
            # ✅ Click "Sign In" button
            print("🔄 Looking for 'Sign In' button...")  # Debug log
            sign_in_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "button-interactive"))
            )
            sign_in_button.click()
            print("✅ Clicked 'Sign In' button!")  # Debug log
            
            time.sleep(3)
        except Exception:
            print("❌ Failed to click 'Sign In' button!")

        try:
            # ✅ Enter login credentials
            print("🔄 Entering login credentials...")  # Debug log
            username_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "loginId"))
            )
            password_field = driver.find_element(By.ID, "password")
            login_button = driver.find_element(By.ID, "login-btn")

            username_field.send_keys("office@gardnerplumbingco.com")
            password_field.send_keys("Job13:14!")
            login_button.click()
            print("✅ Credentials entered, logging in...")  # Debug log
            time.sleep(10)
        except Exception:
            print("❌ Failed to enter credentials!")

        # ✅ Extract job data
        jobs_data = []
        base_url = "https://pro.proconnect.com/jobs"
        driver.get(base_url)
        time.sleep(5)
        print("✅ Jobs page loaded!")  # Debug log

        print("🔄 Fetching job list elements...")  # Debug log
        def get_job_list():
            """ Re-fetch job elements to avoid stale element errors """
            return driver.find_elements(By.XPATH, "//div[contains(@class, '_statusPill_dzcst_42') and contains(text(), 'Assign Pro')]")

        job_elements = get_job_list()
        print(f"✅ Found {len(job_elements)} job elements!")  # Debug log

        for index in range(len(job_elements)):
            try:
                print(f"🔄 Processing job {index+1}/{len(job_elements)}...")  # Debug log
                job_elements = get_job_list()
                job_status = job_elements[index]
                job_entry = job_status.find_element(By.XPATH, "./ancestor::div[contains(@data-testid, 'appointment-list-item')]")
                job_entry.click()
                time.sleep(5)
                print(f"✅ Clicked job {index+1}")  # Debug log

                def extract_text_with_js(xpath):
                    """ Extracts text using JavaScript execution """
                    try:
                        element = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, xpath))
                        )
                        text = driver.execute_script("return arguments[0].innerText;", element).strip()
                        print(f"🔹 Extracted text: {text} from {xpath}")  # Debug log
                        return text if text else "N/A"
                    except Exception:
                        print(f"⚠️ Failed to extract text from {xpath}")  # Debug log
                        return "N/A"

                # ✅ Extract Data
                print("🔄 Extracting job details...")  # Debug log
                job_service = extract_text_with_js("//div[@id='jobPage.jobDetails']//div[h6[contains(text(), 'Service:')]]").replace("Service:", "").strip()
                job_work_order = extract_text_with_js("//div[@id='jobPage.jobDetails']//div[h6[contains(text(), 'Work Order:')]]").replace("Work Order:", "").strip()
                customer_name = extract_text_with_js("//div[@id='jobPage.customerInfo']//div[h6[contains(text(), 'Name:')]]").replace("Name:", "").strip()
                customer_phone = extract_text_with_js("//div[@id='jobPage.customerInfo']//div[h6[contains(text(), 'Phone:')]]").replace("Phone:", "").strip()
                job_description = extract_text_with_js("//div[@id='jobPage.description']//div[contains(@class, 'text-body-long')]")

                appointment_date = extract_text_with_js("//div[@data-testid='jobDetail.appointmentTime']//div[1]")
                appointment_time = extract_text_with_js("//div[@data-testid='jobDetail.appointmentTime']//div[2]")

                street_address = extract_text_with_js("//div[@data-testid='address.street']")
                city_state_zip = extract_text_with_js("//div[contains(@class, '_cityStateZip')]")

                print("✅ Extracted job details!")  # Debug log

                print(f"📌 Saving job {index+1} data...")  # Debug log
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
                print(f"✅ Job {index+1} data saved!")  # Debug log

                driver.get(base_url)
                time.sleep(5)
                print("🔄 Returning to job list...")  # Debug log

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

    print("🟢 /run-script called! Starting Selenium thread...")  # Debug log
    
    try:
        script_running = True
        thread = threading.Thread(target=run_selenium_script)
        thread.start()
        return jsonify({"message": "Script started successfully!"})
    except Exception as e:
        script_running = False
        print(f"❌ Failed to start script: {e}")  # Debug log
        return jsonify({"error": f"Failed to start script: {str(e)}"}), 500

@app.route('/status', methods=['GET'])
def check_status():
    return jsonify({"script_running": script_running, "status": "Running" if script_running else "Idle"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)

