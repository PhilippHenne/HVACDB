import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick 
import sqlalchemy


db_connection_str = 'postgresql://postgres:password@localhost/HVACDevices'
db_connection = sqlalchemy.create_engine(db_connection_str)

sql_query = "SELECT base.market_entry as market_entry, ac.refrigerant_gwp as refrigerant_gwp FROM hvacdevices AS base INNER JOIN air_conditioners AS ac ON base.id = ac.id WHERE device_type = 'air_conditioner' AND market_entry >= '2010-01-01' AND ac.refrigerant_gwp IS NOT NULL;"

try:
    raw_df = pd.read_sql(sql_query, db_connection)
    print("Data loaded successfully:")
    print(raw_df.head())
    print("\nData Info:")
    print(raw_df.info())
except Exception as e:
    print(f"Error loading data: {e}")
finally:
    if 'db_connection' in locals() and hasattr(db_connection, 'dispose'):
        db_connection.dispose() # Close the connection


if not raw_df.empty:
    print("Processing GWP data...")
    raw_df['market_entry'] = pd.to_datetime(raw_df['market_entry'], errors='coerce')
    raw_df = raw_df.dropna(subset=['market_entry']) 
    raw_df['entry_year'] = raw_df['market_entry'].dt.year
    
    raw_df['refrigerant_gwp'] = pd.to_numeric(raw_df['refrigerant_gwp'], errors='coerce')
    raw_df = raw_df.dropna(subset=['refrigerant_gwp'])

    gwp_bins = [-float('inf'), 9.99, 749.99, float('inf')] 
    gwp_labels = ['GWP < 10', 'GWP 10-749', 'GWP >= 750']
    
    raw_df['gwp_category'] = pd.cut(raw_df['refrigerant_gwp'], bins=gwp_bins, labels=gwp_labels, right=True)

    yearly_counts = raw_df.groupby(['entry_year', 'gwp_category']).size().unstack(fill_value=0)
    
    yearly_shares = yearly_counts.apply(lambda x: x / x.sum() * 100, axis=1)
    
    print("\n--- Yearly GWP Category Shares (%) ---")
    print(yearly_shares.round(1))

    print("\nGenerating GWP share plot...")
    fig, ax = plt.subplots(figsize=(10, 8))
    
    yearly_shares.plot(kind='area', stacked=True, ax=ax, 
                       colormap='viridis_r') 

    ax.set_xlabel('Year of Market Entry', size=14)
    ax.set_ylabel('Percentage Share of Models Introduced (%)', size=14)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.legend(title='GWP Category', bbox_to_anchor=(0.5, -0.1), loc='upper center', ncol=4, fontsize='large')
    ax.grid(True, axis='y', linestyle='--', alpha=0.6)
    plt.tight_layout(rect=[0, 0, 0.98, 1])
    plt.show()
    #plt.savefig('gwp_trends.png', dpi=300)

else:
    print("No data found for GWP analysis.")