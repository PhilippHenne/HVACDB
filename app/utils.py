# app/utils.py
import os
import pandas as pd
from werkzeug.utils import secure_filename
from .models import db, HVACDevice, MODEL_MAP, AirConditioner, ResidentialVentilationUnit
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


def process_csv(file_path, target_device_type_str):
    """
    Process CSV for a specific device type using inheritance models.

    Args:
        file_path (str): Path to the CSV file.
        target_device_type_str (str): The polymorphic identity string (e.g., 'air_conditioner').
    """
    ModelClass = MODEL_MAP.get(target_device_type_str)
    if not ModelClass:
        return False, f"Invalid target device type '{target_device_type_str}' provided for CSV processing."

    try:
        na_values_list = ['NULL', 'Null', 'null', '', '#N/A', 'N/A', 'NA', 'NaN', 'None', 'nan', 'none']
        df = pd.read_csv(file_path, low_memory=False, na_values=na_values_list, keep_default_na=True)
        df.columns = map(str.lower, df.columns)

        # Define required COMMON fields first
        required_common_columns = {
            'manufacturer', 'market_entry',
        }
        # Define required specific fields based on type (examples)
        required_specific_columns = {}
        # if target_device_type_str == 'air_conditioner':
        #     required_specific_columns = {'eer', 'seer'} # Add required AC fields here
        # elif target_device_type_str == 'heat_pump':
        #     required_specific_columns = {'sepr'} # Add required HP fields here

        all_required = required_common_columns.union(required_specific_columns)
        missing_required = all_required - set(df.columns)
        if missing_required:
            return False, f"Required column(s) {', '.join(missing_required)} for type '{target_device_type_str}' are missing from CSV."


        success_count = 0
        error_count = 0
        errors = []
        print(f"Starting CSV processing loop for type {target_device_type_str} (committing per row)...")

        for index, row in df.iterrows():
            try:
                # --- Data Extraction and Validation for Common Fields ---
                manufacturer = row.get('manufacturer')
                market_entry_raw = row.get('market_entry')
                market_exit_raw = row.get('market_exit') 
                if pd.isna(manufacturer): raise ValueError("manufacturer is missing")
                if pd.isna(market_entry_raw): raise ValueError("market_entry is missing")

                market_entry_date = safe_date_convert(market_entry_raw)
                if market_entry_date is None: raise ValueError("market_entry has an invalid date format")
                market_exit_date = safe_date_convert(market_exit_raw) 
                # Prepare common data dict
                common_data = {
                    'manufacturer': str(manufacturer).strip(),
                    'market_entry': market_entry_date,
                    'market_exit': market_exit_date,
                    'noise_level_dba': float(row.get('noise_level_dba')) if pd.notna(row.get('noise_level_dba')) else None,
                    'price_currency': str(row.get('price_currency')).strip() if pd.notna(row.get('price_currency')) else None,
                    'price_amount': float(row.get('price_amount')) if pd.notna(row.get('price_amount')) else None,
                    'data_source': str(row.get('data_source')).strip() if pd.notna(row.get('data_source')) else None,
                    'device_type': target_device_type_str, # Set discriminator from function arg
                }

                # --- Data Extraction and Validation for Specific Fields ---
                specific_data = {}
                # Populate specific_data based on target_device_type_str
                # Need checks for required specific fields here too if defined above
                if target_device_type_str == 'air_conditioner':
                    specific_data['eer'] = float(row.get('eer')) if pd.notna(row.get('eer')) else None
                    specific_data['seer'] = float(row.get('seer')) if pd.notna(row.get('seer')) else None
                    specific_data['rated_power_cooling_kw'] = float(row.get('rated_power_cooling_kw')) if pd.notna(row.get('rated_power_cooling_kw')) else None
                    specific_data['energy_class_cooling'] = str(row.get('energy_class_cooling')) if pd.notna(row.get('energy_class_cooling')) else None
                    specific_data['design_load_cooling_kw'] = float(row.get('design_load_cooling_kw')) if pd.notna(row.get('design_load_cooling_kw')) else None
                    specific_data['annual_consumption_cooling_kwh'] = float(row.get('annual_consumption_cooling_kwh')) if pd.notna(row.get('annual_consumption_cooling_kwh')) else None
                    specific_data['rated_power_heating_kw'] = float(row.get('rated_power_heating_kw')) if pd.notna(row.get('rated_power_heating_kw')) else None
                    specific_data['cop_standard'] = float(row.get('cop_standard')) if pd.notna(row.get('cop_standard')) else None
                    specific_data['scop_average'] = float(row.get('scop_average')) if pd.notna(row.get('scop_average')) else None
                    specific_data['energy_class_heating_average'] = str(row.get('energy_class_heating_average')) if pd.notna(row.get('energy_class_heating_average')) else None
                    specific_data['design_load_heating_average_kw'] = float(row.get('design_load_heating_average_kw')) if pd.notna(row.get('design_load_heating_average_kw')) else None
                    specific_data['annual_consumption_heating_average_kwh'] = float(row.get('annual_consumption_heating_average_kwh')) if pd.notna(row.get('annual_consumption_heating_average_kwh')) else None
                    specific_data['scop_warm'] = float(row.get('scop_warm')) if pd.notna(row.get('scop_warm')) else None
                    specific_data['energy_class_heating_warm'] = str(row.get('energy_class_heating_warm')) if pd.notna(row.get('energy_class_heating_warm')) else None
                    specific_data['design_load_heating_warm_kw'] = float(row.get('design_load_heating_warm_kw')) if pd.notna(row.get('design_load_heating_warm_kw')) else None
                    specific_data['scop_cold'] = float(row.get('scop_cold')) if pd.notna(row.get('scop_cold')) else None
                    specific_data['energy_class_heating_cold'] = str(row.get('energy_class_heating_cold')) if pd.notna(row.get('energy_class_heating_cold')) else None
                    specific_data['design_load_heating_cold_kw'] = float(row.get('design_load_heating_cold_kw')) if pd.notna(row.get('design_load_heating_cold_kw')) else None
                    specific_data['refrigerant_type'] = str(row.get('refrigerant_type')) if pd.notna(row.get('refrigerant_type')) else None
                    specific_data['refrigerant_gwp'] = int(row.get('refrigerant_gwp')) if pd.notna(row.get('refrigerant_gwp')) else None
                    specific_data['noise_level_outdoor_cooling_db'] = float(row.get('noise_level_outdoor_cooling_db')) if pd.notna(row.get('noise_level_outdoor_cooling_db')) else None
                    # Add validation for required AC specific fields if necessary
                elif target_device_type_str == 'heat_pump':
                    specific_data['sepr'] = float(row.get('sepr')) if pd.notna(row.get('sepr')) else None
                elif target_device_type_str == 'residential_ventilation_unit':
                     specific_data = {
                        'maximumflowrate': pd.to_numeric(row.get('maximumflowrate'), errors='coerce'),
                        'referenceflowrate': pd.to_numeric(row.get('referenceflowrate'), errors='coerce'),
                        'referencepressuredifference': pd.to_numeric(row.get('referencepressuredifference'), errors='coerce'),
                        'typology': str(row.get('typology')).strip() if pd.notna(row.get('typology')) else None,
                        'heatrecoverysystem': str(row.get('heatrecoverysystem')).strip() if pd.notna(row.get('heatrecoverysystem')) else None,
                        'thermalefficiencyheatrecovery': pd.to_numeric(row.get('thermalefficiencyheatrecovery'), errors='coerce'),
                        'specificpowerinput': pd.to_numeric(row.get('specificpowerinput'), errors='coerce'),
                        'fandrivepowerinput': pd.to_numeric(row.get('fandrivepowerinput'), errors='coerce'),
                        'drivetype': str(row.get('drivetype')).strip() if pd.notna(row.get('drivetype')) else None,
                        'ductedunit': bool(row.get('ductedunit')) if pd.notna(row.get('ductedunit')) else None, # Attempt bool conversion
                        'controltypology': str(row.get('controltypology')).strip() if pd.notna(row.get('controltypology')) else None,
                        'specificenergyconsumptionwarm': pd.to_numeric(row.get('specificenergyconsumptionwarm'), errors='coerce'),
                        'specificenergyconsumptionaverage': pd.to_numeric(row.get('specificenergyconsumptionaverage'), errors='coerce'),
                        'specificenergyconsumptioncold': pd.to_numeric(row.get('specificenergyconsumptioncold'), errors='coerce'),
                        'annualheatingsavedaverageclimate': pd.to_numeric(row.get('annualheatingsavedaverageclimate'), errors='coerce'),
                        'energyclass': str(row.get('energyclass')).strip() if pd.notna(row.get('energyclass')) else None,
                        'maximuminternalleakagerate': pd.to_numeric(row.get('maximuminternalleakagerate'), errors='coerce'),
                        'maximumexternalleakagerate': pd.to_numeric(row.get('maximumexternalleakagerate'), errors='coerce'),
                    }

                # --- Custom fields ---
                custom_data = {}
                custom_column_names = [col for col in df.columns if col not in required_common_columns and col not in specific_data and col not in {'device_type'}] # Approximate logic
                for col_name in custom_column_names:
                    value = row.get(col_name)
                    if pd.notna(value):
                       # ... (existing custom field processing logic) ...
                       if isinstance(value, bool): custom_data[col_name] = value
                       elif isinstance(value, (int, float)):
                           if not math.isnan(value): custom_data[col_name] = value
                       elif isinstance(value, str): custom_data[col_name] = value.strip()
                       else:
                           try:
                               if hasattr(value, 'item'): custom_data[col_name] = value.item()
                               else: custom_data[col_name] = str(value)
                           except Exception: custom_data[col_name] = str(value)


                # Instantiate the correct subclass
                device = ModelClass(**common_data, **specific_data, custom_fields=custom_data if custom_data else None)
                db.session.add(device)
                db.session.commit() # Commit per row
                success_count += 1

            except (ValueError, TypeError) as e:
                db.session.rollback()
                error_count += 1
                errors.append(f"Row {index + 2}: {e}")
            except Exception as e:
                 db.session.rollback()
                 error_count += 1
                 errors.append(f"Row {index + 2}: Unexpected error - {e}")
                 print(f"Unexpected error processing row {index + 2}: {e}")

        # ... (Final message construction - same as before) ...
        print(f"Finished processing loop for {target_device_type_str}. Committed: {success_count}, Errors: {error_count}")
        # ... return message ...
        if error_count == 0 and success_count > 0: message = f"Successfully committed {success_count} devices of type '{target_device_type_str}'."
        # ...(copy rest of message logic)...
        elif success_count > 0 and error_count > 0: message = f"Import finished for '{target_device_type_str}'. Committed: {success_count}, Rows skipped: {error_count}."
        elif success_count == 0 and error_count > 0: message = f"Import finished for '{target_device_type_str}'. No devices committed. Rows skipped: {error_count}."
        else: message = f"Import finished for '{target_device_type_str}'. No data found or processed."
        if error_count > 0 and errors:
            error_preview = '; '.join(errors[:5]); message += f" Example errors: {error_preview}{'...' if len(errors) > 5 else ''}"
        return True, message


    except pd.errors.EmptyDataError:
         return False, f"CSV file for type '{target_device_type_str}' is empty."
    except Exception as e:
         db.session.rollback()
         return False, f"Error reading/processing CSV for type '{target_device_type_str}': {str(e)}"