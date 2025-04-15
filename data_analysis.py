import os
import pandas as pd
from sqlalchemy import create_engine, text
from overall_efficiency_trends import analyze_overall_efficiency_trends_ac, visualize_overall_efficiency_trends_ac
from rvu_trends import visualize_flowrate_to_powerinput_trends
# --- Configuration ---
DATABASE_URI = os.getenv('DATABASE_URL')


if not DATABASE_URI:
    raise ValueError("DATABASE_URI environment variable not set. Please set it before running.")

# --- Database Connection ---

try:
    print("Connecting to database...")
    engine = create_engine(DATABASE_URI)
    # Test connection (optional but recommended)
    with engine.connect() as connection:
        print("Database connection successful.")
except Exception as e:
    print(f"ERROR: Failed to connect to database.")
    print(f"URI Used: {DATABASE_URI}") # Be careful logging URIs if they contain passwords
    print(f"Error details: {e}")
    exit()

# --- SQL Querys ---

AC_PERFORMANCE_QUERY = """
SELECT
    base.manufacturer,
    base.market_entry AS Date,
    ac.seer AS rating_to_test
FROM
    hvacdevices AS base
INNER JOIN
    air_conditioners AS ac ON base.id = ac.id
WHERE
    base.device_type = 'air_conditioner'
    AND ac.seer IS NOT NULL 
    AND ac.seer BETWEEN 1.1 AND 28.0
    AND base.market_entry IS NOT NULL
"""

RVU_PERFORMANCE_QUERY = """
SELECT
    base.manufacturer,
	base.market_entry AS date,
    v.maximumflowrate AS maximumflowrate,
    v.specificpowerinput AS rating_to_test,
    v.fandrivepowerinput AS fandrivepowerinput
FROM
    hvacdevices AS base
INNER JOIN
    residential_ventilation_units AS v ON base.id = v.id
WHERE
    base.device_type = 'residential_ventilation_unit'
    AND v.maximumflowrate IS NOT NULL
    AND v.fandrivepowerinput < 2000
    AND (v.specificpowerinput IS NOT NULL OR v.fandrivepowerinput IS NOT NULL);
"""

# --- Data Fetching Function ---

def fetch_data(db_engine, query):
    """
    Fetches air conditioner performance data from the database.

    Args:
        db_engine: SQLAlchemy engine instance.

    Returns:
        pandas.DataFrame: DataFrame containing manufacturer, market_entry, and seer,
                          or None if an error occurs.
    """
    print("Fetching air conditioner performance data...")
    try:
        with db_engine.connect() as connection:
            # Use pd.read_sql with text() for safe query execution
            df = pd.read_sql(text(query), connection)
        print(f"Successfully fetched {len(df)} records.")
        return df
    except Exception as e:
        print(f"ERROR: Failed to fetch data.")
        print(f"Error details: {e}")
        return None


if __name__ == "__main__":
    # 1. Fetch data
    data_df = fetch_data(engine, RVU_PERFORMANCE_QUERY)

    if data_df is not None and not data_df.empty:
        print("\n--- Data Overview ---")
        print(f"Shape: {data_df.shape}")
        print("First 5 rows:\n", data_df.head())
        print("\nData Types:\n", data_df.dtypes)

        # 2. Analyze data (Call your analysis function here)
        analysis_results = analyze_overall_efficiency_trends_ac(data_df)

        # 3. Visualize results (Call your visualization function here)
        visualize_overall_efficiency_trends_ac(analysis_results)
        #visualize_flowrate_to_powerinput_trends(data_df)
    else:
        print("\nNo data loaded, skipping analysis and visualization.")

    print("\n--- Script Execution Complete ---")