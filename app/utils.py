# app/utils.py
import os
import pandas as pd
from werkzeug.utils import secure_filename
from .models import db, HVACDevice, MODEL_MAP, AirConditioner, ResidentialVentilationUnit, HeatPump 
import math 
from datetime import date
import re
from flask import current_app

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'csv'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def safe_int_convert(value):
    if pd.isna(value):
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None

def safe_date_convert(value):
    if pd.isna(value):
        return None
    try:
        dt = pd.to_datetime(value, errors='coerce')
        return dt.date() if pd.notna(dt) else None
    except Exception:
        return None

def get_row_value(row, col_name, data_type='string'):
    value = row.get(col_name)
    if pd.isna(value) or (isinstance(value, str) and value.strip() == ''):
        return None
    try:
        if data_type == 'float':
            return float(str(value).replace(',', '.'))
        elif data_type == 'int':
            return safe_int_convert(str(value).replace(',', '.'))
        elif data_type == 'string':
            return str(value).strip()
        elif data_type == 'date':
            return safe_date_convert(value)
        else:
            return str(value).strip()
    except (ValueError, TypeError):
        current_app.logger.warning(f"Conversion Warning: Could not convert value '{value}' for column '{col_name}' to type '{data_type}'. Field set to None.")
        return None

def process_csv(file_path, target_device_type_str):
    ModelClass = MODEL_MAP.get(target_device_type_str)
    if not ModelClass:
        return False, f"Invalid target device type '{target_device_type_str}' provided for CSV processing."

    try:
        na_values_list = ['NULL', 'Null', 'null', '', '#N/A', 'N/A', 'NA', 'NaN', 'None', 'nan', 'none', 'undefined', 'Invalid date', '-']
        df = pd.read_csv(file_path, low_memory=False, na_values=na_values_list, keep_default_na=True, encoding='utf-8', skipinitialspace=True)
        
        original_cols = df.columns.tolist()
        df.columns = [
            str(col).strip().lower().replace(' ', '_').replace('-', '_').replace('/', '_').replace('.', '_dot_').replace('(', '_lp_').replace(')', '_rp_')
            for col in original_cols
        ]
        df.columns = [re.sub(r'_+', '_', col).strip('_') for col in df.columns]
        current_app.logger.debug(f"CSV columns after standardization for import ({target_device_type_str}): {df.columns.tolist()}")

        success_count = 0
        error_count = 0
        errors_list = []

        for index, row in df.iterrows():
            try:
                manufacturer_val = get_row_value(row, 'manufacturer', 'string')
                model_identifier_val = get_row_value(row, 'model_identifier', 'string')

                if not manufacturer_val: 
                    raise ValueError(f"Row {index+2}: 'manufacturer' is missing or invalid.")
                if not model_identifier_val: 
                    raise ValueError(f"Row {index+2}: 'model_identifier' is missing or invalid.")

                common_data = {
                    'manufacturer': manufacturer_val,
                    'model_identifier': model_identifier_val,
                    'market_entry': get_row_value(row, 'market_entry', 'date'),
                    'market_exit': get_row_value(row, 'market_exit', 'date'),
                    'noise_level_dba': get_row_value(row, 'noise_level_dba', 'float'),
                    'price_currency': get_row_value(row, 'price_currency', 'string'),
                    'price_amount': get_row_value(row, 'price_amount', 'float'),
                    'data_source': get_row_value(row, 'data_source', 'string'),
                    'device_type': target_device_type_str,
                }

                specific_data = {}
                current_fields_map = {}
                if target_device_type_str == 'air_conditioner':
                    ac_fields_map = {
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
                    }

                    for model_field, (csv_col, dtype) in ac_fields_map.items():
                        specific_data[model_field] = get_row_value(row, csv_col.lower(), dtype)


                elif target_device_type_str == 'residential_ventilation_unit':
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
                elif target_device_type_str == 'heat_pump':
                    current_fields_map = {
                        'trade_name': ('trade_name', 'string'),
                        'model_type': ('model_type', 'string'),
                        'software_name': ('software_name', 'string'),
                        'software_version': ('software_version', 'string'),
                        'refrigerant': ('refrigerant', 'string'), 
                        'main_power_supply': ('main_power_supply', 'string'),
                        'control_of_pump_speed': ('control_of_pump_speed', 'string'),
                        'reversibility_on_water_side': ('reversibility_on_water_side', 'string'),
                        'simultaneous_heating': ('simultaneous_heating', 'string'),
                        'esp_duct': ('esp_duct', 'string'),
                        'outdoor_heat_exchanger_type': ('outdoor_heat_exchanger_type', 'string'),
                        'indoor_heat_exchanger_type': ('indoor_heat_exchanger_type', 'string'),
                        'expansion_valve_type': ('expansion_valve_type', 'string'),
                        'unit_capacity_control': ('unit_capacity_control', 'string'),
                        'compressor_type': ('compressor_type', 'string'),
                        'compressor_inverter': ('compressor_inverter', 'string'),
                        'compressor_number': ('compressor_number', 'int'),
                        
                        # Flattened KPIs
                        'sound_power_level_lw': ('sound_power_level_lw', 'float'),
                        'pc_a35_w12_7': ('pc_a35_w12_7', 'float'),
                        'eer_a35_w12_7': ('eer_a35_w12_7', 'float'),
                        'seer_ac': ('seer_ac', 'float'),
                        'eta_sc_ac': ('eta_sc_ac', 'float'),
                        'pdesignh_avg_lwt35': ('pdesignh_avg_lwt35', 'float'),
                        'scop_avg_lwt35': ('scop_avg_lwt35', 'float'),
                        'eta_sh_avg_lwt35': ('eta_sh_avg_lwt35', 'float'),
                        'ph_a7_w35': ('ph_a7_w35', 'float'),
                        'cop_a7_w35': ('cop_a7_w35', 'float'),
                        'ph_a2_w35': ('ph_a2_w35', 'float'),
                        'cop_a2_w35': ('cop_a2_w35', 'float'),
                        'ph_am7_w35': ('ph_am7_w35', 'float'),
                        'cop_am7_w35': ('cop_am7_w35', 'float'),
                        'pdesignh_avg_lwt55': ('pdesignh_avg_lwt55', 'float'),
                        'scop_avg_lwt55': ('scop_avg_lwt55', 'float'),
                        'eta_sh_avg_lwt55': ('eta_sh_avg_lwt55', 'float'),
                        'ph_a7_w55_approx': ('ph_a7_w55_approx', 'float'),
                        'cop_a7_w55_approx': ('cop_a7_w55_approx', 'float'),
                        'sepr_mt': ('sepr_mt', 'float'),
                        'sepr_ht': ('sepr_ht', 'float'),
                        'sepr_lt': ('sepr_lt', 'float'),
                        'psbc_standby_cooling': ('psbc_standby_cooling', 'float'),
                        'psbh_standby_heating': ('psbh_standby_heating', 'float'),
                    }

                for model_field, (csv_col, dtype) in current_fields_map.items():
                    cleaned_csv_col_for_lookup = csv_col.strip().lower().replace(' ', '_').replace('-', '_').replace('/', '_').replace('.', '_dot_').replace('(', '_lp_').replace(')', '_rp_')
                    cleaned_csv_col_for_lookup = re.sub(r'_+', '_', cleaned_csv_col_for_lookup).strip('_')
                    specific_data[model_field] = get_row_value(row, cleaned_csv_col_for_lookup, dtype)
                
                model_attribute_names = set(common_data.keys()) | set(specific_data.keys())
                
                mapped_csv_cols = set()
                for common_key in common_data.keys():
                    mapped_csv_cols.add(common_key) 
                for model_attr, (csv_col, _) in current_fields_map.items():
                     cleaned_csv_col_for_lookup = csv_col.strip().lower().replace(' ', '_').replace('-', '_').replace('/', '_').replace('.', '_dot_').replace('(', '_lp_').replace(')', '_rp_')
                     cleaned_csv_col_for_lookup = re.sub(r'_+', '_', cleaned_csv_col_for_lookup).strip('_')
                     mapped_csv_cols.add(cleaned_csv_col_for_lookup)

                custom_data = {}
                for csv_col_in_df in df.columns:
                    if csv_col_in_df not in mapped_csv_cols:
                        value = row.get(csv_col_in_df) 
                        if pd.notna(value) and str(value).strip() != '':
                            if isinstance(value, (bool, int, float, str)): custom_data[csv_col_in_df] = value
                            elif isinstance(value, date): custom_data[csv_col_in_df] = value.isoformat()
                            else:
                                try:
                                    if hasattr(value, 'item'): custom_data[csv_col_in_df] = value.item() # numpy types
                                    else: custom_data[csv_col_in_df] = str(value)
                                except: custom_data[csv_col_in_df] = str(value) # Fallback
                
                device = ModelClass(**common_data, **specific_data)
                db.session.add(device)
                db.session.commit()
                success_count += 1

            except ValueError as e: 
                db.session.rollback()
                error_count += 1
                errors_list.append(str(e))
                current_app.logger.warning(f"CSV Import ValueError: {e}")
            except Exception as e:
                db.session.rollback()
                error_count += 1
                errors_list.append(f"Row {index + 2}: Unexpected error - {type(e).__name__} {e}")
                current_app.logger.error(f"CSV Import Exception: Row {index+2}, Type {target_device_type_str}, Error: {e}", exc_info=True)

        # Construct summary message
        if success_count > 0 and error_count == 0:
            message = f"Successfully committed {success_count} {ModelClass.__name__} devices."
        elif success_count > 0 and error_count > 0:
            message = f"Import for {ModelClass.__name__} finished. Committed: {success_count}, Rows with errors: {error_count}."
        elif success_count == 0 and error_count > 0:
            message = f"Import for {ModelClass.__name__} failed. No devices committed. Rows with errors: {error_count}."
        elif success_count == 0 and error_count == 0:
             message = f"No data rows found or processed in the CSV for {ModelClass.__name__}."
        else:
            message = f"Import for {ModelClass.__name__} completed."
        
        if errors_list:
            message += f" First few errors: {'; '.join(errors_list[:3])}{'...' if len(errors_list) > 3 else ''}"
        
        return success_count > 0 or (success_count == 0 and error_count == 0 and len(df) == 0) , message
    
    except pd.errors.EmptyDataError:
         return True, f"CSV file for '{ModelClass.__name__}' is empty. No data imported."
    except KeyError as e:
         db.session.rollback()
         current_app.logger.error(f"CSV Import KeyError: Type {target_device_type_str}, Missing column {e}", exc_info=True)
         return False, f"Error processing CSV for {ModelClass.__name__}: A critical column is missing or named incorrectly. Details: Missing column {e}"
    except Exception as e:
         db.session.rollback()
         current_app.logger.error(f"General CSV Processing Error: Type {target_device_type_str}, Error: {e}", exc_info=True)
         return False, f"Unexpected error reading/processing CSV for {ModelClass.__name__}: {type(e).__name__} - {str(e)}"
