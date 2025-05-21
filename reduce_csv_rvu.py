import pandas as pd
import numpy as np
import os
import re


def parse_market_date(date_str):
    """Parses date strings like '[yyyy, m, d]' into 'YYYY-MM-DD'."""
    if pd.isna(date_str):
        return None
    try:
        cleaned_str = str(date_str).replace('[', '').replace(']', '').replace(' ', '')
        parts = cleaned_str.split(',')
        if len(parts) == 3:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            return f"{year:04d}-{month:02d}-{day:02d}"
        else:
            return pd.to_datetime(date_str, errors='coerce').strftime('%Y-%m-%d')
    except Exception:
         try:
            return pd.to_datetime(date_str, errors='coerce').strftime('%Y-%m-%d')
         except:
            return None # Return None if parsing fails


input_file = 'residentialventilationunits_expanded.csv' 
output_file = 'cleaned_residentialventilationunits.csv'

# 1. Define mappings from source CSV column name to target database column name
#    Verify these source names match your CSV headers EXACTLY
#    Source names should be lowercase as we convert headers to lowercase later.
column_mapping = {
    # Common Fields Mappings (Verify source names!)
    'organisation_organisationname': 'manufacturer',
    'modelidentifier': 'model_identifier',
    'onmarketstartdate': 'market_entry',
    'onmarketenddate': 'market_exit',
    'soundpowerlevel': 'noise_level_dba',
}

# 2. List ALL target columns you want to KEEP in the final CSV
#    These should match the keys in column_mapping OR original column names (if no mapping needed)
#    Ensure these correspond to your database model fields (common + ventilator specific)
target_columns_to_keep = [
    'manufacturer',
    'model_identifier',
    'market_entry',
    'market_exit',
    'power_rating_kw',
    'noise_level_dba',
    'price_currency',
    'price_amount',
    'data_source',

    # Ventilator Specific Fields 
    'maximumflowrate',
    'referenceflowrate',
    'referencepressuredifference',
    'typology',
    'heatrecoverysystem',
    'thermalefficiencyheatrecovery',
    'specificpowerinput',
    'fandrivepowerinput',
    'drivetype',
    'ductedunit',
    'controltypology',
    'specificenergyconsumptionwarm',
    'specificenergyconsumptionaverage',
    'specificenergyconsumptioncold',
    'annualheatingsavedaverageclimate',
    'annualheatingsavedcoldclimate',
    'annualheatingsavedwarmclimate',
    'energyclass',
    'maximuminternalleakagerate',
    'maximumexternalleakagerate',

]

date_columns = ['market_entry', 'market_exit']
numeric_columns = [
    'power_rating_kw', 'noise_level_dba', 'price_amount', 'maximumflowrate',
    'referenceflowrate', 'referencepressuredifference', 'thermalefficiencyheatrecovery',
    'specificpowerinput', 'fandrivepowerinput', 'specificenergyconsumptionwarm',
    'specificenergyconsumptionaverage', 'specificenergyconsumptioncold',
    'annualheatingsavedaverageclimate', 'annualheatingsavedcoldclimate', 'annualheatingsavedwarmclimate', 'maximuminternalleakagerate', 'maximumexternalleakagerate'
]

na_values_list = ['NULL', 'Null', 'null', '', '#N/A', '#N/A N/A', '#NA', '-1.#IND', '-1.#QNAN', '-NaN', '-nan',
                  '1.#IND', '1.#QNAN', '<NA>', 'N/A', 'NA', 'NaN', 'None', 'nan', 'none']

print(f"Reading input file: {input_file}")
try:
    df = pd.read_csv(input_file, low_memory=False, na_values=na_values_list, keep_default_na=True)
except FileNotFoundError:
    print(f"ERROR: Input file not found at {input_file}")
    exit()
except Exception as e:
    print(f"ERROR: Failed to read CSV file. {e}")
    exit()

print(f"Read {len(df)} rows and {len(df.columns)} columns.")

original_columns = df.columns.tolist()
df.columns = df.columns.str.lower()
print("Converted column headers to lowercase.")

df.rename(columns=column_mapping, inplace=True)
print(f"Renamed columns based on mapping: {list(column_mapping.keys())}")

df['data_source'] = 'EPREL'
df['device_type'] = 'ventilator' # Use the key defined in DEVICE_TYPES/MODEL_MAP
print("Added 'data_source' and 'device_type' columns.")

existing_target_columns = [col for col in target_columns_to_keep if col in df.columns]
missing_target_columns = [col for col in target_columns_to_keep if col not in df.columns]

if missing_target_columns:
    print(f"\nWARNING: The following target columns were not found in the input CSV (after renaming):")
    for col in missing_target_columns:
        print(f"- {col}")

print(f"\nSelecting final columns: {existing_target_columns}")
df_cleaned = df[existing_target_columns].copy() 
print("\nConverting data types...")
for col in date_columns:
    if col in df_cleaned.columns:
        original_dtype = df_cleaned[col].dtype
        df_cleaned[col] = df_cleaned[col].apply(parse_market_date)
        print(f"- Converted '{col}' (original type: {original_dtype}) to date (errors coerced to NaT).")
    else:
         print(f"- Date column '{col}' not found, skipping conversion.")

for col in numeric_columns:
    if col in df_cleaned.columns:
        original_dtype = df_cleaned[col].dtype
        df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
        print(f"- Converted '{col}' (original type: {original_dtype}) to numeric (errors coerced to NaN).")
    else:
         print(f"- Numeric column '{col}' not found, skipping conversion.")

print(f"\nSaving cleaned data to: {output_file}")
try:
    df_cleaned.to_csv(output_file, index=False, encoding='utf-8')
    print(f"Successfully saved {len(df_cleaned)} rows and {len(df_cleaned.columns)} columns.")
except Exception as e:
    print(f"ERROR: Failed to save output file. {e}")

print("\nScript finished.")