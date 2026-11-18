from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import os
import time
import csv

# Load credentials securely
email = os.getenv("PROCONNECT_EMAIL")  # Set this in your environment
password = os.getenv("PROCONNECT_PASSWORD")

# Configure WebDriver
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(options=options)

# Open Login Page
driver.get("https://pro.proconnect.com/jobs")

time.sleep(3)  # Allow time for the page to load

# Login
username = driver.find_element(By.NAME, "email")
password_field = driver.find_element(By.NAME, "password")

username.send_keys(email)
password_field.send_keys(password)
password_field.send_keys(Keys.RETURN)  # Submit form

time.sleep(5)  # Wait for login to complete

# Navigate to Jobs Page
driver.get("https://pro.proconnect.com/jobs")
time.sleep(3)

# Extract "Assign Pro" Jobs
assign_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'ASSIGN PRO')]")

job_data = []

for i, button in enumerate(assign_buttons):
    try:
        ActionChains(driver).move_to_element(button).click().perform()
        time.sleep(3)

        # Extract Job Details
        appointment_time = driver.find_element(By.ID, "jobPage.appointmentTime").text
        address = driver.find_element(By.ID, "jobPage.address").text
        customer_info = driver.find_element(By.ID, "jobPage.customerInfo").text
        job_description = driver.find_element(By.ID, "jobPage.description").text

        job_data.append([appointment_time, address, customer_info, job_description])
        print(f"Extracted Job {i+1}: {appointment_time}, {address}")

        driver.back()
        time.sleep(3)

    except Exception as e:
        print(f"Error processing job {i+1}: {e}")
        continue

# Save to CSV
with open("jobs_data.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["Appointment Time", "Address", "Customer Info", "Job Description"])
    writer.writerows(job_data)

print("Data extraction completed! CSV file saved.")
driver.quit()
