# app/utils.py
import os
import pandas as pd
from werkzeug.utils import secure_filename
# Assuming models.py is in the same directory or accessible via '.'
from .models import db, HVACDevice, MODEL_MAP, AirConditioner, ResidentialVentilationUnit, HeatPump, HeatPumpPerformance
import math # For checking nan
from datetime import date # Import date
import re


def allowed_file(filename):
    # Ensure this matches your desired file extensions (e.g., 'csv')
    ALLOWED_EXTENSIONS = {'csv'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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


# Helper function to safely get and convert data from a row
def get_row_value(row, col_name, data_type='string'):
    """ Safely gets a value from the row and converts it. """
    value = row.get(col_name)
    if pd.isna(value):
        return None

    try:
        if data_type == 'float':
            return float(value)
        elif data_type == 'int':
            # Use existing safe function for robustness
            return safe_int_convert(value)
        elif data_type == 'string':
            return str(value).strip()
        elif data_type == 'date':
             # Use existing safe function for robustness
            return safe_date_convert(value)
        else:
            return str(value).strip() # Default to string
    except (ValueError, TypeError):
        # print(f"Warning: Could not convert value '{value}' for column '{col_name}' to type '{data_type}'. Skipping field.")
        return None


def process_csv(file_path, target_device_type_str):
    """
    Process CSV for a specific device type using inheritance models.
    Delegates to process_heat_pump_csvs for 'heat_pump' type.

    Args:
        file_path (str): Path to the primary CSV file (e.g., base file for HP).
        target_device_type_str (str): The polymorphic identity string (e.g., 'air_conditioner', 'heat_pump').
    """
    # --- Handle Heat Pump Special Case ---
    if target_device_type_str == 'heat_pump':
        # Assume performance file has a predictable name relative to the base file
        base_filename = os.path.basename(file_path)
        perf_filename = base_filename.replace('.csv', '_performance.csv') # Example convention
        # Construct full path assuming performance file is in the same directory
        perf_file_path = os.path.join(os.path.dirname(file_path), perf_filename)
        print(f"DEBUG: Looking for performance file at: {perf_file_path}")
        if not os.path.exists(perf_file_path):
            return False, f"Heat pump import failed: Corresponding performance file '{perf_filename}' not found in upload directory."

        # Call the dedicated function
        return process_heat_pump_csvs(file_path, perf_file_path)

    # --- Original Logic for Single-File Imports (AC, RVU, etc.) ---
    ModelClass = MODEL_MAP.get(target_device_type_str)
    if not ModelClass:
        return False, f"Invalid target device type '{target_device_type_str}' provided for CSV processing."

    try:
        na_values_list = ['NULL', 'Null', 'null', '', '#N/A', 'N/A', 'NA', 'NaN', 'None', 'nan', 'none', 'undefined', 'Invalid date']
        # Use keep_default_na=False if you want to handle empty strings manually? No, keep True.
        df = pd.read_csv(file_path, low_memory=False, na_values=na_values_list, keep_default_na=True)

        # Standardize column names from CSV (lowercase, underscore spaces)
        # Do this ONCE after loading
        df.columns = [col.lower().replace(' ', '_') for col in df.columns]
        print(f"DEBUG: Columns after standardization: {df.columns.tolist()}")


        success_count = 0
        error_count = 0
        errors = []
        print(f"Starting CSV processing loop for type {target_device_type_str} (committing per row)...")

        for index, row in df.iterrows():
            try:
                # --- Data Extraction and Validation for Common Fields ---
                # Use standardized column names for row.get()
                manufacturer = get_row_value(row, 'manufacturer', 'string')
                model_identifier_base = get_row_value(row, 'model_identifier', 'string') # Base model identifier
                market_entry_date = get_row_value(row, 'market_entry', 'date')
                market_exit_date = get_row_value(row, 'market_exit', 'date')
                data_source_val = get_row_value(row, 'data_source', 'string') # Get data source from CSV

                # Basic validation
                if not manufacturer: raise ValueError("manufacturer is missing or invalid")
                if not model_identifier_base: raise ValueError("model_identifier (base) is missing or invalid")
                # Market entry might be optional depending on your data logic
                # if not market_entry_date: raise ValueError("market_entry is missing or invalid")


                # Prepare common data dict
                common_data = {
                    'manufacturer': manufacturer,
                    'model_identifier': model_identifier_base,
                    'market_entry': market_entry_date,
                    'market_exit': market_exit_date,
                    'noise_level_dba': get_row_value(row, 'noise_level_dba', 'float'), # General noise level if present
                    'price_currency': get_row_value(row, 'price_currency', 'string'),
                    'price_amount': get_row_value(row, 'price_amount', 'float'),
                    'data_source': data_source_val, # Use source from CSV if provided
                    'device_type': target_device_type_str, # Set discriminator from function arg
                }

                # --- Data Extraction and Validation for Specific Fields ---
                specific_data = {}

                if target_device_type_str == 'air_conditioner':
                    # Define expected fields for AirConditioner (use lowercase snake_case)
                    ac_fields_map = {
                        # Field Name in Model: (Column Name in CSV, Data Type)
                        'eer': ('eer', 'float'),
                        'seer': ('seer', 'float'),
                        'rated_power_cooling_kw': ('rated_power_cooling_kw', 'float'),
                        'energy_class_cooling': ('energy_class_cooling', 'string'),
                        'design_load_cooling_kw': ('design_load_cooling_kw', 'float'),
                        'annual_consumption_cooling_kwh': ('annual_consumption_cooling_kwh', 'float'),
                        'rated_power_heating_kw': ('rated_power_heating_kw', 'float'),
                        'cop_standard': ('cop_standard', 'float'),
                        'scop_average': ('scop_average', 'float'),
                        'energy_class_heating_average': ('energy_class_heating_average', 'string'),
                        'design_load_heating_average_kw': ('design_load_heating_average_kw', 'float'),
                        'annual_consumption_heating_average_kwh': ('annual_consumption_heating_average_kwh', 'float'),
                        'scop_warm': ('scop_warm', 'float'),
                        'energy_class_heating_warm': ('energy_class_heating_warm', 'string'),
                        'design_load_heating_warm_kw': ('design_load_heating_warm_kw', 'float'),
                        'annual_consumption_heating_warm_kwh': ('annual_consumption_heating_warm_kwh', 'float'),
                        'scop_cold': ('scop_cold', 'float'),
                        'energy_class_heating_cold': ('energy_class_heating_cold', 'string'),
                        'design_load_heating_cold_kw': ('design_load_heating_cold_kw', 'float'),
                        'annual_consumption_heating_cold_kwh': ('annual_consumption_heating_cold_kwh', 'float'),
                        'refrigerant_type': ('refrigerant_type', 'string'),
                        'refrigerant_gwp': ('refrigerant_gwp', 'int'),
                        'noise_level_outdoor_cooling_db': ('noise_level_outdoor_cooling_db', 'float'),
                        'eta_s_cooling_percent': ('eta_s_cooling_percent', 'float'), 
                        'eta_s_heating_average_percent': ('eta_s_heating_average_percent', 'float'), 
                        'eta_s_heating_warm_percent': ('eta_s_heating_warm_percent', 'float'), 
                        'eta_s_heating_cold_percent': ('eta_s_heating_cold_percent', 'float'), 
                        'pc_cooling_cond_b_kw': ('pc_cooling_cond_b_kw', 'float'), 
                        'eer_cooling_cond_b': ('eer_cooling_cond_b', 'float'), 
                        'pc_cooling_cond_c_kw': ('pc_cooling_cond_c_kw', 'float'), 
                        'eer_cooling_cond_c': ('eer_cooling_cond_c', 'float'), 
                        'pc_cooling_cond_d_kw': ('pc_cooling_cond_d_kw', 'float'), 
                        'eer_cooling_cond_d': ('eer_cooling_cond_d', 'float'), 
                        'ph_heating_cond_a_kw': ('ph_heating_cond_a_kw', 'float'), 
                        'cop_heating_cond_a': ('cop_heating_cond_a', 'float'), 
                        'ph_heating_cond_b_kw': ('ph_heating_cond_b_kw', 'float'), 
                        'cop_heating_cond_b': ('cop_heating_cond_b', 'float'), 
                        'ph_heating_cond_c_kw': ('ph_heating_cond_c_kw', 'float'), 
                        'cop_heating_cond_c': ('cop_heating_cond_c', 'float'), 
                        'ph_heating_cond_d_kw': ('ph_heating_cond_d_kw', 'float'), 
                        'cop_heating_cond_d': ('cop_heating_cond_d', 'float'), 
                        'tol_temp_heating': ('tol_temp_heating', 'float'), 
                        'ph_heating_tol_kw': ('ph_heating_tol_kw', 'float'), 
                        'cop_heating_tol': ('cop_heating_tol', 'float'), 
                        'tbiv_temp_heating': ('tbiv_temp_heating', 'float'), 
                        'ph_heating_tbiv_kw': ('ph_heating_tbiv_kw', 'float'), 
                        'cop_heating_tbiv': ('cop_heating_tbiv', 'float'), 
                        'power_standby_cooling_kw': ('power_standby_cooling_kw', 'float'), 
                        'power_off_cooling_kw': ('power_off_cooling_kw', 'float'), 
                        'power_standby_heating_kw': ('power_standby_heating_kw', 'float'), 
                        'power_off_heating_kw': ('power_off_heating_kw', 'float'), 
                        'noise_level_indoor_cooling_db': ('noise_level_indoor_cooling_db', 'float'), 
                        'noise_level_outdoor_heating_db': ('noise_level_outdoor_heating_db', 'float'), 
                        'noise_level_indoor_heating_db': ('noise_level_indoor_heating_db', 'float'), 
                        'capacity_control_type': ('capacity_control_type', 'string'), 
                        'degradation_coeff_cooling_cd': ('degradation_coeff_cooling_cd', 'float'), 
                        # 'data_source' field removed from specific map, handled in common_data
                    }

                    for model_field, (csv_col, dtype) in ac_fields_map.items():
                        # Use standardized csv_col name for lookup
                        specific_data[model_field] = get_row_value(row, csv_col.lower(), dtype)


                elif target_device_type_str == 'residential_ventilation_unit':
                    # Define expected fields for RVU (use lowercase snake_case)
                    rvu_fields_map = {
                        'maximumflowrate': ('maximumflowrate', 'float'),
                        'referenceflowrate': ('referenceflowrate', 'float'),
                        'referencepressuredifference': ('referencepressuredifference', 'float'),
                        'typology': ('typology', 'string'),
                        'heatrecoverysystem': ('heatrecoverysystem', 'string'),
                        'thermalefficiencyheatrecovery': ('thermalefficiencyheatrecovery', 'float'),
                        'specificpowerinput': ('specificpowerinput', 'float'),
                        'fandrivepowerinput': ('fandrivepowerinput', 'float'),
                        'drivetype': ('drivetype', 'string'),
                        'ductedunit': ('ductedunit', 'string'),
                        'controltypology': ('controltypology', 'string'),
                        'specificenergyconsumptionwarm': ('specificenergyconsumptionwarm', 'float'),
                        'specificenergyconsumptionaverage': ('specificenergyconsumptionaverage', 'float'),
                        'specificenergyconsumptioncold': ('specificenergyconsumptioncold', 'float'),
                        'annualheatingsavedaverageclimate': ('annualheatingsavedaverageclimate', 'float'),
                        'annualheatingsavedwarmclimate': ('annualheatingsavedwarmclimate', 'float'),
                        'annualheatingsavedcoldclimate': ('annualheatingsavedcoldclimate', 'float'),
                        'energyclass': ('energyclass', 'string'),
                        'maximuminternalleakagerate': ('maximuminternalleakagerate', 'float'),
                        'maximumexternalleakagerate': ('maximumexternalleakagerate', 'float'),
                    }

                    for model_field, (csv_col, dtype) in rvu_fields_map.items():
                        # Use standardized csv_col name for lookup
                        specific_data[model_field] = get_row_value(row, csv_col.lower(), dtype)

                    # Handle potential transformation for heatrecoverysystem if needed
                    if specific_data.get('heatrecoverysystem') is not None:
                         # Example: Ensure uppercase and default to 'NONE' if empty after strip
                        hr_val = specific_data['heatrecoverysystem'].upper()
                        specific_data['heatrecoverysystem'] = hr_val if hr_val else 'NONE'
                    else:
                         specific_data['heatrecoverysystem'] = 'NONE'


                # --- Custom fields ---
                # Identify columns NOT part of common_data or specific_data for this type
                # Get list of keys from the relevant fields map
                if target_device_type_str == 'air_conditioner':
                    specific_keys = set(ac_fields_map.keys())
                elif target_device_type_str == 'residential_ventilation_unit':
                    specific_keys = set(rvu_fields_map.keys())
                else:
                    specific_keys = set() # Add other types if needed

                known_db_cols = set(common_data.keys()) | specific_keys
                custom_data = {}
                for csv_col_name_std in df.columns: # Iterate using standardized CSV column names
                    # Map standardized name back to model/DB attribute name (usually same if snake_case)
                    target_attr_name = csv_col_name_std
                    if target_attr_name not in known_db_cols:
                        # Get value using standardized name from row object
                        value = row.get(csv_col_name_std)
                        if pd.notna(value):
                            # Basic serialization for JSON (can be expanded)
                            if isinstance(value, (bool, int, float, str)):
                                custom_data[target_attr_name] = value
                            elif isinstance(value, date):
                                custom_data[target_attr_name] = value.isoformat()
                            else: # Catch numpy types, etc.
                                try:
                                    if hasattr(value, 'item'): custom_data[target_attr_name] = value.item()
                                    elif hasattr(value, 'tolist'): custom_data[target_attr_name] = value.tolist() # Handle lists/arrays if needed
                                    else: custom_data[target_attr_name] = str(value)
                                except Exception:
                                    custom_data[target_attr_name] = str(value) # Fallback

                # Instantiate the correct subclass
                # Make sure specific_data contains values for all defined attributes in the model class,
                # even if they are None from the CSV.
                device = ModelClass(**common_data, **specific_data, custom_fields=custom_data if custom_data else None)
                db.session.add(device)
                db.session.commit() # Commit per row
                success_count += 1

            except (ValueError, TypeError) as e:
                db.session.rollback()
                error_count += 1
                errors.append(f"Row {index + 2}: Validation Error - {e}")
                # print(f"Validation error processing row {index + 2}: {e}") # Less verbose
            except Exception as e:
                 db.session.rollback()
                 error_count += 1
                 errors.append(f"Row {index + 2}: Unexpected error - {type(e).__name__} {e}")
                 print(f"Unexpected error processing row {index + 2}: {type(e).__name__} {e}") # More info
                 import traceback
                 traceback.print_exc() # Full traceback for debugging

        print(f"Finished processing loop for {target_device_type_str}. Committed: {success_count}, Errors: {error_count}")

        # Construct summary message (same as before)
        if error_count == 0 and success_count > 0: message = f"Successfully committed {success_count} devices of type '{target_device_type_str}'."
        elif success_count > 0 and error_count > 0: message = f"Import finished for '{target_device_type_str}'. Committed: {success_count}, Rows skipped: {error_count}."
        elif success_count == 0 and error_count > 0: message = f"Import finished for '{target_device_type_str}'. No devices committed. Rows skipped: {error_count}."
        else: message = f"Import finished for '{target_device_type_str}'. No data found or processed."
        if error_count > 0 and errors:
            error_preview = '; '.join(errors[:5]); message += f" Example errors: {error_preview}{'...' if len(errors) > 5 else ''}"
        return True, message

    except pd.errors.EmptyDataError:
         return False, f"CSV file for type '{target_device_type_str}' is empty."
    except KeyError as e:
         db.session.rollback()
         return False, f"Error processing CSV: A critical column is missing or named incorrectly in the CSV file. Details: Missing column {e}"
    except Exception as e:
         db.session.rollback()
         import traceback
         traceback.print_exc()
         return False, f"Error reading/processing CSV for type '{target_device_type_str}': {type(e).__name__} {str(e)}"


# --- Heat Pump Processing Function ---
# Note: This function was not requested to be changed, but ensure its logic
# for reading columns also uses standardized names if needed.
def process_heat_pump_csvs(base_file_path, performance_file_path):
    """
    Processes the base and performance CSVs for Heat Pumps.
    (Ensure column names used here match standardized names if applicable)

    Args:
        base_file_path (str): Path to the cleaned base heat pump CSV.
        performance_file_path (str): Path to the cleaned performance heat pump CSV.

    Returns:
        tuple: (bool, str) indicating success status and a message.
    """
    print(f"Starting Heat Pump import. Base: {base_file_path}, Perf: {performance_file_path}")
    base_success_count = 0
    perf_success_count = 0
    base_error_count = 0
    perf_error_count = 0
    base_errors = []
    perf_errors = []
    # Dictionary to map temp_id (original index) from performance file to new DB ID
    temp_id_to_db_id_map = {}

    # --- Step 1: Process Base File ---
    try:
        # Define expected base columns (use lowercase snake_case)
        expected_base_cols = [
            'refrigerant', 'main_power_supply', 'control_of_pump_speed',
            'reversibility_on_water_side', 'simultaneous_heating', 'esp_duct',
            'outdoor_heat_exc_type', 'indoor_heat_exc_type', 'expansion_valve_type',
            'unit_capacity_control', 'compressor_type', 'compressor_inverter', 'compressor_number',
            # Common fields expected in base CSV
            'manufacturer', 'model_identifier', 'market_entry', 'market_exit',
            'noise_level_dba', 'price_currency', 'price_amount', 'data_source'
        ]

        na_values_list = ['NULL', 'Null', 'null', '', '#N/A', 'N/A', 'NA', 'NaN', 'None', 'nan', 'none', 'undefined', 'Invalid date']
        df_base = pd.read_csv(base_file_path, low_memory=False, na_values=na_values_list, keep_default_na=True)
        # Standardize column names AFTER reading
        df_base.columns = [col.lower().replace(' ', '_') for col in df_base.columns]
        print(f"Read {len(df_base)} rows from base file.")

        # Add the temp_id column based on index BEFORE iterating
        df_base['temp_id'] = df_base.index

        for index, row in df_base.iterrows():
            try:
                # Prepare data dict using get_row_value and standardized column names
                heat_pump_data = {
                    'device_type': 'heat_pump' # Set discriminator
                }
                for col in expected_base_cols:
                     # Determine data type based on column name (example)
                    if col in ['market_entry', 'market_exit']: dtype = 'date'
                    elif col in ['compressor_number']: dtype = 'int'
                    elif col in ['noise_level_dba', 'price_amount']: dtype = 'float'
                    else: dtype = 'string' # Default to string
                    heat_pump_data[col] = get_row_value(row, col, dtype)

                # Validate required fields after extraction
                if not heat_pump_data.get('manufacturer'): raise ValueError("manufacturer is missing")
                if not heat_pump_data.get('model_identifier'): raise ValueError("model_identifier is missing")
                # Add other validations as needed

                # Create and add HeatPump instance
                heat_pump = HeatPump(**heat_pump_data)
                db.session.add(heat_pump)
                db.session.flush()
                temp_id_to_db_id_map[row['temp_id']] = heat_pump.id
                db.session.commit()
                base_success_count += 1

            except (ValueError, TypeError) as e:
                db.session.rollback()
                base_error_count += 1
                base_errors.append(f"Base Row {index + 2}: Validation Error - {e}")
            except Exception as e:
                db.session.rollback()
                base_error_count += 1
                base_errors.append(f"Base Row {index + 2}: Unexpected error - {type(e).__name__} {e}")
                print(f"Unexpected error processing base row {index + 2}: {type(e).__name__} {e}")
                # import traceback; traceback.print_exc() # Uncomment for full debug

        print(f"Finished processing base file. Committed: {base_success_count}, Errors: {base_error_count}")

    except pd.errors.EmptyDataError:
        return False, "Heat pump base CSV file is empty."
    except FileNotFoundError:
        return False, f"Heat pump base CSV file not found at {base_file_path}."
    except KeyError as e:
         db.session.rollback()
         return False, f"Error processing base CSV: A critical column is missing or named incorrectly. Details: Missing column {e}"
    except Exception as e:
        db.session.rollback()
        # import traceback; traceback.print_exc() # Uncomment for full debug
        return False, f"Error reading/processing base heat pump CSV: {type(e).__name__} {str(e)}"

    # --- Step 2: Process Performance File ---
    if base_success_count == 0:
         print("No base heat pump records were successfully imported. Skipping performance data.")
         # Return success=True because the base processing finished, but indicate 0 processed
         return True, "Heat Pump Import Summary: Base Records Committed: 0. Performance Records Added: 0."


    try:
        df_perf = pd.read_csv(performance_file_path, low_memory=False, na_values=na_values_list, keep_default_na=True)
        # Standardize column names AFTER reading
        df_perf.columns = [col.lower().replace(' ', '_') for col in df_perf.columns]
        print(f"Read {len(df_perf)} rows from performance file.")

        # Check for required columns using standardized names
        required_perf_cols = {'temp_id', 'condition_group', 'condition_name', 'metric_name', 'metric_value'}
        missing_perf_cols = required_perf_cols - set(df_perf.columns)
        if missing_perf_cols:
             raise ValueError(f"Performance CSV is missing required column(s): {', '.join(missing_perf_cols)}")

        for index, row in df_perf.iterrows():
            try:
                temp_id = get_row_value(row, 'temp_id', 'int')
                if temp_id is None: raise ValueError("temp_id is missing or invalid")

                db_id = temp_id_to_db_id_map.get(temp_id)
                if db_id is None:
                    # Don't raise error, just skip this row and log it maybe
                    # print(f"Warning: No matching base record found for temp_id {temp_id} in performance row {index + 2}. Skipping.")
                    perf_error_count += 1 # Count as error/skip
                    perf_errors.append(f"Perf Row {index + 2}: No base record for temp_id {temp_id}")
                    continue # Skip to next performance row

                # Extract performance data using get_row_value
                condition_group = get_row_value(row, 'condition_group', 'string')
                condition_name = get_row_value(row, 'condition_name', 'string')
                metric_name = get_row_value(row, 'metric_name', 'string')
                metric_value = get_row_value(row, 'metric_value', 'float')

                # Validate required performance fields after extraction
                if condition_name is None: raise ValueError("condition_name is missing")
                if metric_name is None: raise ValueError("metric_name is missing")
                if metric_value is None: raise ValueError("metric_value is missing or invalid")

                # Create HeatPumpPerformance instance
                performance_entry = HeatPumpPerformance(
                    heat_pump_id=db_id, # Use the mapped database ID
                    condition_group=condition_group,
                    condition_name=condition_name,
                    metric_name=metric_name,
                    metric_value=metric_value
                )
                db.session.add(performance_entry)
                db.session.commit() # Commit performance entry
                perf_success_count += 1

            except (ValueError, TypeError) as e:
                db.session.rollback()
                perf_error_count += 1
                perf_errors.append(f"Perf Row {index + 2}: Validation Error - {e}")
            except Exception as e:
                db.session.rollback()
                perf_error_count += 1
                perf_errors.append(f"Perf Row {index + 2}: Unexpected error - {type(e).__name__} {e}")
                print(f"Unexpected error processing performance row {index + 2}: {type(e).__name__} {e}")
                # import traceback; traceback.print_exc() # Uncomment for full debug

        print(f"Finished processing performance file. Added: {perf_success_count}, Errors/Skipped: {perf_error_count}")

    except pd.errors.EmptyDataError:
        print("Performance CSV file is empty. No performance data added.")
    except FileNotFoundError:
        # Don't fail the whole import if performance file is missing, just warn
        print(f"Warning: Heat pump performance CSV file not found at {performance_file_path}. No performance data loaded.")
        perf_error_count = 0 # Reset perf errors if file not found is acceptable
    except KeyError as e:
         db.session.rollback()
         return False, f"Error processing performance CSV: A critical column is missing or named incorrectly. Details: Missing column {e}"
    except Exception as e:
        db.session.rollback()
        # import traceback; traceback.print_exc() # Uncomment for full debug
        return False, f"Error reading/processing performance heat pump CSV: {type(e).__name__} {str(e)}"

    # --- Step 3: Construct Final Message ---
    total_errors = base_error_count + perf_error_count
    message = f"Heat Pump Import Summary: Base Records Committed: {base_success_count} (Errors: {base_error_count}). Performance Records Added: {perf_success_count} (Errors/Skipped: {perf_error_count})."
    if total_errors > 0:
        all_errors = base_errors + perf_errors
        error_preview = '; '.join(all_errors[:5])
        message += f" Example issues: {error_preview}{'...' if len(all_errors) > 5 else ''}"

    # Consider import successful if at least base records were added, even if perf had issues/was missing
    success_status = base_success_count > 0 or (base_success_count == 0 and base_error_count == 0)
    return success_status, message