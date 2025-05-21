import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import pearsonr, spearmanr

def visualise_flowrate_to_powerinput_trends(df):
    bin_edges = [
        pd.Timestamp.min,
        pd.Timestamp('2016-01-01'),
        pd.Timestamp('2018-01-01'),
        pd.Timestamp.max
    ]

    period_labels = [
        'Pre-2016',
        '2016-2017',
        '2018+'
    ]

    df['ecodesign_period'] = pd.cut(
        df['market_entry'],
        bins=bin_edges,
        labels=period_labels,
        right=False
    )
    print("Created 'ecodesign_period' column.")
    print(df['ecodesign_period'].value_counts())

    plot_df = df.dropna(subset=['ecodesign_period', 'maximumflowrate', 'fandrivepowerinput'])

    if plot_df.empty:
        print("No data available for plotting after filtering for periods and metrics.")
    else:
        print("\nGenerating Faceted Scatter Plot...")
        g = sns.relplot(
            data=plot_df,
            x="maximumflowrate",
            y="fandrivepowerinput",
            col="ecodesign_period", 
            col_order=period_labels,
            kind="scatter",
            height=4, aspect=1.2,
        )
        g.fig.suptitle("Fan Drive Power Input vs. Max Flow Rate by Ecodesign Period", y=1.03)
        g.set_axis_labels("Maximum Flow Rate (m³/h)", "Fan Drive Power Input (W)")
        g.set(xscale="log")
        plt.tight_layout()
        plt.show()


def calculate_correlation(df):
    flow_rate_col = 'referenceflowrate'
    spi_col = 'specificpowerinput' 
    eta_t_col = 'thermalefficiencyheatrecovery'
    sec_col = 'specificenergyconsumptionaverage'
    dba_col = 'noise_level_dba'

    metrics_to_correlate = {
        'SPI (Wh/m³)': spi_col,
        'Heat Recovery Efficiency ': eta_t_col,
        'SEC (kWh/m².a)': sec_col,
        'Noise Level (dB)': dba_col
    }

    print("\n--- Correlation Analysis ---")
    for metric_label, metric_col in metrics_to_correlate.items():
        print(metric_label)
        print(metric_col)
        print(df[metric_col].notna().all())
        if metric_col in df.columns and df[flow_rate_col].notna().all() and df[metric_col].notna().all():
            clean_df_for_corr = df[[flow_rate_col, metric_col]].dropna()
            if len(clean_df_for_corr) >= 2:
                pearson_corr, p_pearson = pearsonr(clean_df_for_corr[flow_rate_col], clean_df_for_corr[metric_col])
                spearman_corr, p_spearman = spearmanr(clean_df_for_corr[flow_rate_col], clean_df_for_corr[metric_col])
                print(f"\nCorrelation between Flow Rate and {metric_label}:")
                print(f"  Pearson's r: {pearson_corr:.3f} (p-value: {p_pearson:.3g})")
                print(f"  Spearman's rho: {spearman_corr:.3f} (p-value: {p_spearman:.3g})")
            else:
                print(f"\nNot enough data points to calculate correlation for Flow Rate and {metric_label} after dropping NaNs.")
        else:
            print(f"\nSkipping correlation for {metric_label} due to missing column or all NaN values.")


    print("\n--- Generating Scatter Plots ---")
    num_metrics = len(metrics_to_correlate)
    if num_metrics > 0:
        n_cols = 2 
        n_rows = (num_metrics + n_cols -1) // n_cols
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(10 * n_cols, 7 * n_rows))
        axes = axes.flatten() 

        plot_idx = 0
        for metric_label, metric_col in metrics_to_correlate.items():
            if metric_col in df.columns:
                ax = axes[plot_idx]
                sns.regplot(x=flow_rate_col, y=metric_col, data=df, ax=ax,
                            scatter_kws={'alpha':0.5}, line_kws={'color':'red'})
                ax.set_title(f'Flow Rate vs. {metric_label}')
                ax.set_xlabel(f'Reference Flow Rate')
                ax.set_ylabel(metric_label)
                ax.grid(True, linestyle=':')
                plot_idx += 1
            else:
                print(f"Column {metric_col} not found for plotting.")
        
        for i in range(plot_idx, len(axes)):
            fig.delaxes(axes[i])

        plt.tight_layout()
        plt.show() 
    else:
        print("No metrics to plot.")