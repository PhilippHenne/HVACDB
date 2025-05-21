import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import statsmodels.formula.api as smf 
import matplotlib.dates as mdates
import math
from scipy.stats import pearsonr, spearmanr

def analyse_overall_efficiency_trends_ac(df):
    if 'date' not in df.columns:
        print("Error: 'date' (expected as market_entry) column not found in DataFrame.")
        return None 
    df = df.rename(columns={'date': 'market_entry'})

    if 'rating_to_test' not in df.columns:
        print("Error: 'rating_to_test' (expected as SEER) column not found in DataFrame.")
        return None

    try:
        df['market_entry'] = pd.to_datetime(df['market_entry'], errors='coerce')
        df['rating_to_test'] = pd.to_numeric(df['rating_to_test'], errors='coerce')

        if 'market_exit' in df.columns:
            print("Applying filter for devices with market life >= 1 year...")
            df['market_exit'] = pd.to_datetime(df['market_exit'], errors='coerce')

            valid_dates_mask = df['market_entry'].notna() & df['market_exit'].notna()
            df['market_life_days'] = np.nan 
            df.loc[valid_dates_mask, 'market_life_days'] = \
                (df.loc[valid_dates_mask, 'market_exit'] - df.loc[valid_dates_mask, 'market_entry']).dt.days

            mask_exited_short_life = df['market_exit'].notna() & (df['market_life_days'] < 365)

            count_before_filter = len(df)
            df = df[~mask_exited_short_life].copy()
            count_after_filter = len(df)
            print(f"Filtered out {count_before_filter - count_after_filter} devices with market life < 1 year.")
            if count_after_filter == 0:
                print("Warning: DataFrame is empty after filtering for market lifespan. No data to analyze.")
                return None
        else:
            print("Warning: 'market_exit' column not found. Cannot filter by market lifespan. Proceeding with unfiltered data.")

        df.dropna(subset=['market_entry', 'rating_to_test'], inplace=True)
        if df.empty:
            print("DataFrame is empty after dropping NaNs in 'market_entry' or 'rating_to_test'. No data to analyze.")
            return None

        df.sort_values('market_entry', inplace=True)

        df_indexed = df.set_index('market_entry') # Use the renamed column

        monthly_avg_seer = df_indexed['rating_to_test'].resample('ME').mean().reset_index()
        monthly_avg_seer.rename(columns={'market_entry': 'date'}, inplace=True) # Rename back for consistency if needed later, or use market_entry
        monthly_avg_seer.dropna(inplace=True)

        if monthly_avg_seer.empty:
            print("No data available for monthly average SEER after resampling and dropping NaNs.")
            model_monthly_summary_text = "No data for monthly average SEER regression."
            monthly_hp_avg_seer = pd.DataFrame(columns=['date', f'Avg_SEER_Top_{int(0.90*100)}p', 'Date_Ordinal', 'Predicted_SEER_HP'])
            model_hp_monthly_summary_text = "No data for monthly high performer SEER regression."
            monthly_lp_avg_seer = pd.DataFrame(columns=['date', f'Avg_SEER_Bottom_{int(0.10*100)}p', 'Date_Ordinal', 'Predicted_SEER_LP'])
            model_lp_monthly_summary_text = "No data for monthly low performer SEER regression."
            r_squared_monthly = np.nan
            quantile_threshold = 0.90
            quantile_threshold_low = 0.10
            high_perf_col_name = f'Avg_SEER_Top_{int(quantile_threshold*100)}p'
            low_perf_col_name = f'Avg_SEER_Bottom_{int(quantile_threshold_low*100)}p'
        else:
            print("\n--- Monthly Average SEER Data (potentially filtered) ---")
            print(monthly_avg_seer.head())
            monthly_avg_seer['Date_Ordinal'] = monthly_avg_seer['date'].apply(lambda date_obj: date_obj.toordinal())
            model_monthly = smf.ols('rating_to_test ~ Date_Ordinal', data=monthly_avg_seer).fit()
            model_monthly_summary_text = model_monthly.summary().as_text()
            print("\n--- Regression Analysis: Monthly Average SEER Rating vs. Time ---")
            print(model_monthly_summary_text)
            slope_monthly = model_monthly.params['Date_Ordinal']
            p_value_monthly = model_monthly.pvalues['Date_Ordinal']
            r_squared_monthly = model_monthly.rsquared
            print(f"\nSlope (Change in Avg SEER per Day): {slope_monthly:.5f}")
            print(f"Approx. Change per Month: {slope_monthly * 30.4:.4f}")
            print(f"P-value for Time coefficient: {p_value_monthly:.4f}")
            print(f"R-squared: {r_squared_monthly:.3f}")
            monthly_avg_seer['Predicted_SEER'] = model_monthly.predict(monthly_avg_seer['Date_Ordinal'])


        # Calculate High Performers (90th percentile) per Month
        quantile_threshold = 0.90
        high_perf_col_name = f'Avg_SEER_Top_{int(quantile_threshold*100)}p'
        
        if not df_indexed.empty:
            def calculate_monthly_high_performers(monthly_seer_values):
                # group_month_str = monthly_seer_values.name.strftime('%Y-%m') if hasattr(monthly_seer_values, 'name') and monthly_seer_values.name else "Unknown Month"
                if monthly_seer_values.empty: return np.nan
                seer_numeric = pd.to_numeric(monthly_seer_values, errors='coerce')
                seer_numeric.dropna(inplace=True)
                if seer_numeric.empty: return np.nan
                try:
                    threshold = seer_numeric.quantile(quantile_threshold)
                except Exception: return np.nan
                top_performers = seer_numeric[seer_numeric >= threshold]
                if top_performers.empty: return np.nan
                try:
                    return top_performers.mean()
                except Exception: return np.nan

            print("\nApplying high performer calculation...")
            monthly_hp_avg_seer_series = df_indexed['rating_to_test'].resample('ME').apply(calculate_monthly_high_performers)
            monthly_hp_avg_seer = monthly_hp_avg_seer_series.reset_index()
            monthly_hp_avg_seer.rename(columns={'market_entry': 'date', monthly_hp_avg_seer_series.name: high_perf_col_name}, inplace=True)
            monthly_hp_avg_seer.dropna(subset=[high_perf_col_name], inplace=True)

            if not monthly_hp_avg_seer.empty:
                monthly_hp_avg_seer['Date_Ordinal'] = monthly_hp_avg_seer['date'].apply(lambda date_obj: date_obj.toordinal())
                model_hp_monthly = smf.ols(f'Q("{high_perf_col_name}") ~ Date_Ordinal', data=monthly_hp_avg_seer).fit()
                monthly_hp_avg_seer['Predicted_SEER_HP'] = model_hp_monthly.predict(monthly_hp_avg_seer[['Date_Ordinal']])
                model_hp_monthly_summary_text = model_hp_monthly.summary().as_text()
                print("\n--- Regression Summary: Monthly Top Performers ---")
                print(model_hp_monthly_summary_text)
            else:
                print("\n--- Monthly High Performer Trend Data is empty after dropping NaNs ---")
                model_hp_monthly = None 
                monthly_hp_avg_seer = pd.DataFrame(columns=['date', high_perf_col_name, 'Date_Ordinal', 'Predicted_SEER_HP'])


            # Calculate Low Performers (10th percentile) per Month
            quantile_threshold_low = 0.10
            low_perf_col_name = f'Avg_SEER_Bottom_{int(quantile_threshold_low*100)}p'

            def calculate_monthly_low_performers(monthly_rating_values, low_quantile):
                #group_month_str = monthly_rating_values.name.strftime('%Y-%m') if hasattr(monthly_rating_values, 'name') and monthly_rating_values.name else "Unknown Month"
                if monthly_rating_values.empty: return np.nan
                rating_numeric = pd.to_numeric(monthly_rating_values, errors='coerce')
                rating_numeric.dropna(inplace=True)
                if rating_numeric.empty: return np.nan
                try:
                    threshold_low = rating_numeric.quantile(low_quantile)
                except Exception: return np.nan
                low_performers = rating_numeric[rating_numeric <= threshold_low]
                if low_performers.empty: return np.nan
                try:
                    return low_performers.mean()
                except Exception: return np.nan

            print("\nApplying low performer calculation...")
            monthly_lp_avg_rating_series = df_indexed['rating_to_test'].resample('ME').apply(
                lambda srs: calculate_monthly_low_performers(srs, quantile_threshold_low)
            )
            monthly_lp_avg_seer = monthly_lp_avg_rating_series.reset_index()
            monthly_lp_avg_seer.rename(columns={'market_entry': 'date', monthly_lp_avg_rating_series.name: low_perf_col_name}, inplace=True)
            monthly_lp_avg_seer.dropna(subset=[low_perf_col_name], inplace=True)

            if not monthly_lp_avg_seer.empty:
                monthly_lp_avg_seer['Date_Ordinal'] = monthly_lp_avg_seer['date'].apply(lambda date_obj: date_obj.toordinal())
                model_lp_monthly = smf.ols(f'Q("{low_perf_col_name}") ~ Date_Ordinal', data=monthly_lp_avg_seer).fit()
                monthly_lp_avg_seer['Predicted_SEER_LP'] = model_lp_monthly.predict(monthly_lp_avg_seer[['Date_Ordinal']])
                model_lp_monthly_summary_text = model_lp_monthly.summary().as_text()
                print("\n--- Regression Summary: Monthly Low Performers ---")
                print(model_lp_monthly_summary_text)
            else:
                print("\n--- Monthly Low Performer Trend Data is empty after dropping NaNs ---")
                model_lp_monthly = None # Ensure it's defined
                monthly_lp_avg_seer = pd.DataFrame(columns=['date', low_perf_col_name, 'Date_Ordinal', 'Predicted_SEER_LP'])
        
        else: 
            print("Initial DataFrame was empty after filtering and NaNs, skipping percentile calculations.")
            model_monthly = None
            model_hp_monthly = None
            model_lp_monthly = None
            monthly_hp_avg_seer = pd.DataFrame(columns=['date', high_perf_col_name, 'Date_Ordinal', 'Predicted_SEER_HP'])
            monthly_lp_avg_seer = pd.DataFrame(columns=['date', low_perf_col_name, 'Date_Ordinal', 'Predicted_SEER_LP'])
            r_squared_monthly = np.nan


        # Yearly Group Avg
        yearly_group_avg_seer = None
        if not df_indexed.empty and 'rating_to_test' in df_indexed.columns:
            print("Calculating yearly SEER quantiles...")
            temp_year_col = df_indexed.index.year.to_series(index=df_indexed.index)

            df_indexed['rating_to_test_q_low'] = df_indexed.groupby(temp_year_col)['rating_to_test'].transform(lambda x: x.quantile(quantile_threshold_low))
            df_indexed['rating_to_test_q_high'] = df_indexed.groupby(temp_year_col)['rating_to_test'].transform(lambda x: x.quantile(quantile_threshold))
            
            conditions = [
                (df_indexed['rating_to_test'] > df_indexed['rating_to_test_q_high']),
                (df_indexed['rating_to_test'] < df_indexed['rating_to_test_q_low']),
                (df_indexed['rating_to_test'] >= df_indexed['rating_to_test_q_low']) & (df_indexed['rating_to_test'] <= df_indexed['rating_to_test_q_high'])
            ]
            group_labels = ['High', 'Low', 'Average']
            df_indexed['performance_group'] = np.select(conditions, group_labels, default='Unknown')
            
            yearly_group_avg_seer = df_indexed.groupby([df_indexed.index.year, 'performance_group'])['rating_to_test'].mean().unstack()
            yearly_group_avg_seer.index.name = 'entry_year'

            df_indexed = df_indexed.drop(columns=['rating_to_test_q_low', 'rating_to_test_q_high'])
        else:
            print("Skipping yearly group calculations as df_indexed is empty or missing 'rating_to_test'.")
            yearly_group_avg_seer = pd.DataFrame()

    except KeyError as e:
        print(f"Error: Column not found during analysis - {e}. Make sure input DataFrame has required columns.")
        return None
    except Exception as e:
        print(f"Error during data preparation or analysis: {e}")
        import traceback
        traceback.print_exc()
        return None


    analysis_results = {
        'df_filtered_for_plot': df_indexed.reset_index(), 
        'yearly_group_avg_seer': yearly_group_avg_seer,
        'monthly_avg_seer': monthly_avg_seer,
        'model_monthly': model_monthly if 'model_monthly' in locals() else None, 
        'monthly_hp_avg_seer': monthly_hp_avg_seer,
        'model_hp_monthly': model_hp_monthly if 'model_hp_monthly' in locals() else None,
        'monthly_lp_avg_seer': monthly_lp_avg_seer,
        'model_lp_monthly': model_lp_monthly if 'model_lp_monthly' in locals() else None,
        'r_squared_monthly': r_squared_monthly if 'r_squared_monthly' in locals() else np.nan,
        'quantile_threshold': quantile_threshold,
        'quantile_threshold_low': quantile_threshold_low,
        'low_perf_col_name': low_perf_col_name,
        'high_perf_col_name': high_perf_col_name
    }
    if 'monthly_hp_avg_seer_series' in analysis_results:
        del analysis_results['monthly_hp_avg_seer_series']

    return analysis_results


# Visualise Monthly Trends
def visualise_overall_efficiency_trends_ac(results):
    if results is None:
        print("No results to visualize.")
        return

    plt.figure(figsize=(15, 8))

    # Plot Monthly Average Trend
    label_avg = 'Market Average Trend (Regression N/A)' # Default label
    if not results['monthly_avg_seer'].empty and 'Predicted_SEER' in results['monthly_avg_seer'].columns and results.get('model_monthly'):
        model_avg = results['model_monthly']
        slope_avg_per_day = model_avg.params.get('Date_Ordinal', np.nan)
        slope_avg_per_year = slope_avg_per_day * 365.25
        r2_avg = model_avg.rsquared
        label_avg = f'Market Average (Slope: {slope_avg_per_year:.3f} SEER/yr, R²={r2_avg:.2f})'
        
        sns.scatterplot(data=results['monthly_avg_seer'], x='date', y='rating_to_test', label='Monthly Average SEER', s=50, alpha=0.7)
        sns.lineplot(data=results['monthly_avg_seer'], x='date', y='Predicted_SEER', color='blue', linestyle='--', label=label_avg)
    else:
        print("Skipping plot for Monthly Average SEER: Data, prediction, or model missing.")
        if not results['monthly_avg_seer'].empty:
             sns.scatterplot(data=results['monthly_avg_seer'], x='date', y='rating_to_test', label='Monthly Average SEER (No Trend Line)', s=50, alpha=0.7)


    # Plot Monthly High Performer Trend
    label_hp = f'Monthly Top {int(results.get("quantile_threshold", 0.9)*100)}th% Avg SEER (Regression N/A)' # Default
    if not results['monthly_hp_avg_seer'].empty and 'Predicted_SEER_HP' in results['monthly_hp_avg_seer'].columns and results.get('model_hp_monthly'):
        model_hp = results['model_hp_monthly']
        slope_hp_per_day = model_hp.params.get('Date_Ordinal', np.nan)
        slope_hp_per_year = slope_hp_per_day * 365.25
        r2_hp = model_hp.rsquared
        label_hp = f'Top {int(results["quantile_threshold"]*100)}th% (Slope: {slope_hp_per_year:.3f} SEER/yr, R²={r2_hp:.2f})'
        
        sns.scatterplot(data=results['monthly_hp_avg_seer'], x='date', y=results['high_perf_col_name'], label=f'Monthly Top {int(results["quantile_threshold"]*100)}th% Avg SEER', s=50, marker='^', color='green', alpha=0.7)
        sns.lineplot(data=results['monthly_hp_avg_seer'], x='date', y='Predicted_SEER_HP', color='orange', linestyle='--', label=label_hp)
    else:
        print("Skipping plot for Monthly High Performers: Data, prediction, or model missing.")
        if not results['monthly_hp_avg_seer'].empty:
            sns.scatterplot(data=results['monthly_hp_avg_seer'], x='date', y=results['high_perf_col_name'], label=f'Monthly Top {int(results.get("quantile_threshold", 0.9)*100)}th% Avg SEER (No Trend Line)', s=50, marker='^', color='green', alpha=0.7)


    # Plot Monthly Low Performer Trend
    label_lp = f'Monthly Bottom {int(results.get("quantile_threshold_low", 0.1)*100)}th% Avg SEER (Regression N/A)' # Default
    if not results['monthly_lp_avg_seer'].empty and 'Predicted_SEER_LP' in results['monthly_lp_avg_seer'].columns and results.get('model_lp_monthly'):
        model_lp = results['model_lp_monthly']
        slope_lp_per_day = model_lp.params.get('Date_Ordinal', np.nan)
        slope_lp_per_year = slope_lp_per_day * 365.25
        r2_lp = model_lp.rsquared
        label_lp = f'Bottom {int(results["quantile_threshold_low"]*100)}th% (Slope: {slope_lp_per_year:.3f} SEER/yr, R²={r2_lp:.2f})'

        sns.scatterplot(data=results['monthly_lp_avg_seer'], x='date', y=results['low_perf_col_name'], label=f'Monthly Bottom {int(results["quantile_threshold_low"]*100)}th% Avg SEER', s=50, marker='v', color='red', alpha=0.7)
        sns.lineplot(data=results['monthly_lp_avg_seer'], x='date', y='Predicted_SEER_LP', color='purple', linestyle='--', label=label_lp)
    else:
        print("Skipping plot for Monthly Low Performers: Data, prediction, or model missing.")
        if not results['monthly_lp_avg_seer'].empty: 
            sns.scatterplot(data=results['monthly_lp_avg_seer'], x='date', y=results['low_perf_col_name'], label=f'Monthly Bottom {int(results.get("quantile_threshold_low",0.1)*100)}% Avg SEER (No Trend Line)', s=50, marker='v', color='red', alpha=0.7)


    plt.title(f'Monthly HVAC SEER Rating Trend (Filtered: Market Life >= 1yr): Market Avg vs. Top/Bottom Percentiles')
    plt.xlabel('Date (Market Entry)')
    plt.ylabel('SEER Rating')

    plt.gca().xaxis.set_major_locator(mdates.YearLocator())
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.gca().xaxis.set_minor_locator(mdates.MonthLocator(interval=3))
    plt.gcf().autofmt_xdate()

    plt.legend()
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.tight_layout()
    plt.show()
