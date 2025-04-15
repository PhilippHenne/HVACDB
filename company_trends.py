import pandas as pd
import sqlalchemy
import pandas as pd
import numpy as np
from scipy.stats import linregress
import matplotlib.pyplot as plt
import seaborn as sns
import re
import unicodedata


# --- Configuration ---
DB_PATH = 'postgresql://postgres:password@localhost/HVACDevices'
TABLE_NAME = 'hvac_devices'
MANUFACTURER_COL = 'manufacturer'
RATING_COL = 'seer'
YEAR_COL = 'market_entry'
MIN_DATA_POINTS_PER_MANUFACTURER = 3
EXTRACTED_YEAR_COL = 'Year_Extracted'

def connect_db(db_path):
    conn = sqlalchemy.create_engine(db_path)
    print("Database connected successfully.")
    return conn

def fetch_data(conn, query):
    try:
        df = pd.read_sql_query(query, conn)
        print(f"Fetched {len(df)} rows.")
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame() # Return empty DataFrame on error
    

def normalize_string(s):
    """Normalizes strings: lowercase, removes accents, removes special chars."""
    if not isinstance(s, str):
        s = str(s)
    s = s.lower()
    # Remove accents (like é -> e)
    s = ''.join(c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn')
    # Remove non-alphanumeric characters (allow spaces)
    s = re.sub(r'[^\w\s]', '', s)
    # Consolidate whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    # Optional: Add specific common replacements
    # s = s.replace(' corp', ' corporation').replace(' inc', '')
    return s

def clean_data(df, manufacturer_col, rating_col, date_col, extracted_year_col, min_year=None):
    """Cleans the DataFrame: handles dates, extracts year, normalizes."""
    print("Cleaning data...")
    # Drop rows with missing essential data before processing
    df = df.dropna(subset=[manufacturer_col, rating_col, date_col])
    if df.empty:
        print("DataFrame empty after initial dropna.")
        return df

    # --- Date Handling ---
    print(f"Parsing date column: {date_col}")
    # Convert the date column to datetime objects. 'coerce' turns errors into NaT (Not a Time).
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

    # Drop rows where date parsing failed
    original_rows = len(df)
    df = df.dropna(subset=[date_col])
    if len(df) < original_rows:
        print(f"Dropped {original_rows - len(df)} rows due to invalid dates.")

    if df.empty:
        print("DataFrame empty after dropping invalid dates.")
        return df

    # Extract the year into a new column
    df[extracted_year_col] = df[date_col].dt.year
    # --- End Date Handling ---

    # Normalize manufacturer names
    df['Manufacturer_Clean'] = df[manufacturer_col].apply(normalize_string)

    # Convert rating column to numeric
    df[rating_col] = pd.to_numeric(df[rating_col], errors='coerce')

    # Drop rows where rating conversion failed or year is missing (shouldn't happen after NaT drop)
    df = df.dropna(subset=[rating_col, extracted_year_col])
    if df.empty:
        print("DataFrame empty after dropping NaN ratings/years.")
        return df
        
    # Ensure extracted year is integer
    df[extracted_year_col] = df[extracted_year_col].astype(int)

    # Apply year filtering (if specified) *after* extraction
    if min_year is not None:
        original_rows = len(df)
        df = df[df[extracted_year_col] >= min_year]
        if len(df) < original_rows:
             print(f"Filtered out {original_rows - len(df)} rows based on year < {min_year}.")


    print(f"Data cleaned. {len(df)} rows remaining.")
    return df

def analyze_manufacturer_trends(df, manufacturer_col='Manufacturer_Clean', year_col=EXTRACTED_YEAR_COL, rating_col=RATING_COL, min_points=MIN_DATA_POINTS_PER_MANUFACTURER):
    """Analyzes trends per manufacturer using the extracted year."""
    print(f"Analyzing trends per manufacturer based on column: {year_col}...")
    if year_col not in df.columns:
         print(f"Error: Expected year column '{year_col}' not found in DataFrame.")
         return pd.DataFrame() # Return empty DataFrame

    # Calculate average rating per manufacturer per year (using the EXTRACTED year)
    yearly_avg = df.groupby([manufacturer_col, year_col])[rating_col].mean().reset_index()

    results = []
    # Group by the cleaned manufacturer name
    for manufacturer, group in yearly_avg.groupby(manufacturer_col):
        # Need enough data points (distinct years) for a meaningful trend
        if len(group[year_col].unique()) >= min_points: # Check unique years
            group = group.sort_values(by=year_col)
            years = group[year_col].values # Use the extracted years for regression
            ratings = group[rating_col].values

            # Calculate overall average rating for this manufacturer using original data
            # Ensure we filter the original df correctly using Manufacturer_Clean
            overall_avg_rating = df[df[manufacturer_col] == manufacturer][rating_col].mean()

            # Calculate growth rate using linear regression (slope of rating vs EXTRACTED year)
            try:
                if np.var(years) > 0:
                     slope, intercept, r_value, p_value, std_err = linregress(years, ratings)
                else:
                     slope = 0.0
                     r_value = 0.0
                     p_value = 1.0

                if np.isnan(slope): slope = 0.0 # Handle rare NaN cases

                results.append({
                    'Manufacturer': manufacturer,
                    'Overall_Avg_Rating': overall_avg_rating,
                    'Rating_Growth_Rate': slope,
                    'R_Squared': r_value**2 if 'r_value' in locals() else 0.0,
                    'P_Value': p_value if 'p_value' in locals() else 1.0,
                    'Num_Years_Data': len(group[year_col].unique()), # Count unique years
                    'First_Year': group[year_col].min(),
                    'Last_Year': group[year_col].max()
                })
            except Exception as e:
                 print(f"Could not calculate trend for {manufacturer}: {e}")

    analysis_df = pd.DataFrame(results)
    print(f"Analysis complete. Found trends for {len(analysis_df)} manufacturers.")
    return analysis_df


# --- Visualization Functions ---

def plot_trends(analysis_df, avg_rating_col='Overall_Avg_Rating', growth_rate_col='Rating_Growth_Rate'):
    """Plots Average Rating vs Growth Rate, adjusting ylim for visibility."""
    if analysis_df.empty or growth_rate_col not in analysis_df.columns:
        print("No data or growth rate column found to plot.")
        return
    
    # Drop rows with NaN growth rates if any exist before calculating limits
    valid_growth_rates = analysis_df[growth_rate_col].dropna()

    if valid_growth_rates.empty:
        print("No valid growth rate data to determine plot limits.")
        return

    print("Generating plot with adjusted y-axis limits...")
    plt.figure(figsize=(14, 9)) # You can adjust figsize, e.g., (12, 10) might give more vertical space

    scatter = sns.scatterplot(
        data=analysis_df,
        x=avg_rating_col,
        y=growth_rate_col,
        size='Num_Years_Data',
        hue='R_Squared',
        palette='viridis',
        sizes=(50, 500),
        alpha=0.7,
        legend='auto'
    )

    plt.title(f'Manufacturer {RATING_COL} Growth Rate vs. Overall Average {RATING_COL}')
    plt.xlabel(f'Overall Average {RATING_COL}')
    plt.ylabel(f'{RATING_COL} Growth Rate per year')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.axhline(0, color='grey', linestyle='--', linewidth=1)

    # --- Adjust Y-axis limits ---
    min_growth = valid_growth_rates.min()
    max_growth = valid_growth_rates.max()

    # Add a margin (e.g., 10% of the range) to prevent points sitting exactly on the edge
    data_range = max_growth - min_growth
    
    # Handle cases where range is zero or very small
    if data_range < 1e-6 : # Effectively zero range
        margin = 0.1 # Use a default margin if all points are the same
    else:
        margin = data_range * 0.10 # 10% margin

    # Ensure margin is at least a small absolute value for visibility if range is tiny
    margin = max(margin, 0.02) 

    lower_limit = min_growth - margin
    upper_limit = max_growth + margin

    # Ensure the y=0 line is visible if the data range includes or is near zero
    if lower_limit > 0:
        lower_limit = min(0, lower_limit) # Ensure 0 is included if rates are all positive but close to 0
    if upper_limit < 0:
        upper_limit = max(0, upper_limit) # Ensure 0 is included if rates are all negative but close to 0

    plt.ylim(lower_limit, upper_limit)
    print(f"Adjusted y-axis limits to ({lower_limit:.3f}, {upper_limit:.3f})")
    # --- End of Y-axis adjustment ---

    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
    plt.tight_layout(rect=[0, 0, 0.85, 1])
    plt.savefig('company_trends_seer.png', dpi=300)
    plt.show()

if __name__ == "__main__":
    # 1. Define SQL Query
    sql_query = f"""
    SELECT
        "{MANUFACTURER_COL}",
        "{YEAR_COL}",
        "{RATING_COL}"
    FROM
        "{TABLE_NAME}" as base
    INNER JOIN
    WHERE 
        "{RATING_COL}" 
        BETWEEN 1.1 AND 28.0;
    """

    # 2. Connect to DB
    conn = connect_db(DB_PATH)

    if conn:
        # 3. Fetch Data
        raw_df = pd.read_sql_query(sql_query, conn)
        conn.dispose() # Close connection once data is fetched

        if not raw_df.empty:
            # 4. Clean Data - Pass the original date column name and the desired extracted year column name
            cleaned_df = clean_data(
                raw_df,
                manufacturer_col=MANUFACTURER_COL,
                rating_col=RATING_COL,
                date_col=YEAR_COL, # The original date column
                extracted_year_col=EXTRACTED_YEAR_COL, # The new column to create
            )

            if not cleaned_df.empty:
                # 5. Analyze Trends - It will now use EXTRACTED_YEAR_COL by default
                trend_analysis = analyze_manufacturer_trends(
                    cleaned_df,
                    # No need to specify year_col if default was updated
                    min_points=MIN_DATA_POINTS_PER_MANUFACTURER
                )

                # ... (rest of the main block: printing results, plotting) ...
                if not trend_analysis.empty:
                    print("\n--- Trend Analysis Summary ---")
                    print(trend_analysis.sort_values(by='Rating_Growth_Rate', ascending=False).head())
                    print("\n--- Manufacturers with Highest Average Rating ---")
                    print(trend_analysis.sort_values(by='Overall_Avg_Rating', ascending=False).head())
                    # Call the plot function (make sure it's the version with adjusted ylim if you liked that)
                    plot_trends(trend_analysis)
                else:
                    print("Trend analysis resulted in no data to plot.")

            else:
                print("No data remaining after cleaning.")
        else:
            print("No data fetched from the database.")
    else:
        print("Database connection failed. Exiting.")