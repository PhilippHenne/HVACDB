import pandas as pd
import numpy as np
import os
import re


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


# --- Configuration ---
input_file = 'residentialventilationunits_expanded.csv'  # Your source CSV file name
output_file = 'cleaned_residentialventilationunits.csv' # Output file name

# --- Define Column Mappings and Selections ---

# 1. Define mappings from source CSV column name to target database column name
#    (Verify these source names match your CSV headers EXACTLY, case-insensitively)
#    Source names should be lowercase as we convert headers to lowercase later.
column_mapping = {
    # Common Fields Mappings (Verify source names!)
    'organisation_organisationname': 'manufacturer',         # Assuming 'organisation' is the manufacturer
    'modelidentifier': 'model_identifier',    # Assuming you add model_identifier to base model
    'onmarketstartdate': 'market_entry',      # Assuming this is the correct market entry date
    'onmarketenddate': 'market_exit',        # Assuming this is the correct market exit date
    'soundpowerlevel': 'noise_level_dba', # Mapping ventilation sound to common noise field? Or keep separate?

    # Ventilator Specific Mappings (if source name differs from target)
    # e.g., 'max_flow': 'maximumFlowRate' # If needed
    # Add other necessary remappings here
}

# 2. List ALL target columns you want to KEEP in the final CSV
#    These should match the keys in column_mapping OR original column names (if no mapping needed)
#    Ensure these correspond to your database model fields (common + ventilator specific)
#    Using lowercase based on the analysis in the previous step.
target_columns_to_keep = [
    # Common Fields (target names from mapping or original lowercase name)
    'manufacturer',
    'model_identifier', # Assuming added to base model
    'market_entry',
    'market_exit',      # Added market_exit
    'power_rating_kw', # Keep if still relevant common field
    'noise_level_dba', # Keep if using for common noise level
    'price_currency',
    'price_amount',
    'data_source',      # Will be added manually later
    # 'custom_fields',  # Typically not selected directly, populated from remaining cols later if needed

    # Ventilator Specific Fields (lowercase original names, assuming no mapping needed unless specified above)
    'maximumflowrate',
    'referenceflowrate',
    'referencepressuredifference',
    'typology',
    'heatrecoverysystem',
    'thermalefficiencyheatrecovery',
    'specificpowerinput',           # Key efficiency metric
    'fandrivepowerinput',
    'drivetype',
    'ductedunit',
    'controltypology',
    'specificenergyconsumptionwarm',
    'specificenergyconsumptionaverage',
    'specificenergyconsumptioncold',
    'annualheatingsavedaverageclimate', # Using average as example
    'energyclass',
    'maximuminternalleakagerate',   # Example optional field
    'maximumexternalleakagerate',   # Example optional field

    # Ensure all required fields for your target DB model are listed here
]

# Define columns that should be dates and numeric
date_columns = ['market_entry', 'market_exit']
numeric_columns = [
    'power_rating_kw', 'noise_level_dba', 'price_amount', 'maximumflowrate',
    'referenceflowrate', 'referencepressuredifference', 'thermalefficiencyheatrecovery',
    'specificpowerinput', 'fandrivepowerinput', 'specificenergyconsumptionwarm',
    'specificenergyconsumptionaverage', 'specificenergyconsumptioncold',
    'annualheatingsavedaverageclimate', 'maximuminternalleakagerate', 'maximumexternalleakagerate'
    # Add other numeric fields from target_columns_to_keep
]

# Values in the CSV to be treated as Null/NaN
na_values_list = ['NULL', 'Null', 'null', '', '#N/A', '#N/A N/A', '#NA', '-1.#IND', '-1.#QNAN', '-NaN', '-nan',
                  '1.#IND', '1.#QNAN', '<NA>', 'N/A', 'NA', 'NaN', 'None', 'nan', 'none']

# --- Script Logic ---
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

# Convert original column headers to lowercase for consistent mapping/selection
original_columns = df.columns.tolist() # Keep original case for reporting if needed
df.columns = df.columns.str.lower()
print("Converted column headers to lowercase.")

# Rename columns based on the mapping
df.rename(columns=column_mapping, inplace=True)
print(f"Renamed columns based on mapping: {list(column_mapping.keys())}")

# Add fixed value columns BEFORE filtering columns
df['data_source'] = 'EPREL'
df['device_type'] = 'ventilator' # Use the key defined in DEVICE_TYPES/MODEL_MAP
print("Added 'data_source' and 'device_type' columns.")

# Filter to keep only the target columns
# Ensure all columns in target_columns_to_keep actually exist after renaming
existing_target_columns = [col for col in target_columns_to_keep if col in df.columns]
missing_target_columns = [col for col in target_columns_to_keep if col not in df.columns]

if missing_target_columns:
    print(f"\nWARNING: The following target columns were not found in the input CSV (after renaming):")
    for col in missing_target_columns:
        print(f"- {col}")
    # Decide if this is critical - maybe remove them from existing_target_columns?
    # Or maybe add empty columns? For now, we just select what exists.
    # Example: Add missing columns as empty
    # for col in missing_target_columns:
    #     df[col] = pd.NA

print(f"\nSelecting final columns: {existing_target_columns}")
df_cleaned = df[existing_target_columns].copy() # Use .copy() to avoid SettingWithCopyWarning

# --- Data Cleaning and Type Conversion ---
print("\nConverting data types...")
# Convert date columns
for col in date_columns:
    if col in df_cleaned.columns:
        original_dtype = df_cleaned[col].dtype
        df_cleaned[col] = df_cleaned[col].apply(parse_market_date)
        print(f"- Converted '{col}' (original type: {original_dtype}) to date (errors coerced to NaT).")
    else:
         print(f"- Date column '{col}' not found, skipping conversion.")

# Convert numeric columns
for col in numeric_columns:
    if col in df_cleaned.columns:
        original_dtype = df_cleaned[col].dtype
        df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
        print(f"- Converted '{col}' (original type: {original_dtype}) to numeric (errors coerced to NaN).")
    else:
         print(f"- Numeric column '{col}' not found, skipping conversion.")

# --- Save Output ---
print(f"\nSaving cleaned data to: {output_file}")
try:
    df_cleaned.to_csv(output_file, index=False, encoding='utf-8')
    print(f"Successfully saved {len(df_cleaned)} rows and {len(df_cleaned.columns)} columns.")
except Exception as e:
    print(f"ERROR: Failed to save output file. {e}")

print("\nScript finished.")