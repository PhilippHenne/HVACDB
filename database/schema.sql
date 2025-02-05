      
CREATE TABLE hvac_devices (
    id SERIAL PRIMARY KEY,
    manufacturer VARCHAR(255) NOT NULL,
    market_entry_year INTEGER NOT NULL,
    device_type VARCHAR(255) NOT NULL,
    power_rating_kw DECIMAL NOT NULL,
    airflow_volume_m3h DECIMAL NOT NULL,
    eer DECIMAL,
    seer DECIMAL,
    sepr DECIMAL,
    heat_recovery_rate DECIMAL,
    fan_performance DECIMAL,
    temperature_range VARCHAR(255),
    noise_level_dba DECIMAL,
    price_currency VARCHAR(3),
    price_amount DECIMAL,
    units_sold_year INTEGER,
    units_sold_count INTEGER,
    data_source VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);