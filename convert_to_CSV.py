import json
import csv
import pandas as pd

def convert_json_to_csv(json_file_path, csv_file_path, encoding='utf-8'):
    """
    Convert a JSON file to CSV with robust encoding handling.
    
    Args:
    json_file_path (str): Path to the input JSON file
    csv_file_path (str): Path to the output CSV file
    encoding (str): File encoding to use (default is utf-8)
    """
    try:
        # Read JSON file with specified encoding and error handling
        with open(json_file_path, 'r', encoding=encoding, errors='replace') as json_file:
            data = json.load(json_file)
        
        # Convert to pandas DataFrame
        # Handle different possible JSON structures
        if isinstance(data, list):
            # If JSON is a list of dictionaries
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            # If JSON is a nested dictionary, try to flatten it
            df = pd.json_normalize(data)
        else:
            raise ValueError("Unsupported JSON structure. Must be a list of dictionaries or a dictionary.")
        
        # Write to CSV with UTF-8 encoding
        df.to_csv(csv_file_path, index=False, encoding='utf-8', errors='replace')
        
        print(f"Successfully converted {json_file_path} to {csv_file_path}")
        print(f"Rows: {len(df)}, Columns: {len(df.columns)}")
    
    except Exception as e:
        print(f"Error converting JSON to CSV: {e}")

def detect_file_encoding(file_path):
    """
    Try to detect the file encoding.
    
    Args:
    file_path (str): Path to the file
    
    Returns:
    str: Detected or suggested encoding
    """
    # List of encodings to try
    encodings_to_try = [
        'utf-8', 
        'latin-1',  # Often works as a fallback
        'cp1252',   # Windows default encoding
        'iso-8859-1'
    ]
    
    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                file.read()
            return encoding
        except UnicodeDecodeError:
            continue
    
    return 'utf-8'  # Default fallback

def main():
    # Example usage
    json_file_path = 'residentialventilationunits.json'  # Replace with your JSON file path
    csv_file_path = 'residentialventilationunits.csv'   # Replace with desired CSV output path
    
    # Detect encoding
    detected_encoding = detect_file_encoding(json_file_path)
    print(f"Detected encoding: {detected_encoding}")
    
    # Convert using detected encoding
    convert_json_to_csv(json_file_path, csv_file_path, encoding=detected_encoding)

if __name__ == "__main__":
    main()

