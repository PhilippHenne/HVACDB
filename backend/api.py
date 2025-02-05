      
from flask import Blueprint, request, jsonify
from .database import db, HvacDevice
import pandas as pd

api_bp = Blueprint('api', __name__)

@api_bp.route('/devices', methods=['GET'])
def get_devices():
    devices = HvacDevice.query.all()
    device_list = [{"id": device.id, "manufacturer": device.manufacturer, "device_type": device.device_type} for device in devices] # Example data
    return jsonify(devices=device_list)

@api_bp.route('/upload-csv', methods=['POST'])
def upload_csv():
    if 'csv_file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    file = request.files['csv_file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
    if file:
        try:
            df = pd.read_csv(file)
            # Basic validation and data insertion (needs more robust implementation)
            for index, row in df.iterrows():
                new_device = HvacDevice(
                    manufacturer=row['manufacturer'], # Assuming CSV headers match column names
                    market_entry_year=row['market_entry_year'],
                    device_type=row['device_type'],
                    power_rating_kw=row['power_rating_kw'],
                    airflow_volume_m3h=row['airflow_volume_m3h'],
                    # ... map other columns as needed, handle missing optional columns ...
                )
                db.session.add(new_device)
            db.session.commit()
            return jsonify({'message': 'CSV uploaded and data inserted successfully'}), 201
        except Exception as e:
            db.session.rollback() # Rollback in case of error during insertion
            return jsonify({'message': 'Error processing CSV', 'error': str(e)}), 500
    return jsonify({'message': 'Something went wrong'}), 500

# Add more API endpoints for querying, data analysis etc.