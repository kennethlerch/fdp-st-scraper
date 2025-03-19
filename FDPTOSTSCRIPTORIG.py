from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import time
import re
import os
import json

def run_scraper():
    """ Runs Selenium script to scrape job details, saves to Google Sheets, and returns JSON """

    results = {"success": False, "jobs_scraped": 0, "jobs": [], "error": None}

    try:
        # ✅ Setup Selenium
        options = Options()
        options.add_argument("--headless")  # ✅ Run headless mode
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
            results["error"] = "Failed to click 'Sign In' button"
            return results

        # ✅ Enter login credentials (SECURE)
        try:
            username = os.getenv("FDP_USERNAME")  # ✅ Use environment variable
            password = os.getenv("FDP_PASSWORD")  # ✅ Use environment variable

            username_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "loginId"))
            )
            password_field = driver.find_element(By.ID, "password")
            login_button = driver.find_element(By.ID, "login-btn")

            username_field.send_keys(username)
            password_field.send_keys(password)
            login_button.click()
            time.sleep(10)
        except Exception:
            results["error"] = "Failed to enter credentials"
            return results

        # ✅ Wait for jobs page to load
        try:
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except Exception:
            results["error"] = "Jobs page did not load in time"
            return results

        ### ✅ FIND "ASSIGN PRO" JOBS & CLICK TO OPEN ###
        jobs_data = []
        base_url = "https://pro.proconnect.com/jobs"

        driver.get(base_url)
        time.sleep(5)

        def get_job_list():
            """ Re-fetches the job elements to avoid stale element errors """
            return driver.find_elements(By.XPATH, "//div[contains(@class, '_statusPill_dzcst_42') and contains(text(), 'Assign Pro')]")

        job_elements = get_job_list()

        for index in range(len(job_elements)):  # ✅ Click all "Assign Pro" jobs
            try:
                job_elements = get_job_list()  # ✅ Refresh job list
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

                # ✅ Split city, state, and zip
                match = re.match(r"(.+),\s([A-Z]{2})\s(\d{5})", city_state_zip)
                if match:
                    city, state, zip_code = match.groups()
                else:
                    city, state, zip_code = "N/A", "N/A", "N/A"

                # ✅ Append Data
                job_data = {
                    "Service": job_service,
                    "Work Order": job_work_order,
                    "Name": customer_name,
                    "Phone": customer_phone,
                    "Street Address": street_address,
                    "City": city,
                    "State": state,
                    "ZIP": zip_code,
                    "Country": "US",
                    "Appointment Date": appointment_date,
                    "Appointment Time": appointment_time,
                    "Job Description": job_description
                }

                jobs_data.append(job_data)

                driver.get(base_url)  # ✅ Return to job listings
                time.sleep(5)

            except Exception as e:
                results["error"] = f"Error processing job {index+1}: {str(e)}"

        driver.quit()

        ### ✅ GOOGLE SHEETS INTEGRATION ###
        try:
            json_creds = os.getenv("GOOGLE_SERVICE_ACCOUNT")
            if not json_creds:
                raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT environment variable!")

            creds = Credentials.from_service_account_info(json.loads(json_creds))
            client = gspread.authorize(creds)

            SHEET_NAME = "AcceptedJobsFDPtoST"
            SHEET_TAB = "ASSIGNPROJOBS"

            sheet = client.open(SHEET_NAME).worksheet(SHEET_TAB)

            # ✅ Prevent duplicate work orders
            existing_jobs = sheet.get_all_records()
            existing_work_orders = {row["Work Order"] for row in existing_jobs if "Work Order" in row}

            new_jobs = [job for job in jobs_data if job["Work Order"] not in existing_work_orders]

            if new_jobs:
                new_jobs_df = pd.DataFrame(new_jobs)
                sheet.append_rows(new_jobs_df.values.tolist())
                results["success"] = True
                results["jobs_scraped"] = len(new_jobs_df)
                results["jobs"] = new_jobs
            else:
                results["error"] = "No new 'Assign Pro' jobs found"

        except Exception as e:
            results["error"] = f"Google Sheets Error: {str(e)}"

    except Exception as e:
        results["error"] = f"Unexpected error: {str(e)}"

    return results  # ✅ Returns JSON-compatible dict

if __name__ == "__main__":
    print(json.dumps(run_scraper(), indent=4))




