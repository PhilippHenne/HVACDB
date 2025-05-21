import pandas as pd
import numpy as np
import os
import re

MERGED_FILE = 'merged_hvac_data.csv'
CLEANED_OUTPUT_FILE = 'cleaned_hvac_for_db_v5_fixed_headers.csv'

def parse_market_date(date_str):
    """Parses date strings like '[yyyy, m, d]' or standard formats into 'YYYY-MM-DD'."""
    if pd.isna(date_str):
        return None
    # Try direct conversion first
    try:
        parsed_date = pd.to_datetime(date_str, errors='coerce')
        if pd.notna(parsed_date):
            return parsed_date.strftime('%Y-%m-%d')
    except Exception:
        pass
    try:
        cleaned_str = str(date_str).replace('[', '').replace(']', '').replace(' ', '')
        parts = cleaned_str.split(',')
        if len(parts) == 3:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                 dt = pd.to_datetime(f"{year}-{month}-{day}", errors='coerce')
                 if pd.notna(dt):
                    return dt.strftime('%Y-%m-%d')
                 else:
                    return None
            else:
                 return None
        else:
             return None
    except Exception:
        return None
    return None

try:
    print(f"Loading merged data from {MERGED_FILE}...")
    merged_df = pd.read_csv(os.path.join(os.getcwd(), MERGED_FILE), low_memory=False)
    print(f"Loaded {len(merged_df)} rows and {len(merged_df.columns)} columns.")

    actual_columns_set = set(merged_df.columns)

    cleaned_data = {}

    print("Mapping and transforming columns using exact headers from header.csv...")

    def get_col(df, col_name):
        if col_name in actual_columns_set:
            return df[col_name]
        else:
            print(f"Warning: Column '{col_name}' not found in the input CSV.")
            return pd.Series([np.nan] * len(df), index=df.index)

    cleaned_data['manufacturer'] = get_col(merged_df, 'supplier_or_trademark').combine_first(
                                     get_col(merged_df, 'participant_name'))
    cleaned_data['device_type'] = get_col(merged_df, 'product_group')
    cleaned_data['model_identifier'] = get_col(merged_df, 'model_identifier')

    market_entry_date_raw = get_col(merged_df, 'on_market_start_date')
    cleaned_data['market_entry'] = market_entry_date_raw.apply(parse_market_date)

    market_exit_date_raw = get_col(merged_df, 'on_market_end_date')
    cleaned_data['market_exit'] = market_exit_date_raw.apply(parse_market_date)

    cleaned_data['rated_power_cooling_kw'] = get_col(merged_df, 'cooling_characteristics_rated_capacity')
    cleaned_data['eer'] = get_col(merged_df, 'standard_cooling_cooling_pl_cond_a_eer').combine_first(
                           get_col(merged_df, 'cooling_characteristics_energy_efficiency_ratio'))
    cleaned_data['seer'] = get_col(merged_df, 'seasonal_efficiency_in_cooling_seer').combine_first(
                            get_col(merged_df, 'cooling_characteristics_seasonal_energy_efficiency_ratio'))
    cleaned_data['energy_class_cooling'] = get_col(merged_df, 'seasonal_efficiency_in_cooling_seer_class').combine_first(
                                           get_col(merged_df, 'cooling_characteristics_energy_class')).combine_first(
                                           get_col(merged_df, 'cooling_energy_class'))
    cleaned_data['design_load_cooling_kw'] = get_col(merged_df, 'seasonal_efficiency_in_cooling_pdesignc').combine_first(
                                            get_col(merged_df, 'cooling_characteristics_design_load')).combine_first(
                                            get_col(merged_df, 'cooling_design_load'))
    cleaned_data['annual_consumption_cooling_kwh'] = get_col(merged_df, 'seasonal_efficiency_in_cooling_qce').combine_first(
                                                     get_col(merged_df, 'cooling_characteristics_annual_electricity_consumption'))
    cleaned_data['eta_s_cooling_percent'] = get_col(merged_df, 'seasonal_efficiency_in_cooling_ηsc')

    cleaned_data['rated_power_heating_kw'] = get_col(merged_df, 'heating_characteristics_rated_capacity')
    cleaned_data['cop_standard'] = get_col(merged_df, 'standard_heating_cop').combine_first(
                                   get_col(merged_df, 'heating_characteristics_coefficient_of_performance'))
    cleaned_data['scop_average'] = get_col(merged_df, 'seasonnal_coefficient_of_performance_scop').combine_first(
                                   get_col(merged_df, 'heating_characteristics_seasonal_coefficient_of_performance_average'))
    cleaned_data['energy_class_heating_average'] = get_col(merged_df, 'seasonnal_coefficient_of_performance_scop_class').combine_first(
                                                   get_col(merged_df, 'heating_characteristics_energy_class_average')).combine_first(
                                                   get_col(merged_df, 'heating_energy_class'))
    cleaned_data['design_load_heating_average_kw'] = get_col(merged_df, 'seasonnal_coefficient_of_performance_pdesignh').combine_first(
                                                     get_col(merged_df, 'heating_characteristics_design_load_average')).combine_first(
                                                     get_col(merged_df, 'heating_design_load'))
    cleaned_data['annual_consumption_heating_average_kwh'] = get_col(merged_df, 'seasonnal_coefficient_of_performance_qhe').combine_first(
                                                             get_col(merged_df, 'heating_characteristics_annual_electricity_consumption_average'))
    cleaned_data['eta_s_heating_average_percent'] = get_col(merged_df, 'seasonnal_coefficient_of_performance_ηsh')

    cleaned_data['scop_warm'] = get_col(merged_df, 'seasonnal_coefficient_of_performance_warmer_climate_scop_w').combine_first(
                                get_col(merged_df, 'heating_characteristics_seasonal_coefficient_of_performance_warm'))
    cleaned_data['energy_class_heating_warm'] = get_col(merged_df, 'seasonnal_coefficient_of_performance_warmer_climate_scop_class_w').combine_first(
                                                get_col(merged_df, 'heating_characteristics_energy_class_warm'))
    cleaned_data['design_load_heating_warm_kw'] = get_col(merged_df, 'heating_characteristics_design_load_warm')
    cleaned_data['annual_consumption_heating_warm_kwh'] = get_col(merged_df, 'seasonnal_coefficient_of_performance_warmer_climate_qhe_w').combine_first(
                                                          get_col(merged_df, 'heating_characteristics_annual_electricity_consumption_warm'))
    cleaned_data['eta_s_heating_warm_percent'] = get_col(merged_df, 'seasonnal_coefficient_of_performance_warmer_climate_ηsh_w')

    cleaned_data['scop_cold'] = get_col(merged_df, 'seasonnal_coefficient_of_performance_colder_climate_scop_c').combine_first(
                                get_col(merged_df, 'heating_characteristics_seasonal_coefficient_of_performance_cold'))
    cleaned_data['energy_class_heating_cold'] = get_col(merged_df, 'seasonnal_coefficient_of_performance_colder_climate_scop__class_c ').combine_first( # Note trailing space in header? Verify.
                                                get_col(merged_df, 'heating_characteristics_energy_class_cold'))
    cleaned_data['design_load_heating_cold_kw'] = get_col(merged_df, 'seasonnal_coefficient_of_performance_colder_climate_pdesignh_c').combine_first(
                                                  get_col(merged_df, 'heating_characteristics_design_load_cold'))
    cleaned_data['annual_consumption_heating_cold_kwh'] = get_col(merged_df, 'seasonnal_coefficient_of_performance_colder_climate_qhe_c').combine_first(
                                                           get_col(merged_df, 'heatingCharacteristics_annualElectricityConsumptionCold'))
    cleaned_data['eta_s_heating_cold_percent'] = get_col(merged_df, 'seasonnal_coefficient_of_performance_colder_climate_ηsh_c')

    cleaned_data['refrigerant_type'] = get_col(merged_df, 'general_refrigerant').combine_first( # Prefer Eurovent?
                                        get_col(merged_df, 'refrigerant_name'))
    cleaned_data['refrigerant_gwp'] = get_col(merged_df, 'refrigerant_gwp') # EPREL only source

    cleaned_data['noise_level_outdoor_cooling_db'] = get_col(merged_df, 'acoustic_in_cooling_lwo_env').combine_first(
                                                     get_col(merged_df, 'cooling_characteristics_outdoor_sound_power'))
    cleaned_data['noise_level_indoor_cooling_db'] = get_col(merged_df, 'acoustic_in_cooling_lwi_1_env').combine_first( # Using LwI1 as primary
                                                     get_col(merged_df, 'cooling_characteristics_indoor_sound_power'))
    cleaned_data['noise_level_outdoor_heating_db'] = get_col(merged_df, 'acoustic_in_heating_lwo_env_in_heating').combine_first(
                                                      get_col(merged_df, 'heating_characteristics_outdoor_sound_power'))
    cleaned_data['noise_level_indoor_heating_db'] = get_col(merged_df, 'acoustic_in_heating_lwi_1_env_in_heating').combine_first( # Using LwI1 as primary
                                                     get_col(merged_df, 'heating_characteristics_indoor_sound_power'))

    cleaned_data['pc_cooling_cond_b_kw'] = get_col(merged_df, 'cooling_pl_cond_b_pc_pl_cond_b')
    cleaned_data['eer_cooling_cond_b'] = get_col(merged_df, 'cooling_pl_cond_b_eer_pl_cond_b')
    cleaned_data['pc_cooling_cond_c_kw'] = get_col(merged_df, 'cooling_pl_cond_c_pc_pl_cond_c')
    cleaned_data['eer_cooling_cond_c'] = get_col(merged_df, 'cooling_pl_cond_c_eer_pl_cond_c')
    cleaned_data['pc_cooling_cond_d_kw'] = get_col(merged_df, 'cooling_pl_cond_d_pc_pl_cond_d')
    cleaned_data['eer_cooling_cond_d'] = get_col(merged_df, 'cooling_pl_cond_d_eer_pl_cond_d')

    cleaned_data['ph_heating_cond_a_kw'] = get_col(merged_df, 'heating_pl_cond_a_ph_pl_cond_a')
    cleaned_data['cop_heating_cond_a'] = get_col(merged_df, 'heating_pl_cond_a_cop_pl_cond_a')
    cleaned_data['ph_heating_cond_b_kw'] = get_col(merged_df, 'heating_pl_cond_b_ph_pl_cond_b')
    cleaned_data['cop_heating_cond_b'] = get_col(merged_df, 'heating_pl_cond_b_cop_pl_cond_b')
    cleaned_data['ph_heating_cond_c_kw'] = get_col(merged_df, 'heating_pl_cond_c_ph_pl_cond_c')
    cleaned_data['cop_heating_cond_c'] = get_col(merged_df, 'heating_pl_cond_c_cop_pl_cond_c')
    cleaned_data['ph_heating_cond_d_kw'] = get_col(merged_df, 'heating_pl_cond_d_ph_pl_cond_d')
    cleaned_data['cop_heating_cond_d'] = get_col(merged_df, 'heating_pl_cond_d_cop_pl_cond_d')

    cleaned_data['tol_temp_heating'] = get_col(merged_df, 'heating_pl_cond_e_tol_tol')
    cleaned_data['ph_heating_tol_kw'] = get_col(merged_df, 'heating_pl_cond_e_tol_ph_pl_cond_e_tol')
    cleaned_data['cop_heating_tol'] = get_col(merged_df, 'heating_pl_cond_e_tol_cop_pl_cond_e_tol')
    cleaned_data['tbiv_temp_heating'] = get_col(merged_df, 'heating_pl_cond_f_tbivalent_tbiv')
    cleaned_data['ph_heating_tbiv_kw'] = get_col(merged_df, 'heating_pl_cond_f_tbivalent_ph_pl_cond_f_tbiv')
    cleaned_data['cop_heating_tbiv'] = get_col(merged_df, 'heating_pl_cond_f_tbivalent_cop_pl_cond_f_tbiv')

    cleaned_data['power_standby_cooling_kw'] = get_col(merged_df, 'psbc_psbc') 
    cleaned_data['power_off_cooling_kw'] = get_col(merged_df, 'poffc_poffc')
    cleaned_data['power_standby_heating_kw'] = get_col(merged_df, 'psbh_psbh')
    cleaned_data['power_off_heating_kw'] = get_col(merged_df, 'poffh_poffh')

    cleaned_data['capacity_control_type'] = get_col(merged_df, 'general_capacity_control')
    cleaned_data['degradation_coeff_cooling_cd'] = get_col(merged_df, 'degradation_coefficient_cd')

    eprel_id_present = get_col(merged_df, 'model_identifier').notna()
    eurovent_id_present = get_col(merged_df, 'trade_name').notna()

    sources = []
    for eprel_exists, eurovent_exists in zip(eprel_id_present, eurovent_id_present):
        if eprel_exists and eurovent_exists:
            sources.append('Merged EPREL+Eurovent')
        elif eprel_exists:
            sources.append('EPREL Only')
        elif eurovent_exists:
            sources.append('Eurovent Only')
        else:
            sources.append('Unknown Origin')
    cleaned_data['data_source'] = sources

    cleaned_data['normalized_id'] = get_col(merged_df, 'normalized_id') # Use get_col for safety

    print("\nCreating the final cleaned DataFrame (v5)...")
    final_df = pd.DataFrame(cleaned_data)

    TARGET_COLUMNS_ORDER = [
        "manufacturer", "model_identifier", "market_entry", "market_exit", "device_type",
        "rated_power_cooling_kw", "eer", "seer", "energy_class_cooling",
        "design_load_cooling_kw", "annual_consumption_cooling_kwh", "eta_s_cooling_percent",
        "pc_cooling_cond_b_kw", "eer_cooling_cond_b",
        "pc_cooling_cond_c_kw", "eer_cooling_cond_c",
        "pc_cooling_cond_d_kw", "eer_cooling_cond_d",
        "rated_power_heating_kw", "cop_standard", "scop_average", "energy_class_heating_average",
        "design_load_heating_average_kw", "annual_consumption_heating_average_kwh", "eta_s_heating_average_percent",
        "scop_warm", "energy_class_heating_warm", "design_load_heating_warm_kw",
        "annual_consumption_heating_warm_kwh", "eta_s_heating_warm_percent",
        "scop_cold", "energy_class_heating_cold", "design_load_heating_cold_kw",
        "annual_consumption_heating_cold_kwh", "eta_s_heating_cold_percent",
        "ph_heating_cond_a_kw", "cop_heating_cond_a", "ph_heating_cond_b_kw", "cop_heating_cond_b",
        "ph_heating_cond_c_kw", "cop_heating_cond_c", "ph_heating_cond_d_kw", "cop_heating_cond_d",
        "tol_temp_heating", "ph_heating_tol_kw", "cop_heating_tol",
        "tbiv_temp_heating", "ph_heating_tbiv_kw", "cop_heating_tbiv",
        "power_standby_cooling_kw", "power_off_cooling_kw",
        "power_standby_heating_kw", "power_off_heating_kw",
        "refrigerant_type", "refrigerant_gwp",
        "noise_level_outdoor_cooling_db", "noise_level_indoor_cooling_db",
        "noise_level_outdoor_heating_db", "noise_level_indoor_heating_db",
        "capacity_control_type", "degradation_coeff_cooling_cd",
        "data_source",
        "normalized_id"
    ]

    final_df_ordered = pd.DataFrame()
    final_columns_present = []
    for col in TARGET_COLUMNS_ORDER:
        if col in final_df.columns:
            final_df_ordered[col] = final_df[col]
            final_columns_present.append(col)
        else:
            print(f"Note: Target column '{col}' not found in generated data, skipping.")

    print(f"Final DataFrame has {len(final_df_ordered)} rows and {len(final_df_ordered.columns)} columns.")
    print("\nColumns in the final table (v5):", final_columns_present)
    print("\nSample of the final data (v5):")
    print(final_df_ordered.head())

    print(f"\nSaving cleaned data to {CLEANED_OUTPUT_FILE}...")
    final_df_ordered.to_csv(os.path.join(os.getcwd(), CLEANED_OUTPUT_FILE), index=False, na_rep='NULL', date_format='%Y-%m-%d')
    print("Done.")

except FileNotFoundError:
    print(f"Error: Input file not found. Please ensure '{MERGED_FILE}' is in the script's directory: {os.path.join(os.getcwd(), MERGED_FILE)}")
except pd.errors.EmptyDataError:
     print(f"Error: Input file '{MERGED_FILE}' is empty.")
except KeyError as e:
    print(f"Error: A required column name used in the script was not found in the CSV. Details: {e}")
    print("Please carefully check the EXACT column names in 'header.csv' against the names used in the mapping section of this script.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    import traceback
    traceback.print_exc()