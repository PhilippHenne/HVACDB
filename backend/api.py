from flask import Blueprint, request, jsonify
from .database import db, HvacDevice
import pandas as pd

api_bp = Blueprint('api', __name__)

# --- READ ---

@api_bp.route('/devices', methods=['GET'])
def get_devices():
    """
    Get a list of all HVAC devices.
    """
    devices = HvacDevice.query.all()
    device_list = [device_to_dict(device) for device in devices]
    return jsonify(devices=device_list)

@api_bp.route('/devices/<int:device_id>', methods=['GET'])
def get_device(device_id):
    """
    Get a specific HVAC device by ID.
    """
    device = HvacDevice.query.get_or_404(device_id)
    return jsonify(device=device_to_dict(device))

# --- CREATE ---

@api_bp.route('/devices', methods=['POST'])
def create_device():
    """
    Create a new HVAC device.
    Expects device data in JSON format in the request body.
    """
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No input data provided'}), 400

    try:
        # Validate required fields
        required_fields = ['manufacturer', 'market_entry_year', 'device_type', 'power_rating_kw', 'airflow_volume_m3h']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400

        new_device = HvacDevice(
            manufacturer=data['manufacturer'],
            market_entry_year=data['market_entry_year'],
            device_type=data['device_type'],
            power_rating_kw=data['power_rating_kw'],
            airflow_volume_m3h=data['airflow_volume_m3h'],
            eer=data.get('eer'), # Use .get() for optional fields to avoid KeyError
            seer=data.get('seer'),
            sepr=data.get('sepr'),
            heat_recovery_rate=data.get('heat_recovery_rate'),
            fan_performance=data.get('fan_performance'),
            temperature_range=data.get('temperature_range'),
            noise_level_dba=data.get('noise_level_dba'),
            price_currency=data.get('price_currency'),
            price_amount=data.get('price_amount'),
            units_sold_year=data.get('units_sold_year'),
            units_sold_count=data.get('units_sold_count'),
            data_source=data.get('data_source')
        )
        db.session.add(new_device)
        db.session.commit()
        return jsonify({'message': 'Device created successfully', 'device': device_to_dict(new_device)}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error creating device', 'error': str(e)}), 500

# --- UPDATE ---

@api_bp.route('/devices/<int:device_id>', methods=['PUT'])
def update_device(device_id):
    """
    Update an existing HVAC device by ID.
    Expects updated device data in JSON format in the request body.
    """
    device = HvacDevice.query.get_or_404(device_id)
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No input data provided'}), 400

    try:
        device.manufacturer = data.get('manufacturer', device.manufacturer) # Use .get() with default value for updates
        device.market_entry_year = data.get('market_entry_year', device.market_entry_year)
        device.device_type = data.get('device_type', device.device_type)
        device.power_rating_kw = data.get('power_rating_kw', device.power_rating_kw)
        device.airflow_volume_m3h = data.get('airflow_volume_m3h', device.airflow_volume_m3h)
        device.eer = data.get('eer', device.eer)
        device.seer = data.get('seer', device.seer)
        device.sepr = data.get('sepr', device.sepr)
        device.heat_recovery_rate = data.get('heat_recovery_rate', device.heat_recovery_rate)
        device.fan_performance = data.get('fan_performance', device.fan_performance)
        device.temperature_range = data.get('temperature_range', device.temperature_range)
        device.noise_level_dba = data.get('noise_level_dba', device.noise_level_dba)
        device.price_currency = data.get('price_currency', device.price_currency)
        device.price_amount = data.get('price_amount', device.price_amount)
        device.units_sold_year = data.get('units_sold_year', device.units_sold_year)
        device.units_sold_count = data.get('units_sold_count', device.units_sold_count)
        device.data_source = data.get('data_source', device.data_source)

        db.session.commit()
        return jsonify({'message': 'Device updated successfully', 'device': device_to_dict(device)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error updating device', 'error': str(e)}), 500

# --- DELETE ---

@api_bp.route('/devices/<int:device_id>', methods=['DELETE'])
def delete_device(device_id):
    """
    Delete an HVAC device by ID.
    """
    device = HvacDevice.query.get_or_404(device_id)
    try:
        db.session.delete(device)
        db.session.commit()
        return jsonify({'message': 'Device deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error deleting device', 'error': str(e)}), 500


# --- CSV Upload (already implemented, keeping for completeness) ---

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
            db.session.rollback()
            return jsonify({'message': 'Error processing CSV', 'error': str(e)}), 500
    return jsonify({'message': 'Something went wrong'}), 500


# --- Helper function to convert HvacDevice object to dictionary ---

def device_to_dict(device):
    """
    Helper function to convert an HvacDevice object to a dictionary for JSON response.
    """
    return {
        'id': device.id,
        'manufacturer': device.manufacturer,
        'market_entry_year': device.market_entry_year,
        'device_type': device.device_type,
        'power_rating_kw': str(device.power_rating_kw), # Convert Decimal to string for JSON serialization
        'airflow_volume_m3h': str(device.airflow_volume_m3h), # Convert Decimal to string
        'eer': str(device.eer) if device.eer else None, # Handle potential None values and convert Decimal
        'seer': str(device.seer) if device.seer else None,
        'sepr': str(device.sepr) if device.sepr else None,
        'heat_recovery_rate': str(device.heat_recovery_rate) if device.heat_recovery_rate else None,
        'fan_performance': str(device.fan_performance) if device.fan_performance else None,
        'temperature_range': device.temperature_range,
        'noise_level_dba': str(device.noise_level_dba) if device.noise_level_dba else None,
        'price_currency': device.price_currency,
        'price_amount': str(device.price_amount) if device.price_amount else None,
        'units_sold_year': device.units_sold_year,
        'units_sold_count': device.units_sold_count,
        'data_source': device.data_source,
        'created_at': device.created_at.isoformat(),
        'updated_at': device.updated_at.isoformat()
    }