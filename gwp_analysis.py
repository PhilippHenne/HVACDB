import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick # For formatting y-axis as percentage
import sqlalchemy

# --- Assume 'raw_df' is the DataFrame loaded from the SQL query above ---
# Example:
# conn = sqlite3.connect(DB_PATH)
# sql_query = """SELECT market_entry, refrigerant_gwp FROM your_table WHERE market_entry >= '2010-01-01' AND refrigerant_gwp IS NOT NULL;"""
# raw_df = pd.read_sql_query(sql_query, conn)
# conn.close()

db_connection_str = 'postgresql://postgres:password@localhost/HVACDevices' # Example for SQLite
db_connection = sqlalchemy.create_engine(db_connection_str)

sql_query = "SELECT base.market_entry as market_entry, ac.refrigerant_gwp as refrigerant_gwp FROM hvacdevices AS base INNER JOIN air_conditioners AS ac ON base.id = ac.id WHERE device_type = 'air_conditioner' AND market_entry >= '2010-01-01' AND ac.refrigerant_gwp IS NOT NULL;"

try:
    raw_df = pd.read_sql(sql_query, db_connection)
    print("Data loaded successfully:")
    print(raw_df.head())
    print("\nData Info:")
    print(raw_df.info()) # Useful to check data types, non-null counts
except Exception as e:
    print(f"Error loading data: {e}")
finally:
    if 'db_connection' in locals() and hasattr(db_connection, 'dispose'):
        db_connection.dispose() # Close the connection


if not raw_df.empty:
    print("Processing GWP data...")
    # Convert market_entry to datetime and extract year
    raw_df['market_entry'] = pd.to_datetime(raw_df['market_entry'], errors='coerce')
    raw_df = raw_df.dropna(subset=['market_entry']) # Drop rows where date conversion failed
    raw_df['entry_year'] = raw_df['market_entry'].dt.year
    
    # Ensure GWP is numeric
    raw_df['refrigerant_gwp'] = pd.to_numeric(raw_df['refrigerant_gwp'], errors='coerce')
    raw_df = raw_df.dropna(subset=['refrigerant_gwp'])

    # --- Define GWP Bands ---
    # Adjust bands and labels as needed
    gwp_bins = [-float('inf'), 9.99, 149.99, 749.99, float('inf')] 
    gwp_labels = ['GWP < 10', 'GWP 10-149', 'GWP 150-749', 'GWP >= 750']
    
    # Create a new column for the GWP category
    raw_df['gwp_category'] = pd.cut(raw_df['refrigerant_gwp'], bins=gwp_bins, labels=gwp_labels, right=True)

    # --- Calculate Yearly Shares ---
    # Count models per year per GWP category
    yearly_counts = raw_df.groupby(['entry_year', 'gwp_category']).size().unstack(fill_value=0)
    
    # Calculate percentage share
    yearly_shares = yearly_counts.apply(lambda x: x / x.sum() * 100, axis=1)
    
    print("\n--- Yearly GWP Category Shares (%) ---")
    print(yearly_shares.round(1))

    # --- Visualization ---
    print("\nGenerating GWP share plot...")
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Use a stacked area chart for smooth trends, or stacked bar chart
    yearly_shares.plot(kind='area', stacked=True, ax=ax, 
                       colormap='viridis_r') # Use a colormap, _r reverses it
                       # Or use kind='bar' for bars

    ax.set_title('Development of Refrigerant GWP Category Shares Over Time (Based on Market Entry)')
    ax.set_xlabel('Year of Market Entry')
    ax.set_ylabel('Percentage Share of Models Introduced (%)')
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.legend(title='GWP Category', bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.grid(True, axis='y', linestyle='--', alpha=0.6)
    plt.tight_layout(rect=[0, 0, 0.85, 1]) # Adjust layout for legend
    plt.show()
    plt.savefig('gwp_trends.png', dpi=300)

else:
    print("No data found for GWP analysis.")