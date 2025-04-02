from datetime import datetime, date # Import date
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, DateTime, TIMESTAMP, JSON, Date
from sqlalchemy.sql import func
import json # Import the json library for handling potential string input

db = SQLAlchemy()

class HVACDevice(db.Model):
    __tablename__ = 'hvac_devices'

    id = db.Column(db.Integer, primary_key=True)
    manufacturer = db.Column(db.String(255), nullable=False)
    market_entry = db.Column(db.Date, nullable=False)
    device_type = db.Column(db.String(255), nullable=False)
    power_rating_kw = db.Column(db.Float)
    airflow_volume_m3h = db.Column(db.Float)
    eer = db.Column(db.Float)
    seer = db.Column(db.Float)
    sepr = db.Column(db.Float)
    heat_recovery_rate = db.Column(db.Float)
    fan_performance = db.Column(db.Float)
    temperature_range = db.Column(db.String(255))
    noise_level_dba = db.Column(db.Float)
    price_currency = db.Column(db.String(3))
    price_amount = db.Column(db.Float)
    units_sold_year = db.Column(db.Integer)
    units_sold_count = db.Column(db.Integer)
    data_source = db.Column(db.String(255))
    created_at = db.Column(db.TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = db.Column(db.TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Add the new column for custom fields
    # Use JSONB if using PostgreSQL: custom_fields = db.Column(JSONB)
    custom_fields = db.Column(JSON) # Use JSON for broader compatibility

    def __repr__(self):
        return f'<HVACDevice {self.manufacturer} - {self.device_type}>'

    def to_dict(self):
        data = {
            'id': self.id,
            'manufacturer': self.manufacturer,
            'market_entry': self.market_entry.isoformat() if isinstance(self.market_entry, date) else None,
            'device_type': self.device_type,
            'power_rating_kw': self.power_rating_kw,
            'airflow_volume_m3h': self.airflow_volume_m3h,
            'eer': self.eer,
            'seer': self.seer,
            'sepr': self.sepr,
            'heat_recovery_rate': self.heat_recovery_rate,
            'fan_performance': self.fan_performance,
            'temperature_range': self.temperature_range,
            'noise_level_dba': self.noise_level_dba,
            'price_currency': self.price_currency,
            'price_amount': self.price_amount,
            'units_sold_year': self.units_sold_year,
            'units_sold_count': self.units_sold_count,
            'data_source': self.data_source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            # Add custom fields, ensuring it's a dict
            'custom_fields': self.custom_fields if isinstance(self.custom_fields, dict) else {}
        }
        return data