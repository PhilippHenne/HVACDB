import os
import pandas as pd
from sqlalchemy import create_engine, text
from overall_efficiency_trends import analyse_overall_efficiency_trends_ac, visualise_overall_efficiency_trends_ac
from market_snapshot_analysis import analyse_distribution, _perform_series_analysis
from rvu_trends import visualise_flowrate_to_powerinput_trends, calculate_correlation
# --- Configuration ---
DATABASE_URI = os.getenv('DATABASE_URL')


if not DATABASE_URI:
    raise ValueError("DATABASE_URI environment variable not set. Please set it before running.")

# --- Database Connection ---

try:
    print("Connecting to database...")
    engine = create_engine(DATABASE_URI)
    with engine.connect() as connection:
        print("Database connection successful.")
except Exception as e:
    print(f"ERROR: Failed to connect to database.")
    print(f"URI Used: {DATABASE_URI}")
    print(f"Error details: {e}")
    exit()

# SQL Querys

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
    AND ac.seer BETWEEN 2.5 AND 10.0
    AND base.market_entry IS NOT NULL
    -- AND base.market_exit IS NOT NULL
    AND (
        (base.market_exit IS NOT NULL AND ROUND(((base.market_exit - base.market_entry) / 365.25)::numeric, 1) > 1.0)
        OR 
        (base.market_exit IS NULL)
    )
    AND ac.design_load_cooling_kw < 12
"""

AC_MARKET_SNAPSHOT_QUERY = """SELECT
    ac.id,
    hd.manufacturer,
    hd.model_identifier,
    hd.market_entry,
    hd.market_exit, -- Will be NULL or future date for this query
    hd.data_source,

    -- Core Performance Metrics
    ac.seer,
    ac.scop_average,
    ac.scop_warm,
    ac.scop_cold,
    ac.eer,
    ac.cop_standard,

    -- Energy Classes
    ac.energy_class_cooling,
    ac.energy_class_heating_average,
    ac.energy_class_heating_warm,
    ac.energy_class_heating_cold,

    -- Refrigerant
    ac.refrigerant_type,
    ac.refrigerant_gwp,

    -- Design Loads
    ac.design_load_cooling_kw,
    ac.design_load_heating_average_kw,
    ac.design_load_heating_warm_kw,
    ac.design_load_heating_cold_kw,
    
    -- Annual Consumptions
    ac.annual_consumption_cooling_kwh,
    ac.annual_consumption_heating_average_kwh,
    ac.annual_consumption_heating_warm_kwh,
    ac.annual_consumption_heating_cold_kwh,

    -- Part Load & Seasonal ηs (eta_s)
    ac.eta_s_cooling_percent,
    ac.eta_s_heating_average_percent,
    ac.eta_s_heating_warm_percent,
    ac.eta_s_heating_cold_percent,
    ac.eer_cooling_cond_b, ac.pc_cooling_cond_b_kw,
    ac.eer_cooling_cond_c, ac.pc_cooling_cond_c_kw,
    ac.eer_cooling_cond_d, ac.pc_cooling_cond_d_kw,
    ac.cop_heating_cond_a, ac.ph_heating_cond_a_kw,
    ac.cop_heating_cond_b, ac.ph_heating_cond_b_kw,
    ac.cop_heating_cond_c, ac.ph_heating_cond_c_kw,
    ac.cop_heating_cond_d, ac.ph_heating_cond_d_kw,
    ac.cop_heating_tol, ac.ph_heating_tol_kw, ac.tol_temp_heating,
    ac.cop_heating_tbiv, ac.ph_heating_tbiv_kw, ac.tbiv_temp_heating,

    -- Standby/Off-mode power
    ac.power_standby_cooling_kw,
    ac.power_off_cooling_kw,
    ac.power_standby_heating_kw,
    ac.power_off_heating_kw,

    -- Sound
    ac.noise_level_outdoor_cooling_db,
    ac.noise_level_indoor_cooling_db,
    ac.noise_level_outdoor_heating_db,
    ac.noise_level_indoor_heating_db,

    -- Other technical
    ac.capacity_control_type,
    ac.degradation_coeff_cooling_cd
FROM
    air_conditioners ac
JOIN
    hvacdevices hd ON ac.id = hd.id
WHERE
    (hd.market_exit IS NULL OR hd.market_exit > CURRENT_DATE) -- Not yet exited or exit is in the future
    AND (hd.market_entry IS NOT NULL AND hd.market_entry <= CURRENT_DATE) -- Is on the market
    -- !! CRITICAL DATA CLEANING FILTERS from your CurrentMarketACs_Cleaned CTE !!
    -- Repeat ALL the sensible range filters you established for each metric. Example for SEER:
    AND (ac.seer IS NULL OR (ac.seer > 1 AND ac.seer < 10))
    AND (ac.scop_average IS NULL OR (ac.scop_average > 1 AND ac.scop_average < 10))
    AND (ac.design_load_cooling_kw IS NULL OR (ac.design_load_cooling_kw > 0.1 AND ac.design_load_cooling_kw < 12))
    AND (ac.refrigerant_gwp IS NULL OR (ac.refrigerant_gwp >=0 AND ac.refrigerant_gwp < 4000))
    AND (ac.eta_s_cooling_percent IS NULL OR (ac.eta_s_cooling_percent > 50 AND ac.eta_s_cooling_percent < 500))
    AND (ac.noise_level_outdoor_cooling_db IS NULL OR (ac.noise_level_outdoor_cooling_db > 30 AND ac.noise_level_outdoor_cooling_db < 90))
ORDER BY
    ac.id; -- Or any other preferred order"""

RVU_PERFORMANCE_QUERY = """
SELECT
    base.manufacturer,
	base.market_entry AS date,
    v.maximumflowrate AS maximumflowrate,
    v.specificpowerinput AS rating_to_test,
    v.referenceflowrate AS referenceflowrate,
    v.specificpowerinput AS specificpowerinput,
    v.thermalefficiencyheatrecovery AS thermalefficiencyheatrecovery,
    v.specificenergyconsumptionaverage AS specificenergyconsumptionaverage,
    v.fandrivepowerinput AS fandrivepowerinput,
    base.noise_level_dba AS noise_level_dba
FROM
    hvacdevices AS base
INNER JOIN
    residential_ventilation_units AS v ON base.id = v.id
WHERE
    base.device_type = 'residential_ventilation_unit'
    AND (EXTRACT (YEAR FROM base.market_entry)) > 2009
	AND v.heatrecoverysystem IS DISTINCT FROM 'NONE'
    AND v.maximumflowrate IS NOT NULL
    AND v.fandrivepowerinput < 2000
    AND v.referenceflowrate*3600 < 1000
    AND v.specificenergyconsumptionaverage IS NOT NULL
    AND v.thermalefficiencyheatrecovery IS NOT NULL
    AND (v.specificpowerinput IS NOT NULL OR v.fandrivepowerinput IS NOT NULL)
    AND v.specificpowerinput < 2
"""

RVU_MARKET_SNAPSHOT_QUERY = """SELECT
    v.id,
    hd.manufacturer,
    hd.model_identifier,
    hd.market_entry,
    hd.market_exit,
    hd.data_source,
    v.thermalefficiencyheatrecovery AS thermalefficiencyheatrecovery,
    v.specificpowerinput AS specificpowerinput,
    v.specificenergyconsumptionaverage AS specificenergyconsumptionaverage,
    v.energyclass AS energyclass,
    hd.noise_level_dba AS noise_level_dba
FROM
    residential_ventilation_units v
JOIN
    hvacdevices hd ON v.id = hd.id
WHERE
    (hd.market_exit IS NULL OR hd.market_exit > CURRENT_DATE) -- Not yet exited or exit is in the future
    AND (hd.market_entry IS NOT NULL AND hd.market_entry <= CURRENT_DATE) -- Is on the market
    AND (EXTRACT (YEAR FROM hd.market_entry)) > 2009
	AND v.heatrecoverysystem IS DISTINCT FROM 'NONE'
    AND v.maximumflowrate IS NOT NULL
    AND v.fandrivepowerinput < 2000
    AND v.referenceflowrate*3600 < 1000
    AND v.specificenergyconsumptionaverage IS NOT NULL
    AND v.thermalefficiencyheatrecovery IS NOT NULL
    AND (v.specificpowerinput IS NOT NULL OR v.fandrivepowerinput IS NOT NULL)
    AND v.specificpowerinput < 2
"""

HP_MARKET_SNAPSHOW_QUERY =  """-- CTE to pivot the selected performance metrics for ALL heat pumps
WITH PivotedHPPerformance AS (
    SELECT
        hp.id AS heat_pump_id, 
        MAX(CASE
            WHEN hpp.condition_name = 'SEER AC' AND hpp.metric_name = 'SEER'
            THEN hpp.metric_value ELSE NULL
        END) AS seer_ac,
        MAX(CASE
            WHEN hpp.condition_name = 'SEER AC' AND hpp.metric_name = 'ηsc' 
            THEN hpp.metric_value ELSE NULL
        END) AS eta_sc_seer_ac,
        MAX(CASE
            WHEN hpp.condition_name = 'A35/W12-7' AND hpp.metric_name = 'Pc'
            THEN hpp.metric_value ELSE NULL
        END) AS pc_a35_w12_7,
        MAX(CASE
            WHEN hpp.condition_name = 'A35/W12-7' AND hpp.metric_name = 'EER'
            THEN hpp.metric_value ELSE NULL
        END) AS eer_a35_w12_7,
        
        -- Added: SCOP and ηsh for Average Climate W35
        MAX(CASE
            WHEN hpp.condition_name = 'SCOP Average W35' AND hpp.metric_name = 'SCOP'
            THEN hpp.metric_value ELSE NULL
        END) AS scop_avg_w35,
        MAX(CASE
            WHEN hpp.condition_name = 'SCOP Average W35' AND hpp.metric_name = 'ηsh'
            THEN hpp.metric_value ELSE NULL
        END) AS eta_sh_avg_w35, -- ηsh is seasonal space heating efficiency (%)

        -- Added: SCOP and ηsh for Average Climate W55
        MAX(CASE
            WHEN hpp.condition_name = 'SCOP Average W55' AND hpp.metric_name = 'SCOP'
            THEN hpp.metric_value ELSE NULL
        END) AS scop_avg_w55,
        MAX(CASE
            WHEN hpp.condition_name = 'SCOP Average W55' AND hpp.metric_name = 'ηsh'
            THEN hpp.metric_value ELSE NULL
        END) AS eta_sh_avg_w55
        
    FROM
        heat_pumps hp 
    LEFT JOIN
        heat_pump_performance hpp ON hp.id = hpp.heat_pump_id
    GROUP BY
        hp.id
),
-- CTE to apply data cleaning filters to the pivoted metrics
CleanedHPDataForAnalysis AS (
    SELECT
        pivoted.heat_pump_id,
        hd.manufacturer,       -- From hvacdevices table
        hd.model_identifier,   -- From hvacdevices table
        hp_base.refrigerant,   -- Example from heat_pumps specific table
        pivoted.seer_ac,
        pivoted.eta_sc_seer_ac,
        pivoted.pc_a35_w12_7,
        pivoted.eer_a35_w12_7,
        pivoted.scop_avg_w35,   -- Added
        pivoted.eta_sh_avg_w35, -- Added
        pivoted.scop_avg_w55,   -- Added
        pivoted.eta_sh_avg_w55  -- Added
    FROM
        PivotedHPPerformance pivoted
    JOIN 
        heat_pumps hp_base ON pivoted.heat_pump_id = hp_base.id 
    JOIN 
        hvacdevices hd ON pivoted.heat_pump_id = hd.id        
    WHERE
        hd.device_type = 'heat_pump' 
        
        -- !! CRITICAL DATA CLEANING FILTERS !!
        -- Adjust these example ranges based on your data exploration for heat pumps.
        AND (pivoted.pc_a35_w12_7 IS NULL OR (pivoted.pc_a35_w12_7 > 0.1 AND pivoted.pc_a35_w12_7 < 200))
        AND (pivoted.eer_a35_w12_7 IS NULL OR (pivoted.eer_a35_w12_7 > 1 AND pivoted.eer_a35_w12_7 < 10))
        AND (pivoted.seer_ac IS NULL OR (pivoted.seer_ac > 1 AND pivoted.seer_ac < 15))
        AND (pivoted.eta_sc_seer_ac IS NULL OR (pivoted.eta_sc_seer_ac > 50 AND pivoted.eta_sc_seer_ac < 600))
        -- Added filters for new SCOP and ηsh values (adjust ranges as needed)
        AND (pivoted.scop_avg_w35 IS NULL OR (pivoted.scop_avg_w35 > 1 AND pivoted.scop_avg_w35 < 7)) 
        AND (pivoted.eta_sh_avg_w35 IS NULL OR (pivoted.eta_sh_avg_w35 > 50 AND pivoted.eta_sh_avg_w35 < 300)) -- ηsh is a percentage
        AND (pivoted.scop_avg_w55 IS NULL OR (pivoted.scop_avg_w55 > 1 AND pivoted.scop_avg_w55 < 6)) 
        AND (pivoted.eta_sh_avg_w55 IS NULL OR (pivoted.eta_sh_avg_w55 > 50 AND pivoted.eta_sh_avg_w55 < 250)) -- ηsh at W55 might be lower
)
-- Final SELECT to get the raw, cleaned data for each heat pump
SELECT
    heat_pump_id,
    manufacturer,
    model_identifier,
    refrigerant,
    seer_ac,
    eta_sc_seer_ac,
    pc_a35_w12_7,
    eer_a35_w12_7,
    scop_avg_w35,   -- Added
    eta_sh_avg_w35, -- Added
    scop_avg_w55,   -- Added
    eta_sh_avg_w55  -- Added
FROM
    CleanedHPDataForAnalysis
ORDER BY
    heat_pump_id;"""

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
    data_df = fetch_data(engine, AC_PERFORMANCE_QUERY)

    if data_df is not None and not data_df.empty:
        print("\n--- Data Overview ---")
        print(f"Shape: {data_df.shape}")
        print("First 5 rows:\n", data_df.head())
        print("\nData Types:\n", data_df.dtypes)

        # 2. Analyse data 
        #analyse_distribution(data_df, 'seer', metric_label='SEER')
        metrics_to_analyze = ['seer_ac', 'eta_sc_seer_ac', 'pc_a35_w12_7', 'eer_a35_w12_7']
        for col in metrics_to_analyze:
            if col in data_df.columns:
                data_df[col] = pd.to_numeric(data_df[col], errors='coerce')
        #if 'scop_avg_w35' in data_df.columns:
        #    analyse_distribution(data_df, 'scop_avg_w35', metric_label='Heat Pump SCOP (Average W35)')
        #if 'eta_sh_avg_w35' in data_df.columns:
        #    analyse_distribution(data_df, 'eta_sh_avg_w35', metric_label='Heat Pump ηsh (Average W35 %)')
        #if 'scop_avg_w55' in data_df.columns:
        #    analyse_distribution(data_df, 'scop_avg_w55', metric_label='Heat Pump SCOP (Average W55)')
        #if 'eta_sh_avg_w55' in data_df.columns:
        #    analyse_distribution(data_df, 'eta_sh_avg_w55', metric_label='Heat Pump ηsh (Average W55 %)')        
        #if 'seer_ac' in data_df.columns:
        #    analyse_distribution(data_df, 'seer_ac', metric_label='Heat Pump SEER (SEER AC)')

        #if 'eta_sc_seer_ac' in data_df.columns:
        #    analyse_distribution(data_df, 'eta_sc_seer_ac', metric_label='Heat Pump ηsc (SEER AC %)')

        #if 'pc_a35_w12_7' in data_df.columns:
        #    analyse_distribution(data_df, 'pc_a35_w12_7', metric_label='Heat Pump Pc (A35/W12-7 kW)')

        #if 'eer_a35_w12_7' in data_df.columns:
        #    analyse_distribution(data_df, 'eer_a35_w12_7', metric_label='Heat Pump EER (A35/W12-7)')
        #metrics_to_analyze = ['thermalefficiencyheatrecovery', 'specificpowerinput', 'specificenergyconsumptionaverage']
        #for col in metrics_to_analyze:
        #    if col in data_df.columns:
        #        data_df[col] = pd.to_numeric(data_df[col], errors='coerce')
        #if 'thermalefficiencyheatrecovery' in data_df.columns:
        #    analyse_distribution(data_df, 'thermalefficiencyheatrecovery', metric_label='Thermal Efficiency of Heat Recovery %')
        #if 'specificpowerinput' in data_df.columns:
        #    analyse_distribution(data_df, 'specificpowerinput', metric_label='Specific Power Input')
        #if 'noise_level_dba' in data_df.columns:
        #    analyse_distribution(data_df, 'noise_level_dba', metric_label='Noise level')

        #if 'specificenergyconsumptionaverage' in data_df.columns:
        #    analyse_distribution(data_df, 'specificenergyconsumptionaverage', metric_label='Specific Energy Consumption Average Climate', group_by_column='energyclass')

        analysis_results = analyse_overall_efficiency_trends_ac(data_df)
        visualise_overall_efficiency_trends_ac(analysis_results)
        #calculate_correlation(data_df)
    else:
        print("\nNo data loaded, skipping analysis and visualization.")

    print("\n--- Script Execution Complete ---")