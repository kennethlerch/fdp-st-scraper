from flask import Flask, jsonify, request
import threading
import os
import json
import time
from FDPtoSTSCRIPT import run_selenium_script  # ✅ Import the scraping function

app = Flask(__name__)

# Global variable to track script status
script_running = False

def run_script_wrapper():
    """ Wrapper to run the Selenium script and update status """
    global script_running
    script_running = True
    try:
        run_selenium_script()  # ✅ Calls the function from FDPtoSTSCRIPT.py
    finally:
        script_running = False

@app.route('/run-script', methods=['GET'])
def start_script():
    """API Endpoint to start the Selenium script"""
    global script_running
    if script_running:
        return jsonify({"message": "Script is already running!"}), 400

    thread = threading.Thread(target=run_script_wrapper)
    thread.start()

    return jsonify({"message": "Script started successfully!"})

@app.route('/', methods=['GET'])
def home():
    """API Endpoint for the root URL"""
    return jsonify({"message": "Service is running!"})

@app.route('/status', methods=['GET'])
def check_status():
    """API Endpoint to check if the script is running"""
    return jsonify({
        "script_running": script_running,
        "status": "Running" if script_running else "Idle"
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))  # Use Render's assigned port
    app.run(host="0.0.0.0", port=port, debug=True)

