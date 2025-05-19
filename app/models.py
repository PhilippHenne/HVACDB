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
    __tablename__ = 'hvacdevices'

    id = db.Column(db.Integer, primary_key=True)
    # --- Common Fields (ensure these are present in your unified CSVs or handled) ---
    # model_identifier is crucial and should be consistently named in your CSVs (e.g., 'model_identifier')
    # manufacturer is also crucial.
    manufacturer = db.Column(db.String(255), nullable=False, index=True)
    model_identifier = db.Column(db.String(255), nullable=False, index=True) 
    
    market_entry = db.Column(db.Date, nullable=True, index=True)
    market_exit = db.Column(db.Date, nullable=True)
    noise_level_dba = db.Column(db.Float, nullable=True) # General noise level, if applicable as common
    price_currency = db.Column(db.String(3), nullable=True)
    price_amount = db.Column(db.Float, nullable=True)
    data_source = db.Column(db.String(255), nullable=True) # Source of the data entry
    
    created_at = db.Column(db.TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = db.Column(db.TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    device_type = db.Column(db.String(50), nullable=False, index=True)

    __mapper_args__ = {
        'polymorphic_identity': 'hvac_device_base',
        'polymorphic_on': device_type
    }

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.id}: {self.manufacturer} {self.model_identifier}>'

    def to_dict(self):
        common_data = {
            'id': self.id,
            'device_type': DEVICE_TYPES.get(self.device_type, self.device_type), # Show user-friendly type name
            'manufacturer': self.manufacturer,
            'model_identifier': self.model_identifier,
            'market_entry': self.market_entry.isoformat() if isinstance(self.market_entry, date) else None,
            'market_exit': self.market_exit.isoformat() if isinstance(self.market_exit, date) else None,
            'noise_level_dba': self.noise_level_dba,
            'price_currency': self.price_currency,
            'price_amount': self.price_amount,
            'data_source': self.data_source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        return common_data
    

# --- Air Conditioner Subclass ---
class AirConditioner(HVACDevice):
    __tablename__ = 'air_conditioners'

    id = db.Column(db.Integer, ForeignKey('hvacdevices.id'), primary_key=True)

    eer = db.Column(db.Float, nullable=True)
    seer = db.Column(db.Float, nullable=True)
    rated_power_cooling_kw = db.Column(db.Float, nullable=True)
    energy_class_cooling = db.Column(db.String(50), nullable=True)
    design_load_cooling_kw = db.Column(db.Float, nullable=True)
    annual_consumption_cooling_kwh = db.Column(db.Float, nullable=True)

    rated_power_heating_kw = db.Column(db.Float, nullable=True)
    cop_standard = db.Column(db.Float, nullable=True)
    scop_average = db.Column(db.Float, nullable=True)
    energy_class_heating_average = db.Column(db.String(50), nullable=True)
    design_load_heating_average_kw = db.Column(db.Float, nullable=True)
    annual_consumption_heating_average_kwh = db.Column(db.Float, nullable=True)

    scop_warm = db.Column(db.Float, nullable=True)
    energy_class_heating_warm = db.Column(db.String(50), nullable=True)
    design_load_heating_warm_kw = db.Column(db.Float, nullable=True)
    annual_consumption_heating_warm_kwh = db.Column(db.Float, nullable=True)


    scop_cold = db.Column(db.Float, nullable=True)
    energy_class_heating_cold = db.Column(db.String(50), nullable=True)
    design_load_heating_cold_kw = db.Column(db.Float, nullable=True)
    annual_consumption_heating_cold_kwh = db.Column(db.Float, nullable=True)


    refrigerant_type = db.Column(db.String(100), nullable=True)
    refrigerant_gwp = db.Column(db.Integer, nullable=True)
    noise_level_outdoor_cooling_db = db.Column(db.Float, nullable=True)

    # Seasonal Efficiency Parameters ηs (eta_s)
    eta_s_cooling_percent = db.Column(db.Float, nullable=True)
    eta_s_heating_average_percent = db.Column(db.Float, nullable=True)
    eta_s_heating_warm_percent = db.Column(db.Float, nullable=True)
    eta_s_heating_cold_percent = db.Column(db.Float, nullable=True)

    # Part-Load Cooling (Eurovent)
    pc_cooling_cond_b_kw = db.Column(db.Float, nullable=True)
    eer_cooling_cond_b = db.Column(db.Float, nullable=True)
    pc_cooling_cond_c_kw = db.Column(db.Float, nullable=True)
    eer_cooling_cond_c = db.Column(db.Float, nullable=True)
    pc_cooling_cond_d_kw = db.Column(db.Float, nullable=True)
    eer_cooling_cond_d = db.Column(db.Float, nullable=True)

    # Part-Load Heating (Eurovent)
    ph_heating_cond_a_kw = db.Column(db.Float, nullable=True)
    cop_heating_cond_a = db.Column(db.Float, nullable=True)
    ph_heating_cond_b_kw = db.Column(db.Float, nullable=True)
    cop_heating_cond_b = db.Column(db.Float, nullable=True)
    ph_heating_cond_c_kw = db.Column(db.Float, nullable=True)
    cop_heating_cond_c = db.Column(db.Float, nullable=True)
    ph_heating_cond_d_kw = db.Column(db.Float, nullable=True)
    cop_heating_cond_d = db.Column(db.Float, nullable=True)

    # TOL and Tbivalent points (Eurovent)
    tol_temp_heating = db.Column(db.Float, nullable=True)
    ph_heating_tol_kw = db.Column(db.Float, nullable=True)
    cop_heating_tol = db.Column(db.Float, nullable=True)
    tbiv_temp_heating = db.Column(db.Float, nullable=True)
    ph_heating_tbiv_kw = db.Column(db.Float, nullable=True)
    cop_heating_tbiv = db.Column(db.Float, nullable=True)

    # Standby/Off-mode power consumption
    power_standby_cooling_kw = db.Column(db.Float, nullable=True)
    power_off_cooling_kw = db.Column(db.Float, nullable=True)
    power_standby_heating_kw = db.Column(db.Float, nullable=True)
    power_off_heating_kw = db.Column(db.Float, nullable=True)

    # Additional Sound Data
    noise_level_indoor_cooling_db = db.Column(db.Float, nullable=True)
    noise_level_outdoor_heating_db = db.Column(db.Float, nullable=True)
    noise_level_indoor_heating_db = db.Column(db.Float, nullable=True)

    # Other technical details
    capacity_control_type = db.Column(db.String(100), nullable=True)
    degradation_coeff_cooling_cd = db.Column(db.Float, nullable=True)

    __mapper_args__ = {
        'polymorphic_identity': 'air_conditioner', # Matches value stored in hvac_devices_base.device_type
    }

    def to_dict(self):
        data = super().to_dict() # Get common fields from HVACDevice (manufacturer, market_entry, device_type etc.)
        data.update({
            # Existing specific fields
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
            'annual_consumption_heating_warm_kwh': self.annual_consumption_heating_warm_kwh, # Added
            'scop_cold': self.scop_cold,
            'energy_class_heating_cold': self.energy_class_heating_cold,
            'design_load_heating_cold_kw': self.design_load_heating_cold_kw,
            'annual_consumption_heating_cold_kwh': self.annual_consumption_heating_cold_kwh, # Added
            'refrigerant_type': self.refrigerant_type,
            'refrigerant_gwp': self.refrigerant_gwp,
            'noise_level_outdoor_cooling_db': self.noise_level_outdoor_cooling_db,
            'model_identifier': self.model_identifier,
            'eta_s_cooling_percent': self.eta_s_cooling_percent,
            'eta_s_heating_average_percent': self.eta_s_heating_average_percent,
            'eta_s_heating_warm_percent': self.eta_s_heating_warm_percent,
            'eta_s_heating_cold_percent': self.eta_s_heating_cold_percent,
            'pc_cooling_cond_b_kw': self.pc_cooling_cond_b_kw,
            'eer_cooling_cond_b': self.eer_cooling_cond_b,
            'pc_cooling_cond_c_kw': self.pc_cooling_cond_c_kw,
            'eer_cooling_cond_c': self.eer_cooling_cond_c,
            'pc_cooling_cond_d_kw': self.pc_cooling_cond_d_kw,
            'eer_cooling_cond_d': self.eer_cooling_cond_d,
            'ph_heating_cond_a_kw': self.ph_heating_cond_a_kw,
            'cop_heating_cond_a': self.cop_heating_cond_a,
            'ph_heating_cond_b_kw': self.ph_heating_cond_b_kw,
            'cop_heating_cond_b': self.cop_heating_cond_b,
            'ph_heating_cond_c_kw': self.ph_heating_cond_c_kw,
            'cop_heating_cond_c': self.cop_heating_cond_c,
            'ph_heating_cond_d_kw': self.ph_heating_cond_d_kw,
            'cop_heating_cond_d': self.cop_heating_cond_d,
            'tol_temp_heating': self.tol_temp_heating,
            'ph_heating_tol_kw': self.ph_heating_tol_kw,
            'cop_heating_tol': self.cop_heating_tol,
            'tbiv_temp_heating': self.tbiv_temp_heating,
            'ph_heating_tbiv_kw': self.ph_heating_tbiv_kw,
            'cop_heating_tbiv': self.cop_heating_tbiv,
            'power_standby_cooling_kw': self.power_standby_cooling_kw,
            'power_off_cooling_kw': self.power_off_cooling_kw,
            'power_standby_heating_kw': self.power_standby_heating_kw,
            'power_off_heating_kw': self.power_off_heating_kw,
            'noise_level_indoor_cooling_db': self.noise_level_indoor_cooling_db,
            'noise_level_outdoor_heating_db': self.noise_level_outdoor_heating_db,
            'noise_level_indoor_heating_db': self.noise_level_indoor_heating_db,
            'capacity_control_type': self.capacity_control_type,
            'degradation_coeff_cooling_cd': self.degradation_coeff_cooling_cd,
        })
        return data

class HeatPump(HVACDevice):
    __tablename__ = 'heat_pumps'
    id = db.Column(db.Integer, ForeignKey('hvacdevices.id'), primary_key=True)

    # --- Base Characteristics (from your KPI_COLUMN_MAP or other direct fields) ---
    # model_identifier and manufacturer are inherited from HVACDevice
    trade_name = db.Column(db.String(255), nullable=True)
    model_type = db.Column(db.String(100), nullable=True) # e.g., Air/Water
    software_name = db.Column(db.String(100), nullable=True)
    software_version = db.Column(db.String(50), nullable=True)
    # factory_country = db.Column(db.String(100), nullable=True) # Optional
    # factory_city = db.Column(db.String(100), nullable=True)    # Optional
    
    refrigerant = db.Column(db.String(50), nullable=True) # This is HP specific refrigerant
    main_power_supply = db.Column(db.String(100), nullable=True)
    control_of_pump_speed = db.Column(db.String(100), nullable=True)
    reversibility_on_water_side = db.Column(db.String(50), nullable=True)
    simultaneous_heating = db.Column(db.String(50), nullable=True)
    esp_duct = db.Column(db.String(50), nullable=True) # Could be float if always numeric
    outdoor_heat_exchanger_type = db.Column(db.String(100), nullable=True)
    indoor_heat_exchanger_type = db.Column(db.String(100), nullable=True)
    expansion_valve_type = db.Column(db.String(100), nullable=True)
    
    unit_capacity_control = db.Column(db.String(100), nullable=True)
    compressor_type = db.Column(db.String(100), nullable=True)
    compressor_inverter = db.Column(db.String(50), nullable=True) # e.g., 'Yes', 'No', or type
    compressor_number = db.Column(db.Integer, nullable=True)

    # Acoustics
    sound_power_level_lw = db.Column(db.Float, nullable=True)

    # Cooling Performance (Flattened KPIs)
    pc_a35_w12_7 = db.Column(db.Float, nullable=True)    # Cooling Capacity
    eer_a35_w12_7 = db.Column(db.Float, nullable=True)   # EER
    seer_ac = db.Column(db.Float, nullable=True)         # SEER for AC mode
    eta_sc_ac = db.Column(db.Float, nullable=True)       # ηsc for AC mode

    # Heating Performance - LWT 35°C (Average Climate) (Flattened KPIs)
    pdesignh_avg_lwt35 = db.Column(db.Float, nullable=True)
    scop_avg_lwt35 = db.Column(db.Float, nullable=True)
    eta_sh_avg_lwt35 = db.Column(db.Float, nullable=True)
    ph_a7_w35 = db.Column(db.Float, nullable=True)      # Heating Capacity at A7/W35
    cop_a7_w35 = db.Column(db.Float, nullable=True)     # COP at A7/W35
    ph_a2_w35 = db.Column(db.Float, nullable=True)
    cop_a2_w35 = db.Column(db.Float, nullable=True)
    ph_am7_w35 = db.Column(db.Float, nullable=True)
    cop_am7_w35 = db.Column(db.Float, nullable=True)

    # Heating Performance - LWT 55°C (Average Climate) (Flattened KPIs)
    pdesignh_avg_lwt55 = db.Column(db.Float, nullable=True)
    scop_avg_lwt55 = db.Column(db.Float, nullable=True)
    eta_sh_avg_lwt55 = db.Column(db.Float, nullable=True)
    ph_a7_w55_approx = db.Column(db.Float, nullable=True) # Or ph_a7_w55_65 etc.
    cop_a7_w55_approx = db.Column(db.Float, nullable=True)

    # SEPR (Flattened KPIs)
    sepr_mt = db.Column(db.Float, nullable=True)
    sepr_ht = db.Column(db.Float, nullable=True)
    sepr_lt = db.Column(db.Float, nullable=True)

    # Standby Power (Flattened KPIs)
    psbc_standby_cooling = db.Column(db.Float, nullable=True)
    psbh_standby_heating = db.Column(db.Float, nullable=True)

    # REMOVED: Relationship to HeatPumpPerformance
    # performance_data = relationship("HeatPumpPerformance", back_populates="heat_pump", cascade="all, delete-orphan")

    __mapper_args__ = {
        'polymorphic_identity': 'heat_pump',
    }

    def to_dict(self):
        data = super().to_dict()
        data.update({
            # Base characteristics specific to HeatPump or previously in HeatPump table
            'trade_name': self.trade_name,
            'model_type': self.model_type,
            'software_name': self.software_name,
            'software_version': self.software_version,
            'refrigerant': self.refrigerant,
            'main_power_supply': self.main_power_supply,
            'control_of_pump_speed': self.control_of_pump_speed,
            'reversibility_on_water_side': self.reversibility_on_water_side,
            'simultaneous_heating': self.simultaneous_heating,
            'esp_duct': self.esp_duct,
            'outdoor_heat_exchanger_type': self.outdoor_heat_exchanger_type,
            'indoor_heat_exchanger_type': self.indoor_heat_exchanger_type,
            'expansion_valve_type': self.expansion_valve_type,
            'unit_capacity_control': self.unit_capacity_control,
            'compressor_type': self.compressor_type,
            'compressor_inverter': self.compressor_inverter,
            'compressor_number': self.compressor_number,
            
            # Flattened KPIs
            'sound_power_level_lw': self.sound_power_level_lw,
            'pc_a35_w12_7': self.pc_a35_w12_7,
            'eer_a35_w12_7': self.eer_a35_w12_7,
            'seer_ac': self.seer_ac,
            'eta_sc_ac': self.eta_sc_ac,
            'pdesignh_avg_lwt35': self.pdesignh_avg_lwt35,
            'scop_avg_lwt35': self.scop_avg_lwt35,
            'eta_sh_avg_lwt35': self.eta_sh_avg_lwt35,
            'ph_a7_w35': self.ph_a7_w35,
            'cop_a7_w35': self.cop_a7_w35,
            'ph_a2_w35': self.ph_a2_w35,
            'cop_a2_w35': self.cop_a2_w35,
            'ph_am7_w35': self.ph_am7_w35,
            'cop_am7_w35': self.cop_am7_w35,
            'pdesignh_avg_lwt55': self.pdesignh_avg_lwt55,
            'scop_avg_lwt55': self.scop_avg_lwt55,
            'eta_sh_avg_lwt55': self.eta_sh_avg_lwt55,
            'ph_a7_w55_approx': self.ph_a7_w55_approx,
            'cop_a7_w55_approx': self.cop_a7_w55_approx,
            'sepr_mt': self.sepr_mt,
            'sepr_ht': self.sepr_ht,
            'sepr_lt': self.sepr_lt,
            'psbc_standby_cooling': self.psbc_standby_cooling,
            'psbh_standby_heating': self.psbh_standby_heating,
        })
        # Remove any keys that are None if desired, or let them be null in JSON
        # data = {k: v for k, v in data.items() if v is not None} # Optional: removes None values from dict
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
    annualheatingsavedwarmclimate = db.Column(db.Float, nullable=True)
    annualheatingsavedcoldclimate = db.Column(db.Float, nullable=True)
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
            'annualheatingsavedwarmclimate': self.annualheatingsavedwarmclimate,
            'annualheatingsavedcoldclimate': self.annualheatingsavedcoldclimate,
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