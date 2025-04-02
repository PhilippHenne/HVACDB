import pandas as pd
import numpy as np
import os
import re # Import re for date parsing

# --- Configuration ---
MERGED_FILE = 'merged_hvac_data.csv' # Input file from the previous step
CLEANED_OUTPUT_FILE = 'cleaned_hvac_for_db_v2.csv' # Updated output file name

# --- Helper Function for Coalescing ---
# (Remains the same as before)
def get_coalesced_column(df, base_name):
    """Gets a column, preferring _A suffix, then _B, then base name."""
    col_a = base_name + '_A'
    col_b = base_name + '_B'

    if col_a in df.columns and col_b in df.columns:
        return df[col_a].combine_first(df[col_b])
    elif col_a in df.columns:
        return df[col_a]
    elif col_b in df.columns:
        return df[col_b]
    elif base_name in df.columns:
        return df[base_name]
    else:
        print(f"Warning: Base column '{base_name}' (or variants _A/_B) not found.")
        return pd.Series([np.nan] * len(df), index=df.index)

# --- Helper Function for Parsing Market Date ---
def parse_market_date(date_str):
    """Parses date strings like '[yyyy, m, d]' into 'YYYY-MM-DD'."""
    if pd.isna(date_str):
        return None
    try:
        # Remove brackets and spaces, then split
        cleaned_str = str(date_str).replace('[', '').replace(']', '').replace(' ', '')
        parts = cleaned_str.split(',')
        if len(parts) == 3:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            # Format as YYYY-MM-DD
            return f"{year:04d}-{month:02d}-{day:02d}"
        else:
            # Attempt direct datetime conversion if format is different
            return pd.to_datetime(date_str, errors='coerce').strftime('%Y-%m-%d')
    except Exception:
        # Fallback for unexpected formats or conversion errors
         try: # Try direct conversion one more time on original string
            return pd.to_datetime(date_str, errors='coerce').strftime('%Y-%m-%d')
         except:
            return None # Return None if parsing fails

# --- Main Script Logic ---
try:
    print(f"Loading merged data from {MERGED_FILE}...")
    merged_df = pd.read_csv(os.path.join(os.getcwd(), MERGED_FILE), low_memory=False)
    print(f"Loaded {len(merged_df)} rows and {len(merged_df.columns)} columns.")

    # Create a dictionary to hold the data for the new DataFrame
    cleaned_data = {}

    print("Mapping and transforming columns (v2)...")

    # --- Mapping Logic ---

    # == Core Identification ==
    cleaned_data['manufacturer'] = get_coalesced_column(merged_df, 'supplierOrTrademark').combine_first(
                                     get_coalesced_column(merged_df, 'TRADE_NAME'))
    cleaned_data['device_type'] = get_coalesced_column(merged_df, 'productGroup') # Or 'functionType' / 'MODEL_TYPE'

    # == Market Entry ==
    market_date_raw = get_coalesced_column(merged_df, 'onMarketStartDate')
    cleaned_data['market_entry'] = market_date_raw.apply(parse_market_date) # Use the new parsing function

    # == Cooling Performance ==
    # Prefer characteristics columns, fallback to others if needed
    cleaned_data['rated_power_cooling_kw'] = get_coalesced_column(merged_df, 'coolingCharacteristics_ratedCapacity')
    cleaned_data['eer'] = get_coalesced_column(merged_df, 'coolingCharacteristics_energyEfficiencyRatio').combine_first(
                           get_coalesced_column(merged_df, 'Standard Cooling/Cooling PL Cond A | EER'))
    cleaned_data['seer'] = get_coalesced_column(merged_df, 'coolingCharacteristics_seasonalEnergyEfficiencyRatio').combine_first(
                            get_coalesced_column(merged_df, 'Seasonal Efficiency in Cooling | SEER'))
    cleaned_data['energy_class_cooling'] = get_coalesced_column(merged_df, 'coolingCharacteristics_energyClass').combine_first(
                                           get_coalesced_column(merged_df, 'coolingEnergyClass')).combine_first(
                                           get_coalesced_column(merged_df, 'Seasonal Efficiency in Cooling | SEER Class'))
    cleaned_data['design_load_cooling_kw'] = get_coalesced_column(merged_df, 'coolingCharacteristics_designLoad').combine_first(
                                            get_coalesced_column(merged_df, 'coolingDesignLoad')).combine_first(
                                            get_coalesced_column(merged_df, 'Seasonal Efficiency in Cooling | Pdesignc'))
    cleaned_data['annual_consumption_cooling_kwh'] = get_coalesced_column(merged_df, 'coolingCharacteristics_annualElectricityConsumption').combine_first(
                                                     get_coalesced_column(merged_df, 'Seasonal Efficiency in Cooling | Qce'))

    # == Heating Performance ==
    cleaned_data['rated_power_heating_kw'] = get_coalesced_column(merged_df, 'heatingCharacteristics_ratedCapacity')
    cleaned_data['cop_standard'] = get_coalesced_column(merged_df, 'heatingCharacteristics_coefficientOfPerformance').combine_first(
                                   get_coalesced_column(merged_df, 'Standard Heating | COP'))
    # SCOP - Average Climate
    cleaned_data['scop_average'] = get_coalesced_column(merged_df, 'heatingCharacteristics_seasonalCoefficientOfPerformanceAverage').combine_first(
                                   get_coalesced_column(merged_df, 'Seasonnal Coefficient of Performance | SCOP'))
    cleaned_data['energy_class_heating_average'] = get_coalesced_column(merged_df, 'heatingCharacteristics_energyClassAverage').combine_first(
                                                   get_coalesced_column(merged_df, 'heatingEnergyClass')).combine_first(
                                                   get_coalesced_column(merged_df, 'Seasonnal Coefficient of Performance | SCOP Class'))
    cleaned_data['design_load_heating_average_kw'] = get_coalesced_column(merged_df, 'heatingCharacteristics_designLoadAverage').combine_first(
                                                     get_coalesced_column(merged_df, 'heatingDesignLoad')).combine_first(
                                                     get_coalesced_column(merged_df, 'Seasonnal Coefficient of Performance | Pdesignh'))
    cleaned_data['annual_consumption_heating_average_kwh'] = get_coalesced_column(merged_df, 'heatingCharacteristics_annualElectricityConsumptionAverage').combine_first(
                                                             get_coalesced_column(merged_df, 'Seasonnal Coefficient of Performance | Qhe'))
    # SCOP - Warm Climate
    cleaned_data['scop_warm'] = get_coalesced_column(merged_df, 'heatingCharacteristics_seasonalCoefficientOfPerformanceWarm').combine_first(
                                get_coalesced_column(merged_df, 'Seasonnal Coefficient of Performance Warmer climate | SCOP_W'))
    cleaned_data['energy_class_heating_warm'] = get_coalesced_column(merged_df, 'heatingCharacteristics_energyClassWarm').combine_first(
                                                get_coalesced_column(merged_df, 'Seasonnal Coefficient of Performance Warmer climate | SCOP Class_W'))
    cleaned_data['design_load_heating_warm_kw'] = get_coalesced_column(merged_df, 'heatingCharacteristics_designLoadWarm') # Only one clear source?
    cleaned_data['annual_consumption_heating_warm_kwh'] = get_coalesced_column(merged_df, 'heatingCharacteristics_annualElectricityConsumptionWarm').combine_first(
                                                          get_coalesced_column(merged_df, 'Seasonnal Coefficient of Performance Warmer climate | Qhe_W'))
    # SCOP - Cold Climate
    cleaned_data['scop_cold'] = get_coalesced_column(merged_df, 'heatingCharacteristics_seasonalCoefficientOfPerformanceCold').combine_first(
                                get_coalesced_column(merged_df, 'Seasonnal Coefficient of Performance Colder Climate | SCOP_C'))
    cleaned_data['energy_class_heating_cold'] = get_coalesced_column(merged_df, 'heatingCharacteristics_energyClassCold').combine_first(
                                                get_coalesced_column(merged_df, 'Seasonnal Coefficient of Performance Colder Climate | SCOP Class_C'))
    cleaned_data['design_load_heating_cold_kw'] = get_coalesced_column(merged_df, 'heatingCharacteristics_designLoadCold').combine_first(
                                                  get_coalesced_column(merged_df, 'Seasonnal Coefficient of Performance Colder Climate | Pdesignh_C'))
    cleaned_data['annual_consumption_heating_cold_kwh'] = get_coalesced_column(merged_df, 'heatingCharacteristics_annualElectricityConsumptionCold').combine_first(
                                                           get_coalesced_column(merged_df, 'Seasonnal Coefficient of Performance Colder Climate | Qhe_C'))

    # == Refrigerant ==
    cleaned_data['refrigerant_type'] = get_coalesced_column(merged_df, 'refrigerantName').combine_first(
                                        get_coalesced_column(merged_df, 'General | Refrigerant'))
    cleaned_data['refrigerant_gwp'] = get_coalesced_column(merged_df, 'refrigerantGwp')

    # == Sound (Example: Outdoor Cooling) ==
    # Still using outdoor cooling as example, confirm if Lw or Lp(dBA)
    cleaned_data['noise_level_outdoor_cooling_db'] = get_coalesced_column(merged_df, 'outdoorSoundPowerCooling').combine_first(
                                                     get_coalesced_column(merged_df, 'Acoustic in cooling | LwO env'))


    # == Data Source and Identifiers ==
    id_col_a_original = 'model_identifier_A_A'
    id_col_b_original = 'model_identifier_B_B'

    def determine_source(row):
        # (Function remains the same as before)
        has_a = pd.notna(row[id_col_a_original]) if id_col_a_original in row.index else False
        has_b = pd.notna(row[id_col_b_original]) if id_col_b_original in row.index else False
        if has_a and has_b: return 'Merged A+B'
        elif has_a: return 'Source A Only'
        elif has_b: return 'Source B Only'
        else: return 'Unknown Origin'

    if id_col_a_original in merged_df.columns and id_col_b_original in merged_df.columns:
         cleaned_data['data_source'] = merged_df.apply(determine_source, axis=1)
    # (Add fallbacks as before if needed)
    else:
         print(f"Warning: Original identifier columns ({id_col_a_original}, {id_col_b_original}) not found. Setting data_source generically.")
         cleaned_data['data_source'] = 'Merged EPREL/Certification Data'

    cleaned_data['original_model_id_A'] = merged_df[id_col_a_original] if id_col_a_original in merged_df.columns else np.nan
    cleaned_data['original_model_id_B'] = merged_df[id_col_b_original] if id_col_b_original in merged_df.columns else np.nan
    cleaned_data['normalized_id'] = merged_df['normalized_id'] if 'normalized_id' in merged_df.columns else np.nan


    # --- Create Final DataFrame ---
    print("\nCreating the final cleaned DataFrame (v2)...")
    final_df = pd.DataFrame(cleaned_data)

    # Define the desired column order for the output file
    TARGET_COLUMNS_ORDER = [
        # Core Info
        "manufacturer", "market_entry", "device_type",
        # Cooling Perf
        "rated_power_cooling_kw", "eer", "seer", "energy_class_cooling",
        "design_load_cooling_kw", "annual_consumption_cooling_kwh",
        # Heating Perf (Standard/Average)
        "rated_power_heating_kw", "cop_standard", "scop_average", "energy_class_heating_average",
        "design_load_heating_average_kw", "annual_consumption_heating_average_kwh",
        # Heating Perf (Warm Climate)
        "scop_warm", "energy_class_heating_warm", "design_load_heating_warm_kw",
        "annual_consumption_heating_warm_kwh",
        # Heating Perf (Cold Climate)
        "scop_cold", "energy_class_heating_cold", "design_load_heating_cold_kw",
        "annual_consumption_heating_cold_kwh",
        # Sustainability / Other
        "refrigerant_type", "refrigerant_gwp", "noise_level_outdoor_cooling_db",
        # Identifiers / Provenance
        "data_source", "original_model_id_A", "original_model_id_B", "normalized_id"
    ]

    # Filter and reorder columns
    final_df = final_df[[col for col in TARGET_COLUMNS_ORDER if col in final_df.columns]]

    print(f"Final DataFrame has {len(final_df)} rows and {len(final_df.columns)} columns.")
    print("\nColumns in the final table (v2):", list(final_df.columns))
    print("\nSample of the final data (v2):")
    print(final_df.head())

    # --- Save Cleaned Data ---
    print(f"\nSaving cleaned data to {CLEANED_OUTPUT_FILE}...")
    final_df.to_csv(os.path.join(os.getcwd(), CLEANED_OUTPUT_FILE), index=False, na_rep='NULL', date_format='%Y-%m-%d')
    print("Done.")

except FileNotFoundError:
    print(f"Error: Input file not found. Please ensure '{MERGED_FILE}' is in the script's directory.")
except KeyError as e:
    print(f"Error: A required column was not found in the merged CSV. Details: {e}")
    print("Please check the column names in the merged file and adjust the mapping logic in the script.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")