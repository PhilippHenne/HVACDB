import pandas as pd
import re
import os # Import os module for file path joining

# --- Configuration ---
# Adjust these paths and column names to match your files
FILE_A = 'airconditioners_1_expanded.csv' # Path to your first CSV file
FILE_B = '20250314_135815_exportAC.csv' # Path to your second CSV file
OUTPUT_FILE = 'merged_hvac_data.csv' # Name for the output file

ID_COLUMN_A = 'modelIdentifier' # Name of the identifier column in FILE_A
ID_COLUMN_B = 'MODEL_NAME' # Name of the identifier column in FILE_B
# --- End Configuration ---

def normalize_identifier(identifier):
    """
    Attempts to normalize complex HVAC model identifiers into a standard format.
    Example A: "MXZ-2D33VA-E4 / MSZ-SF15VA + MSZ-EF18VE"
    Example B: "MXZ-2D33VA/MSZ-SF15VA/MSZ-EF18VE3W(B)(S)"
    Target Normalized: "MXZ-2D33VA|MSZ-EF18VE|MSZ-SF15VA" (sorted components)
    """
    if pd.isna(identifier):
        return None
    
    original_identifier = str(identifier) # Ensure it's a string
    
    processed = re.sub(r'\s*[\+/]\s*', '/', original_identifier) 
    processed = re.sub(r'-E\d+', '', processed) # Remove -E followed by digits (e.g., -E4)
    processed = re.sub(r'\([^\)]*\)', '', processed) # Remove anything in parentheses (e.g., (B)(S))
    processed = re.sub(r'(\d[A-Z]?)(\d[A-Z]+)$', r'\1', processed) # Try removing patterns like VE3W -> VE

    components = [part.strip() for part in processed.split('/') if part.strip()]
    
    if not components:
        return None 

    components = [re.sub(r'[^A-Za-z0-9]$', '', comp) for comp in components]

    components.sort()
    
    normalized_key = '|'.join(components)
    
    return normalized_key

try:
    print(f"Loading data from {FILE_A}...")
    df_a = pd.read_csv(os.path.join(os.getcwd(), FILE_A)) 
    print(f"Loaded {len(df_a)} rows.")

    print(f"Loading data from {FILE_B}...")
    df_b = pd.read_csv(os.path.join(os.getcwd(), FILE_B), sep=';') 
    print(f"Loaded {len(df_b)} rows.")

    if ID_COLUMN_A not in df_a.columns:
        raise ValueError(f"Column '{ID_COLUMN_A}' not found in {FILE_A}")
    if ID_COLUMN_B not in df_b.columns:
        raise ValueError(f"Column '{ID_COLUMN_B}' not found in {FILE_B}")

    print(f"\nNormalizing identifiers in {FILE_A} (Column: {ID_COLUMN_A})...")
    df_a['normalized_id'] = df_a[ID_COLUMN_A].apply(normalize_identifier)
    
    print("\nNormalization Examples from Table A:")
    print(df_a[[ID_COLUMN_A, 'normalized_id']].head())
    print(f"Unique normalized IDs created in Table A: {df_a['normalized_id'].nunique()}")


    print(f"\nNormalizing identifiers in {FILE_B} (Column: {ID_COLUMN_B})...")
    df_b['normalized_id'] = df_b[ID_COLUMN_B].apply(normalize_identifier)

    print("\nNormalization Examples from Table B:")
    print(df_b[[ID_COLUMN_B, 'normalized_id']].head())
    print(f"Unique normalized IDs created in Table B: {df_b['normalized_id'].nunique()}")

    failed_a = df_a[df_a['normalized_id'].isna() | (df_a['normalized_id'] == '')]
    failed_b = df_b[df_b['normalized_id'].isna() | (df_b['normalized_id'] == '')]
    if not failed_a.empty:
        print(f"\nWarning: {len(failed_a)} rows in {FILE_A} could not be normalized:")
        print(failed_a[ID_COLUMN_A].head())
    if not failed_b.empty:
        print(f"\nWarning: {len(failed_b)} rows in {FILE_B} could not be normalized:")
        print(failed_b[ID_COLUMN_B].head())

    print("\nMerging the two tables based on 'normalized_id'...")
    merged_df = pd.merge(
        df_a, 
        df_b, 
        on='normalized_id', 
        how='outer', 
        suffixes=('_A', '_B') 
    )

    print(f"Merge complete. Resulting table has {len(merged_df)} rows.")


    print(f"\nSaving merged data to {OUTPUT_FILE}...")
    output_dir = os.path.dirname(OUTPUT_FILE)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    merged_df.to_csv(os.path.join(os.getcwd(), OUTPUT_FILE), index=False)
    print("Done.")

except FileNotFoundError as e:
    print(f"Error: File not found. Please check the paths. Details: {e}")
except ValueError as e:
    print(f"Error: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")