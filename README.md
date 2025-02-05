      
# HVAC Device Database for Energy Efficiency Analysis

This project aims to build a database for collecting data on HVAC devices to analyze energy efficiency trends over time and understand the current market state.

## Technologies Used:

* **Backend:** Python Flask
* **Database:** PostgreSQL
* **Frontend:** Basic HTML, CSS, JavaScript

## Setup Instructions:

**1. Prerequisites:**

* **Python 3.x:** Make sure you have Python 3 installed.
* **pip:** Python package installer (usually comes with Python).
* **PostgreSQL:** Install PostgreSQL on your system. You'll need to create a database and user for this project.
* **Virtual Environment (Recommended):** It's highly recommended to use a virtual environment to manage Python dependencies.

**2. Backend Setup:**

* Navigate to the `backend` directory: `cd backend`
* Create a virtual environment (if you don't have `virtualenv` installed, run `pip install virtualenv`):
  ```bash
  python -m venv venv
  # or
  virtualenv venv

**3. Using the DB:**
* Use curl to interact with the local DB
* Example create request:
  ```curl -X POST -H "Content-Type: application/json" -d '{
    "manufacturer": "Test Manufacturer",
    "market_entry_year": 2023,
    "device_type": "Split AC",
    "power_rating_kw": 3.5,
    "airflow_volume_m3h": 500,
    "eer": 3.2
  }' http://127.0.0.1:5000/api/devices
* Example update request:
  ```curl -X PUT -H "Content-Type: application/json" -d '{
    "eer": 3.5,
    "noise_level_dba": 50
  }' http://127.0.0.1:5000/api/devices/1
* Example delete request:
  ```curl -X DELETE http://127.0.0.1:5000/api/devices/1

    