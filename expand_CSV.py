import pandas as pd
import json
import ast

def extract_nested_json_columns(input_csv, output_csv=None, columns_to_extract=None):
    """
    Extract nested JSON columns into separate columns.
    
    Args:
    input_csv (str): Path to the input CSV file
    output_csv (str, optional): Path to save the expanded CSV
    columns_to_extract (list, optional): List of column names to extract nested JSON from
    
    Returns:
    pandas.DataFrame: DataFrame with extracted columns
    """
    # Read the CSV
    df = pd.read_csv(input_csv)
    
    # Function to safely parse JSON-like strings
    def parse_nested_json(field):
        if pd.isna(field) or field == 'None':
            return {}
        
        try:
            # Try parsing as JSON first
            if isinstance(field, str):
                # Handle string representations of dictionaries
                try:
                    # First try json.loads
                    parsed = json.loads(field.replace("'", '"'))
                except json.JSONDecodeError:
                    # If that fails, try ast.literal_eval
                    try:
                        parsed = ast.literal_eval(field)
                    except (ValueError, SyntaxError):
                        # If all parsing fails, return empty dict
                        return {}
                
                return parsed
            return field
        except Exception as e:
            print(f"Error parsing field {field}: {e}")
            return {}
    
    # If columns to extract not specified, try to detect
    if columns_to_extract is None:
        columns_to_extract = ['organisation', 'heatingCharacteristics', 'coolingCharacteristics', 'contactDetails']
    
    # Process each specified column
    for col in columns_to_extract:
        if col in df.columns:
            # Parse the nested JSON
            parsed_col = df[col].apply(parse_nested_json)
            
            # Extract all unique keys from the parsed column
            all_keys = set()
            for item in parsed_col:
                all_keys.update(item.keys())
            
            # Create new columns for each key
            for key in all_keys:
                new_col_name = f"{col}_{key}"
                # Extract the specific key, using None if not present
                df[new_col_name] = parsed_col.apply(lambda x: x.get(key))
            
            # Optionally, drop the original nested column
            df = df.drop(columns=[col])
    
    # Save the expanded DataFrame
    if output_csv is None:
        output_csv = input_csv.rsplit('.', 1)[0] + '_nested_expanded.csv'
    
    df.to_csv(output_csv, index=False)
    
    print(f"Expanded CSV saved to {output_csv}")
    print(f"Total columns after expansion: {len(df.columns)}")
    
    return df

def main():
    # Example usage
    input_csv = 'airconditioners_1.csv'  # Your input CSV file
    output_csv = 'airconditioners_1_expanded.csv'  # Optional output file path
    
    # Specific columns to extract (optional)
    columns_to_extract = ['organisation', 'heatingCharacteristics', 'coolingCharacteristics', 'contactDetails']
    
    expanded_df = extract_nested_json_columns(input_csv, output_csv, columns_to_extract)

if __name__ == "__main__":
    main()