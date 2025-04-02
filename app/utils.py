# app/utils.py
import os
import pandas as pd
from werkzeug.utils import secure_filename
from .models import db, HVACDevice
import math # For checking nan
from datetime import date # Import date

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'

# Helper function for safe integer conversion
def safe_int_convert(value):
    if pd.isna(value):
        return None
    try:
        # Try converting to float first (handles "2020.0"), then to int
        return int(float(value))
    except (ValueError, TypeError):
        # If conversion fails, return None or handle as an error
        return None # Or raise an exception if invalid data should stop the row


def safe_date_convert(value):
    if pd.isna(value):
        return None
    try:
        # errors='coerce' will return NaT (Not a Time) for invalid formats
        dt = pd.to_datetime(value, errors='coerce')
        # Convert NaT to None, otherwise return the date part
        result = dt.date() if pd.notna(dt) else None
        return result
    except Exception as e: # Catch any other unexpected errors
        print(f"DEBUG: Exception during date conversion for '{value}': {e}")
        return None


def process_csv(file_path):
    # ... (rest of the process_csv function remains the same as the last version) ...
    # Make sure it uses safe_date_convert for the 'market_entry' field
    # and raises the ValueError if market_entry_date is None.
    # ...
    try:

        na_values_list = ['NULL', 'Null', 'null', '', '#N/A', '#N/A N/A', '#NA', '-1.#IND', '-1.#QNAN', '-NaN', '-nan', '1.#IND', '1.#QNAN', '<NA>', 'N/A', 'NA', 'NaN', 'None', 'nan', 'none']
        df = pd.read_csv(file_path, low_memory=False, na_values=na_values_list, keep_default_na=True)
        df.columns = map(str.lower, df.columns)
        # Update standard and required columns list
        standard_columns = {
            'manufacturer', 'market_entry', 'device_type', # Changed from market_entry_year
            'power_rating_kw', 'airflow_volume_m3h', 'eer', 'seer', 'sepr',
            'heat_recovery_rate', 'fan_performance', 'temperature_range',
            'noise_level_dba', 'price_currency', 'price_amount',
            'units_sold_year', 'units_sold_count', 'data_source', 'power_rating_kw', 'airflow_volume_m3h'
        }
        required_columns = {
            'manufacturer', 'market_entry', 'device_type', # Changed from market_entry_year
        }

        # Check for required columns
        missing_required = required_columns - set(df.columns)
        if missing_required:
            return False, f"Required column(s) {missing_required} are missing from CSV file"

        custom_column_names = [col for col in df.columns if col not in standard_columns]

        success_count = 0
        error_count = 0
        errors = []

        print("Starting CSV processing loop...") # Add start message

        for index, row in df.iterrows():
            try:
                # Use safe_date_convert for market_entry
                device_type = row.get('device_type')
                manufacturer = row.get('manufacturer')
                market_entry_raw = row.get('market_entry')

                if pd.isna(device_type):
                    raise ValueError("device_type is missing")
                if pd.isna(manufacturer):
                    raise ValueError("manufacturer is missing")
                if pd.isna(market_entry_raw):
                     raise ValueError("market_entry is missing")

                market_entry_date = safe_date_convert(market_entry_raw)
                if market_entry_date is None: # Check conversion result
                     raise ValueError("market_entry has an invalid date format")
                
                device_data = {
                    'manufacturer': str(manufacturer).strip(),
                    'market_entry': market_entry_date,
                    'device_type': str(device_type).strip(),
                    'power_rating_kw': float(row.get('power_rating_kw')) if pd.notna(row.get('power_rating_kw')) else None,
                    'airflow_volume_m3h': float(row.get('airflow_volume_m3h')) if pd.notna(row.get('airflow_volume_m3h')) else None,
                    'eer': float(row.get('eer')) if pd.notna(row.get('eer')) else None,
                    'seer': float(row.get('seer')) if pd.notna(row.get('seer')) else None,
                    'sepr': float(row.get('sepr')) if pd.notna(row.get('sepr')) else None,
                    'heat_recovery_rate': float(row.get('heat_recovery_rate')) if pd.notna(row.get('heat_recovery_rate')) else None,
                    'fan_performance': float(row.get('fan_performance')) if pd.notna(row.get('fan_performance')) else None,
                    'temperature_range': str(row.get('temperature_range')) if pd.notna(row.get('temperature_range')) else None,
                    'noise_level_dba': float(row.get('noise_level_dba')) if pd.notna(row.get('noise_level_dba')) else None,
                    'price_currency': str(row.get('price_currency')) if pd.notna(row.get('price_currency')) else None,
                    'price_amount': float(row.get('price_amount')) if pd.notna(row.get('price_amount')) else None,
                    'data_source': str(row.get('data_source')) if pd.notna(row.get('data_source')) else None
                }


                # --- Custom fields logic ---
                custom_data = {}
                for col_name in custom_column_names:
                    value = row.get(col_name)
                    if pd.notna(value): # Only add non-empty values
                        if isinstance(value, bool):
                           custom_data[col_name] = value
                        elif isinstance(value, (int, float)):
                           if not math.isnan(value):
                               custom_data[col_name] = value
                        elif isinstance(value, str):
                           custom_data[col_name] = value.strip()
                        else:
                            try:
                                if hasattr(value, 'item'):
                                     custom_data[col_name] = value.item()
                                else:
                                     custom_data[col_name] = str(value)
                            except Exception:
                                custom_data[col_name] = str(value)
                device_data['custom_fields'] = custom_data if custom_data else None
                device = HVACDevice(**device_data)
                db.session.add(device)
                db.session.commit()
                success_count += 1 # Increment only if add is successful before potential commit failure

            except Exception as e:
                db.session.rollback() # Rollback potential add for this row
                error_count += 1
                errors.append(f"Row {index + 2}: {e}")
                # Keep console log minimal for many errors, or add conditional logging
                # print(f"Error processing row {index + 2}: {e}")

        print(f"Finished processing loop. Success count (pre-commit): {success_count}, Error count: {error_count}")

        if error_count == 0 and success_count > 0:
             message = f"Successfully committed {success_count} devices."
        elif success_count > 0 and error_count > 0:
             message = f"Import finished. Successfully committed: {success_count}, Rows skipped due to errors: {error_count}."
        elif success_count == 0 and error_count > 0:
             message = f"Import finished. No devices committed. Rows skipped due to errors: {error_count}."
        else: # success_count == 0 and error_count == 0
             message = "Import finished. No data found or processed in the CSV."

        if error_count > 0 and errors:
            error_preview = '; '.join(errors[:5])
            if len(errors) > 5: error_preview += '...'
            message += f" Example errors: {error_preview}"

        # Return True as the process itself completed, message indicates outcome
        return True, message

    except pd.errors.EmptyDataError:
         print("CSV file is empty.")
         return False, "CSV file is empty."
    except Exception as e:
         # Catch potential errors during file reading or initial setup
         print(f"Critical error during CSV read or setup: {e}")
         # No explicit rollback needed here as session likely wasn't used yet, but doesn't hurt
         try:
             db.session.rollback()
         except: # Ignore rollback errors if session wasn't active
             pass
         return False, f"Error reading or processing CSV file: {str(e)}"