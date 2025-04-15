from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, DateTime, TIMESTAMP, JSON, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import json

db = SQLAlchemy()


DEVICE_TYPES = {
    'air_conditioner': 'Air Conditioner',
    'heat_pump': 'Heat Pump',
    'residential_ventilation_unit': 'Residential Ventilation Units'
    # Add other known types here
}


class HVACDevice(db.Model):
    __tablename__ = 'hvacdevices' # Base table name

    id = db.Column(db.Integer, primary_key=True)
    # --- Common Fields ---
    manufacturer = db.Column(db.String(255), nullable=False, index=True)
    market_entry = db.Column(db.Date, nullable=False, index=True)
    market_exit = db.Column(db.Date, nullable=True)
    #power_rating_kw = db.Column(db.Float, nullable=True)
    noise_level_dba = db.Column(db.Float, nullable=True)
    price_currency = db.Column(db.String(3), nullable=True)
    price_amount = db.Column(db.Float, nullable=True)
    data_source = db.Column(db.String(255), nullable=True)
    custom_fields = db.Column(JSON, nullable=True) # for less common or truly custom data
    created_at = db.Column(db.TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = db.Column(db.TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    # --- End Common Fields ---

    # --- Inheritance Discriminator ---
    device_type = db.Column(db.String(50), nullable=False, index=True) # Changed from type for clarity

    __mapper_args__ = {
        'polymorphic_identity': 'hvac_device_base', # Base identity (optional but good practice)
        'polymorphic_on': device_type # Column SQLAlchemy uses to determine subclass
    }

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.id}: {self.manufacturer}>'

    # Base to_dict - subclasses can extend this
    def to_dict(self):
        common_data = {
            'id': self.id,
            'device_type': self.device_type, # Include the type
            'manufacturer': self.manufacturer,
            'market_entry': self.market_entry.isoformat() if isinstance(self.market_entry, date) else None,
            'market_exit': self.market_exit.isoformat() if isinstance(self.market_exit, date) else None,            'noise_level_dba': self.noise_level_dba,
            'price_currency': self.price_currency,
            'price_amount': self.price_amount,
            'data_source': self.data_source,
            'custom_fields': self.custom_fields if isinstance(self.custom_fields, dict) else {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        return common_data

# --- Air Conditioner Subclass ---
class AirConditioner(HVACDevice):
    __tablename__ = 'air_conditioners' # Specific table for ACs

    id = db.Column(db.Integer, ForeignKey('hvacdevices.id'), primary_key=True)
    eer = db.Column(db.Float, nullable=True)
    seer = db.Column(db.Float, nullable=True)
    rated_power_cooling_kw = db.Column(db.Float, nullable=True)
    energy_class_cooling = db.Column(db.String(255), nullable=True)
    design_load_cooling_kw = db.Column(db.Float, nullable=True)
    annual_consumption_cooling_kwh = db.Column(db.Float, nullable=True)
    rated_power_heating_kw = db.Column(db.Float, nullable=True)
    cop_standard = db.Column(db.Float, nullable=True)
    scop_average = db.Column(db.Float, nullable=True)
    energy_class_heating_average = db.Column(db.String(255), nullable=True)
    design_load_heating_average_kw = db.Column(db.Float, nullable=True)
    annual_consumption_heating_average_kwh = db.Column(db.Float, nullable=True)
    scop_warm = db.Column(db.Float, nullable=True)
    energy_class_heating_warm = db.Column(db.String(255), nullable=True)
    design_load_heating_warm_kw = db.Column(db.Float, nullable=True)
    scop_cold = db.Column(db.Float, nullable=True)
    energy_class_heating_cold = db.Column(db.String(255), nullable=True)
    design_load_heating_cold_kw = db.Column(db.Float, nullable=True)
    refrigerant_type = db.Column(db.String(255), nullable=True)
    refrigerant_gwp = db.Column(db.Integer, nullable=True)
    noise_level_outdoor_cooling_db = db.Column(db.Float, nullable=True)
    # Add other AC-specific fields here as needed
    # Example: cooling_capacity_btu_hr = db.Column(db.Integer)

    __mapper_args__ = {
        'polymorphic_identity': 'air_conditioner', # Matches value stored in hvac_devices_base.device_type
    }

    # Extend to_dict to include specific fields
    def to_dict(self):
        data = super().to_dict() # Get common fields
        data.update({
            'eer': self.eer,
            'seer': self.seer,
            'rated_power_cooling_kw': self.rated_power_cooling_kw,
            'energy_class_cooling': self.energy_class_cooling,
            'design_load_cooling_kw': self.design_load_cooling_kw,
            'annual_consumption_cooling_kwh': self.annual_consumption_cooling_kwh,
            'rated_power_heating_kw': self.rated_power_heating_kw,
            'cop_standard': self.cop_standard,
            'scop_average': self.scop_average,
            'energy_class_heating_average': self.energy_class_heating_average,
            'design_load_heating_average_kw': self.design_load_heating_average_kw,
            'annual_consumption_heating_average_kwh': self.annual_consumption_heating_average_kwh,
            'scop_warm': self.scop_warm,
            'energy_class_heating_warm': self.energy_class_heating_warm,
            'design_load_heating_warm_kw': self.design_load_heating_warm_kw,
            'scop_cold': self.scop_cold,
            'energy_class_heating_cold': self.energy_class_heating_cold,
            'design_load_heating_cold_kw': self.design_load_heating_cold_kw,
            'refrigerant_type': self.refrigerant_type,
            'refrigerant_gwp': self.refrigerant_gwp,
            'noise_level_outdoor_cooling_db': self.noise_level_outdoor_cooling_db,
            # Add other specific fields here
            # 'cooling_capacity_btu_hr': self.cooling_capacity_btu_hr,
        })
        return data


# --- Placeholder HeatPump Subclass ---
class HeatPump(HVACDevice):
    __tablename__ = 'heat_pumps'
    id = db.Column(db.Integer, ForeignKey('hvacdevices.id'), primary_key=True)
    # Add HeatPump specific fields later
    # Example: heating_cop = db.Column(db.Float)
    sepr = db.Column(db.Float, nullable=True) # Example specific field moved here

    __mapper_args__ = {
        'polymorphic_identity': 'heat_pump',
    }

    def to_dict(self):
        data = super().to_dict()
        data.update({
             'sepr': self.sepr,
            # Add other specific fields
        })
        return data
    

class ResidentialVentilationUnit(HVACDevice):
    __tablename__ = 'residential_ventilation_units'
    id = db.Column(db.Integer, ForeignKey('hvacdevices.id'), primary_key=True)

    maximumflowrate = db.Column(db.Float, nullable=True)
    referenceflowrate = db.Column(db.Float, nullable=True)
    referencepressuredifference = db.Column(db.Float, nullable=True)
    typology = db.Column(db.String(100), nullable=True) 
    heatrecoverysystem = db.Column(String(100), nullable=True) 
    thermalefficiencyheatrecovery = db.Column(db.Float, nullable=True)
    specificpowerinput = db.Column(db.Float, nullable=True) # Key metric
    fandrivepowerinput = db.Column(db.Float, nullable=True)
    drivetype = db.Column(db.String(50), nullable=True)
    ductedunit = db.Column(db.String(50), nullable=True)
    controltypology = db.Column(db.String(100), nullable=True)
    specificenergyconsumptionwarm = db.Column(db.Float, nullable=True)
    specificenergyconsumptionaverage = db.Column(db.Float, nullable=True)
    specificenergyconsumptioncold = db.Column(db.Float, nullable=True)
    annualheatingsavedaverageclimate = db.Column(db.Float, nullable=True)
    energyclass = db.Column(db.String(10), nullable=True)
    maximuminternalleakagerate = db.Column(db.Float, nullable=True)
    maximumexternalleakagerate = db.Column(db.Float, nullable=True)

    __mapper_args__ = {
        'polymorphic_identity': 'residential_ventilation_unit', # Matches value in DEVICE_TYPES key
    }

    def to_dict(self):
        data = super().to_dict()
        data.update({
            'maximumflowrate': self.maximumflowrate,
            'referenceflowrate': self.referenceflowrate,
            'referencepressuredifference': self.referencepressuredifference,
            'typology': self.typology,
            'heatrecoverysystem': self.heatrecoverysystem,
            'thermalefficiencyheatrecovery': self.thermalefficiencyheatrecovery,
            'specificpowerinput': self.specificpowerinput,
            'fandrivepowerinput': self.fandrivepowerinput,
            'drivetype': self.drivetype,
            'ductedunit': self.ductedunit,
            'controltypology': self.controltypology,
            'specificenergyconsumptionwarm': self.specificenergyconsumptionwarm,
            'specificenergyconsumptionaverage': self.specificenergyconsumptionaverage,
            'specificenergyconsumptioncold': self.specificenergyconsumptioncold,
            'annualheatingsavedaverageclimate': self.annualheatingsavedaverageclimate,
            'energyclass': self.energyclass,
            'maximuminternalleakagerate': self.maximuminternalleakagerate,
            'maximumexternalleakagerate': self.maximumexternalleakagerate,
        })
        return data


# --- Add more subclasses as needed ---

MODEL_MAP = {
    'air_conditioner': AirConditioner,
    'heat_pump': HeatPump,
    'residential_ventilation_unit': ResidentialVentilationUnit
    # Add other types as you define their models
}