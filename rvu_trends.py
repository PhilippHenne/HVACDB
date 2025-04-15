import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

def visualize_flowrate_to_powerinput_trends(df):
    bin_edges = [
        pd.Timestamp.min,          # Start of time
        pd.Timestamp('2016-01-01'), # Start of Tier 1
        pd.Timestamp('2018-01-01'), # Start of Tier 2
        pd.Timestamp.max           # End of time
    ]

    # Define labels for the periods (one less label than bin edges)
    period_labels = [
        'Pre-2016',
        '2016-2017',
        '2018+'
    ]

    # --- 2. Create the 'ecodesign_period' Column ---
    # Use pd.cut to assign each row to a period based on 'market_entry' date
    df['ecodesign_period'] = pd.cut(
        df['market_entry'],
        bins=bin_edges,
        labels=period_labels,
        right=False # Intervals are [start, end), e.g., 2016-01-01 included in '2016-2017'
    )
    print("Created 'ecodesign_period' column.")
    print(df['ecodesign_period'].value_counts()) # See how many devices fall in each period

    # --- 3. Adapt Visualization ---

    # Filter out NaN values needed for plotting
    plot_df = df.dropna(subset=['ecodesign_period', 'maximumflowrate', 'fandrivepowerinput'])

    if plot_df.empty:
        print("No data available for plotting after filtering for periods and metrics.")
    else:
        # --- Option A: Faceted Scatter Plots (Plot per Period) ---
        print("\nGenerating Faceted Scatter Plot...")
        g = sns.relplot(
            data=plot_df,
            x="maximumflowrate",
            y="fandrivepowerinput",
            col="ecodesign_period",  # Facet by the new period column
            col_order=period_labels, # Ensure correct order
            kind="scatter",
            height=4, aspect=1.2,
            # hue="manufacturer", # Optional: add another dimension
            # alpha=0.6
        )
        g.fig.suptitle("Fan Drive Power Input vs. Max Flow Rate by Ecodesign Period", y=1.03)
        g.set_axis_labels("Maximum Flow Rate (m³/h)", "Fan Drive Power Input (W)")
        g.set(xscale="log")
        plt.tight_layout()
        plt.show()

        #print("\nGenerating Scatter Plot with Trend Lines per Period...")
        #sns.lmplot(
        #    data=plot_df,
        #    x="maximumflowrate",
        #    y="specificpowerinput",
        #    hue="ecodesign_period",    # Color points AND fit lines per period
        #    hue_order=period_labels,  # Ensure correct order
        #    palette="viridis",
        #    height=6, aspect=1.5,
        #    # scatter_kws={'s': 20, 'alpha': 0.6},
        #    # ci=None, # Turn off confidence intervals if desired
        #    # legend_out=True
        #)
        #plt.title("Specific Power Input vs. Max Flow Rate by Ecodesign Period")
        #plt.xlabel("Maximum Flow Rate (m³/h)")
        ##plt.ylabel("Specific Power Input (W/(m³/h))")
        #plt.grid(True, linestyle='--', alpha=0.7)
        #plt.tight_layout()
        #plt.show()