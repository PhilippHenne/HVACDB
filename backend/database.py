      
from flask_sqlalchemy import SQLAlchemy
from .app import app  # Import app instance from app.py

db = SQLAlchemy(app)

class HvacDevice(db.Model):
    __tablename__ = 'hvac_devices'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    manufacturer = db.Column(db.String(255), nullable=False)
    market_entry_year = db.Column(db.Integer, nullable=False)
    device_type = db.Column(db.String(255), nullable=False)
    power_rating_kw = db.Column(db.Numeric, nullable=False)
    airflow_volume_m3h = db.Column(db.Numeric, nullable=False)
    eer = db.Column(db.Numeric)
    seer = db.Column(db.Numeric)
    sepr = db.Column(db.Numeric)
    heat_recovery_rate = db.Column(db.Numeric)
    fan_performance = db.Column(db.Numeric)
    temperature_range = db.Column(db.String(255))
    noise_level_dba = db.Column(db.Numeric)
    price_currency = db.Column(db.String(3))
    price_amount = db.Column(db.Numeric)
    units_sold_year = db.Column(db.Integer)
    units_sold_count = db.Column(db.Integer)
    data_source = db.Column(db.String(255))
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
    updated_at = db.Column(db.TIMESTAMP, server_default=db.func.now(), onupdate=db.func.now())

    def __repr__(self):
        return f"<HvacDevice {self.id} - {self.manufacturer} {self.device_type}>"

