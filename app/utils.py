import os
import pandas as pd
from werkzeug.utils import secure_filename
from .models import db, HVACDevice

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'

def process_csv(file_path):
    """Process a CSV file and add entries to the database"""
    try:
        # Read the CSV file
        df = pd.read_csv(file_path)
        
        # Check for required columns
        required_columns = ['manufacturer', 'market_entry_year', 'device_type', 
                           'power_rating_kw', 'airflow_volume_m3h']
        
        for col in required_columns:
            if col not in df.columns:
                return False, f"Required column '{col}' is missing from CSV file"
        
        # Process each row
        success_count = 0
        error_count = 0
        
        for _, row in df.iterrows():
            try:
                # Create a new device from the CSV data
                device = HVACDevice(
                    manufacturer=row.get('manufacturer'),
                    market_entry_year=int(row.get('market_entry_year')),
                    device_type=row.get('device_type'),
                    power_rating_kw=float(row.get('power_rating_kw')),
                    airflow_volume_m3h=float(row.get('airflow_volume_m3h')),
                    eer=float(row.get('eer')) if pd.notna(row.get('eer')) else None,
                    seer=float(row.get('seer')) if pd.notna(row.get('seer')) else None,
                    sepr=float(row.get('sepr')) if pd.notna(row.get('sepr')) else None,
                    heat_recovery_rate=float(row.get('heat_recovery_rate')) if pd.notna(row.get('heat_recovery_rate')) else None,
                    fan_performance=float(row.get('fan_performance')) if pd.notna(row.get('fan_performance')) else None,
                    temperature_range=row.get('temperature_range') if pd.notna(row.get('temperature_range')) else None,
                    noise_level_dba=float(row.get('noise_level_dba')) if pd.notna(row.get('noise_level_dba')) else None,
                    price_currency=row.get('price_currency') if pd.notna(row.get('price_currency')) else None,
                    price_amount=float(row.get('price_amount')) if pd.notna(row.get('price_amount')) else None,
                    units_sold_year=int(row.get('units_sold_year')) if pd.notna(row.get('units_sold_year')) else None,
                    units_sold_count=int(row.get('units_sold_count')) if pd.notna(row.get('units_sold_count')) else None,
                    data_source=row.get('data_source') if pd.notna(row.get('data_source')) else None
                )
                
                db.session.add(device)
                success_count += 1
            except Exception as e:
                error_count += 1
                print(f"Error processing row: {e}")
        
        db.session.commit()
        return True, f"Successfully imported {success_count} devices with {error_count} errors."
        
    except Exception as e:
        return False, f"Error processing CSV file: {str(e)}"