import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np # For numerical operations if needed
import statsmodels.formula.api as smf # For regression with R-style formulas
import matplotlib.dates as mdates 
import math 

def analyze_overall_efficiency_trends_ac(df):
    if 'df' in locals() and 'date' in df.columns and 'rating_to_test' in df.columns:
        try:
            # --- Convert 'date' column to datetime objects ---
            df['date'] = pd.to_datetime(df['date'], errors='coerce')

            # --- Convert 'rating_to_test' to numeric ---
            df['rating_to_test'] = pd.to_numeric(df['rating_to_test'], errors='coerce')

            # --- Drop rows where Date or SEER couldn't be parsed ---
            df.dropna(subset=['date', 'rating_to_test'], inplace=True)

            # --- Sort by Date (important for time series analysis) ---
            df.sort_values('date', inplace=True)

            # --- Aggregate data by Month ---
            df_indexed = df.set_index('date')

            # Calculate monthly average SEER
            monthly_avg_seer = df_indexed['rating_to_test'].resample('ME').mean().reset_index()
            # 'ME' stands for Month End frequency. Use 'MS' for Month Start if preferred.

            monthly_avg_seer.dropna(inplace=True)

            print("\n--- Monthly Average SEER Data ---")
            print(monthly_avg_seer.head())

            # --- Prepare data for regression: Convert Date to numeric (ordinal) ---
            monthly_avg_seer['Date_Ordinal'] = monthly_avg_seer['date'].apply(lambda date: date.toordinal())

        except KeyError as e:
            print(f"Error: Column not found - {e}. Make sure 'date' and 'rating_to_test' columns exist.")
        except Exception as e:
            print(f"Error during data preparation: {e}")
    else:
        print("DataFrame 'df' or required columns ('date', 'rating_to_test') not found.")


    try:
        # Use the ordinal date for regression
        model_monthly = smf.ols('rating_to_test ~ Date_Ordinal', data=monthly_avg_seer).fit()

        print("\n--- Regression Analysis: Monthly Average SEER Rating vs. Time ---")
        print(model_monthly.summary())

        # Extract results
        slope_monthly = model_monthly.params['Date_Ordinal']
        p_value_monthly = model_monthly.pvalues['Date_Ordinal']
        r_squared_monthly = model_monthly.rsquared

        # Note: Slope is now "change in SEER per *day*". Multiply by ~30.4 for approx monthly change.
        print(f"\nSlope (Change in Avg SEER per Day): {slope_monthly:.5f}")
        print(f"Approx. Change per Month: {slope_monthly * 30.4:.4f}")
        print(f"P-value for Time coefficient: {p_value_monthly:.4f}")
        print(f"R-squared: {r_squared_monthly:.3f}")

        # Add prediction line to the DataFrame
        monthly_avg_seer['Predicted_SEER'] = model_monthly.predict(monthly_avg_seer['Date_Ordinal'])


    except Exception as e:
        print(f"Error during monthly regression analysis: {e}")


# --- Calculate High Performers (e.g., 95th percentile) per Month ---
    quantile_threshold = 0.90
    high_perf_col_name = f'Avg_SEER_Top_{int(quantile_threshold*100)}p'

    # Group by month, then calculate threshold and average of top performers within each month
    # This requires a custom function with groupby().apply()
    def calculate_monthly_high_performers(monthly_seer_values):
        """
        Calculates the average SEER rating of the top performers within a monthly group.
        Args:
            monthly_seer_values (pd.Series): A Series containing the SEER rating values
                                            for a specific month, indexed by date.
        Returns:
            float: The average SEER rating of the top performers, or np.nan if calculation fails.
        """
        # --- Debugging Start ---
        group_month_str = monthly_seer_values.name.strftime('%Y-%m') if hasattr(monthly_seer_values, 'name') and monthly_seer_values.name else "Unknown Month"
        print(f"\n--- Processing Group for Month: {group_month_str} ---")
        print(f"Input Series sample:\n{monthly_seer_values.head()}")
        print(f"Input Series dtype: {monthly_seer_values.dtype}")
        print(f"Input Series is empty: {monthly_seer_values.empty}")
        # --- Debugging End ---

        # 1. Handle empty input Series (no data for the month)
        if monthly_seer_values.empty:
            print(f"Group {group_month_str} is empty. Returning NaN.")
            return np.nan

        # 2. Ensure data is numeric (though dtype suggests it is, this adds safety)
        #    Coerce errors just in case, and drop NaNs resulting from coercion or already present.
        seer_numeric = pd.to_numeric(monthly_seer_values, errors='coerce')
        seer_numeric.dropna(inplace=True)

        if seer_numeric.empty:
            print(f"No valid numeric data remaining in group {group_month_str} after cleaning. Returning NaN.")
            return np.nan

        try:
            # 3. Calculate the threshold directly on the numeric Series
            threshold = seer_numeric.quantile(quantile_threshold)
            # print(f"Calculated threshold for {group_month_str}: {threshold}") # Optional

        except Exception as e:
            print(f"ERROR calculating quantile for group {group_month_str}: {e}")
            return np.nan

        # 4. Filter the numeric Series to get top performers
        top_performers = seer_numeric[seer_numeric >= threshold]

        if top_performers.empty:
            # print(f"No top performers found >= threshold {threshold} in group {group_month_str}.") # Optional
            return np.nan # Return NaN if no device meets the threshold

        # 5. Calculate the mean of the top performers
        try:
            final_mean = top_performers.mean()
            # print(f"Calculated mean for top performers in {group_month_str}: {final_mean}") # Optional
            return final_mean
        except Exception as e:
            print(f"ERROR calculating mean for top performers in {group_month_str}: {e}")
            return np.nan

    # Apply the function to each monthly group
    # Resample creates the monthly bins, then we apply our function
    try:
        print("\nApplying high performer calculation...")
        # Apply the revised function to the 'rating_to_test' Series after resampling
        monthly_hp_avg_seer_series = df_indexed['rating_to_test'].resample('ME').apply(calculate_monthly_high_performers)

        # Convert the resulting Series to a DataFrame
        monthly_hp_avg_seer = monthly_hp_avg_seer_series.reset_index()

        # Rename the results column appropriately
        monthly_hp_avg_seer.rename(columns={monthly_hp_avg_seer.columns[1]: high_perf_col_name}, inplace=True)

        # Optional: Drop months where calculation resulted in NaN
        monthly_hp_avg_seer.dropna(subset=[high_perf_col_name], inplace=True)

        print("\n--- Monthly High Performer Trend Data (Recalculated) ---")
        if not monthly_hp_avg_seer.empty: # Check if not empty after dropna
            monthly_hp_avg_seer['Date_Ordinal'] = monthly_hp_avg_seer['date'].apply(lambda date: date.toordinal())
            print("\n--- Monthly High Performer Trend Data (with Date_Ordinal added) ---")
            print(monthly_hp_avg_seer.head())
        else:
            print("\n--- Monthly High Performer Trend Data is empty after dropping NaNs ---")

    except KeyError:
        print(f"KeyError: Ensure the column 'rating_to_test' exists in df_indexed.")
    except Exception as e:
        print(f"An error occurred during the high performer calculation: {e}")

    try:
        # Now this line should work because 'Date_Ordinal' exists
        model_hp_monthly = smf.ols(f'{high_perf_col_name} ~ Date_Ordinal', data=monthly_hp_avg_seer).fit()

        # Add prediction column AFTER fitting the model
        monthly_hp_avg_seer['Predicted_SEER_HP'] = model_hp_monthly.predict(monthly_hp_avg_seer[['Date_Ordinal']]) # Pass as DataFrame slice for safety

        print("\n--- Regression Summary: Monthly Top Performers ---")
        print(model_hp_monthly.summary())

    except Exception as e:
        print(f"Could not fit regression line for monthly high performers: {e}")
        print("Columns in monthly_hp_avg_seer during regression attempt:", monthly_hp_avg_seer.columns)
        print("Data sample:\n", monthly_hp_avg_seer.head())


    quantile_threshold_low = 0.1
    low_perf_col_name = f'Avg_SEER_Bottom_{int(quantile_threshold_low*100)}p' # Dynamic low performer column name

    # Group by month, then calculate threshold and average of top performers within each month
    # This requires a custom function with groupby().apply()
    def calculate_monthly_low_performers(monthly_rating_values, low_quantile):
        """
        Calculates the average rating of the low performers (e.g., bottom 10%)
        within a monthly group.
        Args:
            monthly_rating_values (pd.Series): Series of rating values for a specific month.
            low_quantile (float): The quantile threshold for low performers (e.g., 0.10).
        Returns:
            float: The average rating of the low performers, or np.nan.
        """
        group_month_str = monthly_rating_values.name.strftime('%Y-%m') if hasattr(monthly_rating_values, 'name') and monthly_rating_values.name else "Unknown Month"
        # print(f"\n--- Processing Low Perf Group for Month: {group_month_str} ---") # Optional debug

        if monthly_rating_values.empty:
            # print(f"Low Perf Group {group_month_str} is empty. Returning NaN.")
            return np.nan

        # Ensure numeric, drop NaNs
        rating_numeric = pd.to_numeric(monthly_rating_values, errors='coerce')
        rating_numeric.dropna(inplace=True)

        if rating_numeric.empty:
            # print(f"No valid numeric data for Low Perf in {group_month_str}. Returning NaN.")
            return np.nan

        try:
            # Calculate the LOW threshold (e.g., 10th percentile)
            threshold_low = rating_numeric.quantile(low_quantile)
        except Exception as e:
            print(f"ERROR calculating low quantile for group {group_month_str}: {e}")
            return np.nan

        # Filter to get LOW performers (<= threshold)
        low_performers = rating_numeric[rating_numeric <= threshold_low]

        if low_performers.empty:
            # print(f"No low performers found <= threshold {threshold_low} in group {group_month_str}.")
            return np.nan

        # Calculate the mean of the low performers
        try:
            final_mean = low_performers.mean()
            return final_mean
        except Exception as e:
            print(f"ERROR calculating mean for low performers in {group_month_str}: {e}")
            return np.nan

    try:
        print("\nApplying low performer calculation...")
        # Apply the low performer function to the correct rating Series after resampling
        monthly_lp_avg_rating_series = df_indexed['rating_to_test'].resample('ME').apply(
            lambda srs: calculate_monthly_low_performers(srs, quantile_threshold_low)
        )

        # Convert the resulting Series to a DataFrame
        monthly_lp_avg_seer = monthly_lp_avg_rating_series.reset_index()

        # Rename the results column appropriately
        monthly_lp_avg_seer.rename(columns={monthly_lp_avg_seer.columns[1]: low_perf_col_name}, inplace=True)

        # Optional: Drop months where calculation resulted in NaN
        monthly_lp_avg_seer.dropna(subset=[low_perf_col_name], inplace=True)

        print("\n--- Monthly Low Performer Trend Data ---")
        if not monthly_lp_avg_seer.empty: # Check if not empty after dropna
            monthly_lp_avg_seer['Date_Ordinal'] = monthly_lp_avg_seer['date'].apply(lambda date: date.toordinal()) # Use 'Date', not 'date' if reset_index created 'Date'
            print(monthly_lp_avg_seer.head())
        else:
            print("Monthly Low Performer Trend Data is empty after dropping NaNs.")

    except KeyError:
        print(f"KeyError: Ensure the column SEER exists in df_indexed.")
    except Exception as e:
        print(f"An error occurred during the low performer calculation: {e}")


    try:
        model_lp_monthly = smf.ols(f'{low_perf_col_name} ~ Date_Ordinal', data=monthly_lp_avg_seer).fit()
        monthly_lp_avg_seer['Predicted_SEER_LP'] = model_lp_monthly.predict(monthly_lp_avg_seer[['Date_Ordinal']]) # Pass as DataFrame slice for safety

        print("\n--- Regression Summary: Monthly Low Performers ---")
        print(model_lp_monthly.summary())

    except Exception as e:
        print(f"Could not fit regression line for monthly low performers: {e}")
        # For debugging if it still fails:
        print("Columns in monthly_lp_avg_seer during regression attempt:", monthly_lp_avg_seer.columns)
        print("Data sample:\n", monthly_lp_avg_seer.head())


    print("Calculating yearly SEER quantiles...")
    df_indexed['rating_to_test_q25'] = df_indexed.groupby('date')['rating_to_test'].transform(lambda x: x.quantile(0.1))
    df_indexed['rating_to_test_q75'] = df_indexed.groupby('date')['rating_to_test'].transform(lambda x: x.quantile(0.9))
    print("Added yearly quantile threshold columns ('rating_to_test_q25', 'rating_to_test_q75').")

    conditions = [
        (df_indexed['rating_to_test'] > df_indexed['rating_to_test_q75']),                # Condition for High performers
        (df_indexed['rating_to_test'] < df_indexed['rating_to_test_q25']),                # Condition for Low performers
        (df_indexed['rating_to_test'] >= df_indexed['rating_to_test_q25']) & (df_indexed['rating_to_test'] <= df_indexed['rating_to_test_q75']) # Condition for Average
    ]
    group_labels = ['High', 'Low', 'Average'] # Must match the order of conditions
    df_indexed['performance_group'] = np.select(conditions, group_labels, default='Unknown')
    yearly_group_avg_seer = df_indexed.groupby(['date', 'performance_group'])['rating_to_test'].mean().unstack()    
    df_indexed = df_indexed.drop(columns=['rating_to_test_q25', 'rating_to_test_q75'])

    analysis_results = {
    'df': df_indexed,
    'yearly_group_avg_seer': yearly_group_avg_seer,
    'monthly_avg_seer': monthly_avg_seer,
    'monthly_hp_avg_seer': monthly_hp_avg_seer,
    'model_hp_monthly': model_hp_monthly,
    'model_lp_monthly': model_lp_monthly,
    'monthly_hp_avg_seer_series': monthly_hp_avg_seer_series,
    'monthly_lp_avg_seer': monthly_lp_avg_seer,
    'r_squared_monthly': r_squared_monthly,
    'quantile_threshold': quantile_threshold,
    'quantile_threshold_low': quantile_threshold_low,
    'low_perf_col_name': low_perf_col_name,
    'high_perf_col_name': high_perf_col_name
    }

    return analysis_results

# --- Visualize Monthly Trends ---
def visualize_overall_efficiency_trends_ac(results):
    plt.figure(figsize=(15, 8)) # Wider figure for time series

    # Plot Monthly Average Trend (actual points)
    sns.scatterplot(data=results['monthly_avg_seer'], x='date', y='rating_to_test', label='Monthly Average SEER', s=50, alpha=0.7)
    # Plot Monthly Average Trend Regression Line
    sns.lineplot(data=results['monthly_avg_seer'], x='date', y='Predicted_SEER', color='blue', linestyle='--', label=f'Market Average Trend (R²={results["r_squared_monthly"]:.2f})')

    # Plot Monthly High Performer Trend (actual points)
    sns.scatterplot(data=results['monthly_hp_avg_seer'], x='date', y=results['high_perf_col_name'], label=f'Monthly Top {int(results["quantile_threshold"]*100)}th Percentile Avg SEER', s=50, marker='^', color='green', alpha=0.7)

    # Plot Monthly High Performer Regression Line (if calculated)
    sns.lineplot(data=results['monthly_hp_avg_seer'], x='date', y='Predicted_SEER_HP', color='orange', linestyle='--', label=f'Top Performers Trend (R²={results["model_hp_monthly"].rsquared:.2f})')
    
    sns.scatterplot(data=results['monthly_lp_avg_seer'], x='date', y=results['low_perf_col_name'], label=f'Monthly Bottom {int(results["quantile_threshold_low"]*100)}% Avg SEER', s=50, marker='v', color='red', alpha=0.7)
    
    sns.lineplot(data=results['monthly_lp_avg_seer'], x='date', y='Predicted_SEER_LP', color='purple', linestyle='--', label=f'Low Performers Trend (R²={results["model_lp_monthly"].rsquared:.2f})')

    plt.title(f'Monthly HVAC SEER Rating Trend: Market Average vs. Top {int(results["quantile_threshold"]*100)}th Percentile vs Bottom {int(results["quantile_threshold_low"]*100)}%')
    plt.xlabel('date')
    plt.ylabel('SEER Rating')

    # Improve date formatting on X-axis
    plt.gca().xaxis.set_major_locator(mdates.YearLocator()) # Tick marks per year
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m')) # Format as Year-Month
    plt.gca().xaxis.set_minor_locator(mdates.MonthLocator(interval=3)) # Minor ticks every 3 months
    plt.gcf().autofmt_xdate() # Auto-rotate date labels

    plt.legend()
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.tight_layout()
    plt.savefig('seer_trend_monthly_regression.png', dpi=300)
    plt.show()


    # Use seaborn's boxplot
    df = results['df']
    try:
        # *** Extract year into a new column FROM THE INDEX ***
        df['entry_year'] = df.index.year
        print("Created 'entry_year' column from DatetimeIndex.")
    except AttributeError:
        print("ERROR: Could not access '.year' attribute. Is the index truly a DatetimeIndex?")
        return
    except Exception as e:
        print(f"ERROR: Failed to extract year from index: {e}")
        return

    unique_years = sorted(df['entry_year'].unique())
    print(unique_years)
    num_years = len(unique_years)
    if num_years == 0:
        print("No unique years found in data.")
        return

    # Determine grid size (e.g., aim for roughly 3-4 columns)
    ncols = 3 if num_years > 2 else num_years # Adjust number of columns as desired
    nrows = math.ceil(num_years / ncols)

    # Define the order for the performance groups on the x-axis
    group_order = ['Low', 'Average', 'High'] # Adjust if your labels are different

    # Create figure and axes grid
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(ncols * 5, nrows * 4), sharey=True) # Share Y axis for easier comparison
    # Flatten axes array for easy iteration, handling single row/col cases
    axes_flat = axes.flatten() if isinstance(axes, np.ndarray) else [axes]

    print(f"Creating {nrows}x{ncols} grid for {num_years} years...")

    # --- Loop through years and create subplot for each ---
    for i, year in enumerate(unique_years):
        ax = axes_flat[i] # Get the current subplot axis
        year_df = df[df['entry_year'] == year] # Filter data for the current year

        if year_df.empty:
            ax.set_title(f'Year {year}\n(No Data)')
            ax.set_xticks([])
            ax.set_yticks([])
            continue

        sns.boxplot(
            data=year_df,
            x='performance_group',
            y='rating_to_test',
            order=group_order, # Ensure consistent order
            ax=ax # Tell seaborn which subplot axis to draw on
        )
        ax.set_title(f'Year {year}')
        ax.set_xlabel('') # Remove individual x-labels if shared below
        ax.set_ylabel('') # Remove individual y-labels if shared on left

    # --- Final Figure Formatting ---
    # Hide any unused subplots if the grid isn't perfectly filled
    for i in range(num_years, len(axes_flat)):
        axes_flat[i].set_visible(False)

    # Add shared axis labels (optional)
    fig.supxlabel('Performance Group', y=0.02) # Adjust position if needed
    fig.supylabel('SEER Rating', x=0.02) # Adjust position if needed

    fig.suptitle('SEER Distribution by Performance Group Per Year', fontsize=16, y=1.0) # Add overall title
    plt.tight_layout(rect=[0.03, 0.03, 1, 0.97]) # Adjust layout (rect leaves space for suptitle/labels)

    # --- Show or Save Plot ---
    try:
        plt.show()
        # output_filename = 'seer_yearly_boxplots.png'
        # plt.savefig(output_filename)
        # print(f"Saved yearly box plots to {output_filename}")
    except Exception as e:
        print(f"Error displaying or saving plot: {e}")

    print("--- Finished Yearly Box Plots ---")