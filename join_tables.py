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
    
    # 1. Standardize separators (replace space-padded +, /, - with a single '/')
    #    Be careful with '-' as it might be part of the model name itself.
    #    We primarily target separators between distinct model parts.
    #    This regex looks for space(s), then +, /, or -, then space(s) OR just /
    processed = re.sub(r'\s*[\+/]\s*', '/', original_identifier) 
    # Consider if a pattern like ' - ' specifically needs replacement too, but MXZ-2D33VA uses '-' internally.
    # If '-' sometimes separates units like 'A - B', you might add:
    # processed = re.sub(r'\s+-\s+', '/', processed)

    # 2. Remove common extraneous info (like -E#, (XYZ), trailing letters/numbers)
    #    This is highly specific to your data patterns. Adjust cautiously.
    processed = re.sub(r'-E\d+', '', processed) # Remove -E followed by digits (e.g., -E4)
    processed = re.sub(r'\([^\)]*\)', '', processed) # Remove anything in parentheses (e.g., (B)(S))
    # Optional: Remove trailing version indicators like '3W' - this might be too aggressive if '3W' is significant
    # Be careful not to remove essential model number parts. Example: remove trailing W,B,S maybe?
    # processed = re.sub(r'([A-Z0-9])([WBS]+)$', r'\1', processed) # Example: Attempt to remove trailing W/B/S
    # Let's refine this: remove known suffixes ONLY if preceded by potential model chars
    # Example: Remove 3W, 2B, etc., if they look like suffixes
    processed = re.sub(r'(\d[A-Z]?)(\d[A-Z]+)$', r'\1', processed) # Try removing patterns like VE3W -> VE

    # 3. Split into components based on the standardized separator '/'
    components = [part.strip() for part in processed.split('/') if part.strip()]
    
    if not components:
        return None # Cannot normalize

    # 4. Optional: Further clean individual components if needed (e.g., trim whitespace already done)
    #    Example: Remove trailing non-alphanumeric chars if necessary (use with care)
    #    components = [re.sub(r'[^A-Za-z0-9]$', '', comp) for comp in components]

    # 5. Sort components alphabetically for consistency
    components.sort()
    
    # 6. Join with a standard delimiter
    normalized_key = '|'.join(components)
    
    return normalized_key

# --- Main Script Logic ---
try:
    print(f"Loading data from {FILE_A}...")
    # Construct full paths using os.path.join for better cross-platform compatibility
    df_a = pd.read_csv(os.path.join(os.getcwd(), FILE_A)) 
    print(f"Loaded {len(df_a)} rows.")

    print(f"Loading data from {FILE_B}...")
    df_b = pd.read_csv(os.path.join(os.getcwd(), FILE_B), sep=';') 
    print(f"Loaded {len(df_b)} rows.")

    # Check if ID columns exist
    if ID_COLUMN_A not in df_a.columns:
        raise ValueError(f"Column '{ID_COLUMN_A}' not found in {FILE_A}")
    if ID_COLUMN_B not in df_b.columns:
        raise ValueError(f"Column '{ID_COLUMN_B}' not found in {FILE_B}")

    print(f"\nNormalizing identifiers in {FILE_A} (Column: {ID_COLUMN_A})...")
    df_a['normalized_id'] = df_a[ID_COLUMN_A].apply(normalize_identifier)
    
    # Display some normalization examples from Table A
    print("\nNormalization Examples from Table A:")
    print(df_a[[ID_COLUMN_A, 'normalized_id']].head())
    print(f"Unique normalized IDs created in Table A: {df_a['normalized_id'].nunique()}")


    print(f"\nNormalizing identifiers in {FILE_B} (Column: {ID_COLUMN_B})...")
    df_b['normalized_id'] = df_b[ID_COLUMN_B].apply(normalize_identifier)

    # Display some normalization examples from Table B
    print("\nNormalization Examples from Table B:")
    print(df_b[[ID_COLUMN_B, 'normalized_id']].head())
    print(f"Unique normalized IDs created in Table B: {df_b['normalized_id'].nunique()}")

    # Identify IDs that failed to normalize (result is None or empty)
    failed_a = df_a[df_a['normalized_id'].isna() | (df_a['normalized_id'] == '')]
    failed_b = df_b[df_b['normalized_id'].isna() | (df_b['normalized_id'] == '')]
    if not failed_a.empty:
        print(f"\nWarning: {len(failed_a)} rows in {FILE_A} could not be normalized:")
        print(failed_a[ID_COLUMN_A].head())
    if not failed_b.empty:
        print(f"\nWarning: {len(failed_b)} rows in {FILE_B} could not be normalized:")
        print(failed_b[ID_COLUMN_B].head())

    print("\nMerging the two tables based on 'normalized_id'...")
    # Perform an outer merge to keep all data from both tables
    # Suffixes are added to columns that exist in both DataFrames (except the join key)
    merged_df = pd.merge(
        df_a, 
        df_b, 
        on='normalized_id', 
        how='outer', 
        suffixes=('_A', '_B') 
    )

    print(f"Merge complete. Resulting table has {len(merged_df)} rows.")

    # Analyze the merge results
    # matched_rows = merged_df[merged_df[ID_COLUMN_A + '_A'].notna() & merged_df[ID_COLUMN_B + '_B'].notna()]
    #only_in_a = merged_df[merged_df[ID_COLUMN_A + '_A'].notna() & merged_df[ID_COLUMN_B + '_B'].isna()]
    #only_in_b = merged_df[merged_df[ID_COLUMN_A + '_A'].isna() & merged_df[ID_COLUMN_B + '_B'].notna()]

    #print(f"\nMerge Summary:")
    #print(f"- Rows matched between both tables: {len(matched_rows)}")
    #print(f"- Rows unique to {FILE_A}: {len(only_in_a)}")
    #print(f"- Rows unique to {FILE_B}: {len(only_in_b)}")
    
    # Note: If a normalized ID appears multiple times in either source table, 
    # the merge can result in more rows than the sum of unique A + unique B + matched.

    print(f"\nSaving merged data to {OUTPUT_FILE}...")
    # Make sure the output directory exists if specifying a path
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