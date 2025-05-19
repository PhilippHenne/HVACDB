# app/forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, IntegerField, FloatField, SubmitField, SelectField, TextAreaField, SelectMultipleField, RadioField, DecimalField
from wtforms.fields import DateField # Ensure DateField is imported if used elsewhere
from wtforms.validators import DataRequired, Optional, NumberRange, ValidationError, InputRequired
import json
from .models import DEVICE_TYPES # For DEVICE_TYPE_CHOICES

# --- Field Definitions (Ideally in app/field_definitions.py and imported) ---
# For now, simplified version embedded. Ensure 'name' is unique for form field values.
# 'model_attr' is the actual SQLAlchemy attribute. 'model_class_name' is the Python class name.
FIELD_DEFINITIONS = {
    # Common
    'id': {'label': 'ID', 'model_attr': 'id', 'model_class_name': 'HVACDevice', 'type': 'integer', 'metric': False, 'searchable': True, 'displayable': True, 'groupable': False},
    'manufacturer': {'label': 'Manufacturer', 'model_attr': 'manufacturer', 'model_class_name': 'HVACDevice', 'type': 'string', 'metric': False, 'searchable': True, 'displayable': True, 'groupable': True},
    'model_identifier': {'label': 'Model Identifier', 'model_attr': 'model_identifier', 'model_class_name': 'HVACDevice', 'type': 'string', 'metric': False, 'searchable': True, 'displayable': True, 'groupable': False},
    'market_entry': {'label': 'Market Entry Date', 'model_attr': 'market_entry', 'model_class_name': 'HVACDevice', 'type': 'date', 'metric': False, 'searchable': True, 'displayable': True, 'groupable': True}, # Group by year special
    'noise_level_dba': {'label': 'Noise Level (dBA)', 'model_attr': 'noise_level_dba', 'model_class_name': 'HVACDevice', 'type': 'float', 'metric': True, 'searchable': True, 'displayable': True, 'groupable': False},
    # AC
    'ac_seer': {'label': 'SEER (AC)', 'model_attr': 'seer', 'model_class_name': 'AirConditioner', 'type': 'float', 'metric': True, 'searchable': True, 'displayable': True, 'groupable': False},
    'ac_scop_average': {'label': 'SCOP Average (AC)', 'model_attr': 'scop_average', 'model_class_name': 'AirConditioner', 'type': 'float', 'metric': True, 'searchable': True, 'displayable': True, 'groupable': False},
    'ac_refrigerant_type': {'label': 'Refrigerant (AC)', 'model_attr': 'refrigerant_type', 'model_class_name': 'AirConditioner', 'type': 'string', 'metric': False, 'searchable':True, 'displayable':True, 'groupable':True},

    # HP (Unified) - Add ALL relevant from your HeatPump model
    'hp_refrigerant': {'label': 'Refrigerant (HP)', 'model_attr': 'refrigerant', 'model_class_name': 'HeatPump', 'type': 'string', 'metric': False, 'searchable': True, 'displayable': True, 'groupable': True},
    'hp_scop_avg_lwt35': {'label': 'SCOP Avg LWT35 (HP)', 'model_attr': 'scop_avg_lwt35', 'model_class_name': 'HeatPump', 'type': 'float', 'metric': True, 'searchable': True, 'displayable': True, 'groupable': False},
    'hp_ph_a7_w35': {'label': 'Heating Cap (A7/W35 kW, HP)', 'model_attr': 'ph_a7_w35', 'model_class_name': 'HeatPump', 'type': 'float', 'metric': True, 'searchable': True, 'displayable': True, 'groupable': False},
    'hp_cop_a7_w35': {'label': 'COP (A7/W35, HP)', 'model_attr': 'cop_a7_w35', 'model_class_name': 'HeatPump', 'type': 'float', 'metric': True, 'searchable': True, 'displayable': True, 'groupable': False},
    'hp_model_type': {'label': 'Model Type (HP)', 'model_attr': 'model_type', 'model_class_name': 'HeatPump', 'type': 'string', 'metric': False, 'searchable': True, 'displayable': True, 'groupable': True},


    # RVU
    'rvu_specificpowerinput': {'label': 'Specific Power Input (RVU)', 'model_attr': 'specificpowerinput', 'model_class_name': 'ResidentialVentilationUnit', 'type': 'float', 'metric': True, 'searchable': True, 'displayable': True, 'groupable': False},
    'rvu_typology': {'label': 'Typology (RVU)', 'model_attr': 'typology', 'model_class_name': 'ResidentialVentilationUnit', 'type': 'string', 'metric': False, 'searchable':True, 'displayable':True, 'groupable':True},
    'rvu_thermalefficiencyheatrecovery': {'label': 'Thermal Eff. Heat Rec. (RVU %)', 'model_attr': 'thermalefficiencyheatrecovery', 'model_class_name': 'ResidentialVentilationUnit', 'type': 'float', 'metric': True, 'searchable': True, 'displayable': True, 'groupable': False},
}
SPECIAL_GROUPING_OPTIONS = {
    'market_entry_year': {'label': 'Market Entry Year', 'model_attr': 'market_entry'} # Actual attr is market_entry
}

DEVICE_TYPE_MODEL_MAPPING = {
    'air_conditioner': 'AirConditioner',
    'heat_pump': 'HeatPump',
    'residential_ventilation_unit': 'ResidentialVentilationUnit'
}

def get_initial_choices(purpose='displayable'):
    """Generates initial choices for dropdowns, including all possible fields."""
    choices = [('', '-- Select --')] if purpose != 'displayable_multiple' else []
    # Use a set to ensure unique field names (values for select options)
    seen_names = set()
    for name, definition in FIELD_DEFINITIONS.items():
        flag = False
        if purpose == 'searchable_metric' and definition.get('metric') and definition.get('searchable'):
            flag = True
        elif purpose == 'displayable' and definition.get('displayable'):
            flag = True
        elif purpose == 'displayable_multiple' and definition.get('displayable'):
             flag = True
        elif purpose == 'groupable' and definition.get('groupable'):
            flag = True
        
        if flag and name not in seen_names:
            choices.append((name, definition['label']))
            seen_names.add(name)
            
    if purpose == 'groupable': # Add special grouping options
        if 'market_entry_year' not in seen_names:
             choices.append(('market_entry_year', 'Market Entry Year'))
    return choices
# --- End Field Definitions ---


DEVICE_TYPE_CHOICES = [('', 'Any')] + [(k, v) for k, v in DEVICE_TYPES.items()]

DEVICE_TYPE_CHOICES_FOR_ADD_FORM = [('', '-- Select Type --')] + [(k, v) for k, v in DEVICE_TYPES.items()]

class HVACDeviceForm(FlaskForm):
    # Common Fields (must match 'model_attr' in FIELD_DEFINITIONS for 'HVACDevice' model_class_name)
    device_type = SelectField('Device Type', choices=DEVICE_TYPE_CHOICES_FOR_ADD_FORM, validators=[InputRequired()])
    manufacturer = StringField('Manufacturer', validators=[DataRequired()])
    model_identifier = StringField('Model Identifier', validators=[DataRequired()])
    market_entry = DateField('Market Entry Date', format='%Y-%m-%d', validators=[Optional()])
    market_exit = DateField('Market Exit Date', format='%Y-%m-%d', validators=[Optional()])
    noise_level_dba = FloatField('Noise Level (dBA)', validators=[Optional(), NumberRange(min=0)])
    price_currency = SelectField('Currency', choices=[('', '--'), ('USD', 'USD'), ('EUR', 'EUR')], validators=[Optional()])
    price_amount = FloatField('Price Amount', validators=[Optional(), NumberRange(min=0)])
    data_source = StringField('Data Source', validators=[Optional()])

    # AirConditioner Specific Fields (names must match 'model_attr' for AC in FIELD_DEFINITIONS)
    eer = FloatField('EER (AC)', validators=[Optional(), NumberRange(min=0)])
    seer = FloatField('SEER (AC)', validators=[Optional(), NumberRange(min=0)])
    scop_average = FloatField('SCOP Average (AC)', validators=[Optional(), NumberRange(min=0)])
    refrigerant_type = StringField('Refrigerant Type (AC)', validators=[Optional()]) # AC specific refrigerant
    refrigerant_gwp = IntegerField('Refrigerant GWP (AC)', validators=[Optional(), NumberRange(min=0)])
    rated_power_cooling_kw = FloatField('Rated Power Cooling (kW, AC)', validators=[Optional(), NumberRange(min=0)])
    # ... add ALL other AC fields you want on the form ...

    # HeatPump Specific Fields (names must match 'model_attr' for HP in FIELD_DEFINITIONS)
    # Note: 'refrigerant' is also a field name here. If it's distinct from AC's 'refrigerant_type',
    # your FIELD_DEFINITIONS 'model_attr' for HP refrigerant should be 'refrigerant'.
    trade_name = StringField('Trade Name (HP)', validators=[Optional()])
    model_type = StringField('Model Type (HP)', validators=[Optional()])
    refrigerant = StringField('Refrigerant (HP)', validators=[Optional()]) # HP specific refrigerant
    sound_power_level_lw = FloatField('Sound Power (Lw, HP)', validators=[Optional(), NumberRange(min=0)])
    seer_ac = FloatField('SEER (AC Mode, HP)', validators=[Optional(), NumberRange(min=0)]) # SEER if HP has cooling
    scop_avg_lwt35 = FloatField('SCOP Avg LWT35 (HP)', validators=[Optional(), NumberRange(min=0)])
    ph_a7_w35 = FloatField('Heating Cap (A7/W35 kW, HP)', validators=[Optional(), NumberRange(min=0)])
    cop_a7_w35 = FloatField('COP (A7/W35, HP)', validators=[Optional(), NumberRange(min=0)])
    scop_avg_lwt55 = FloatField('SCOP Avg LWT55 (HP)', validators=[Optional(), NumberRange(min=0)])
    # ... add ALL other flattened HP fields from your model that should be on the form ...

    # ResidentialVentilationUnit Specific Fields
    specificpowerinput = FloatField('Specific Power Input (RVU W/(m³/h))', validators=[Optional(), NumberRange(min=0)])
    thermalefficiencyheatrecovery = FloatField('Thermal Eff. Heat Recovery (RVU %)', validators=[Optional(), NumberRange(min=0, max=100)])
    maximumflowrate = FloatField('Max Flow Rate (m³/h, RVU)', validators=[Optional(), NumberRange(min=0)])
    typology = StringField('Typology (RVU)', validators=[Optional()])
    # ... add ALL other RVU fields ...

    submit = SubmitField('Add HVAC Device')
    

class CSVUploadForm(FlaskForm): # Unchanged
    device_type = SelectField('Device Type for this CSV', choices=[('', '-- Select Type --')] + [(k,v) for k,v in DEVICE_TYPES.items()], validators=[InputRequired()])
    file = FileField('CSV File', validators=[FileRequired(), FileAllowed(['csv'], 'CSV files only!')])
    submit = SubmitField('Upload CSV')


class SearchForm(FlaskForm):
    # --- Basic Search Filters ---
    manufacturer = StringField('Filter by Manufacturer', validators=[Optional()])
    device_type = SelectField('Filter by Device Type', choices=DEVICE_TYPE_CHOICES, validators=[Optional()], id="device_type_select")
    id_or_model_identifier = StringField('Search by ID or Model Identifier', validators=[Optional()])

    # --- NEW: Unified Core Metric Filters ---
    search_metric_name = SelectField('Metric to Search', validators=[Optional()], id="search_metric_name_select")
    search_metric_operator = SelectField('Operator', 
                                         choices=[('>=', '>='), ('<=', '<='), ('==', '=='), ('like', 'Contains (text)')], 
                                         default='>=', 
                                         validators=[Optional()],
                                         id="search_metric_operator_select")
    search_metric_value = StringField('Metric Value', validators=[Optional()], id="search_metric_value_input")
    
    # --- REMOVED old metric-specific fields ---
    # search_seer, search_scop, search_specificpowerinput, search_hp_refrigerant

    # --- NEW: Dynamic Display Options ---
    fields_to_display = SelectMultipleField(
        'Fields to Display in Results',
        validators=[Optional()],
        id="fields_to_display_select"
        # Choices will be populated by __init__ initially, then by JS
    )

    # --- Generic Filtering (Advanced - Retained for now, could be removed if new metric search is sufficient) ---
    filter_field = SelectField( # This could also be made dynamic eventually
        'Filter by Other Field (Advanced)',
        # Initial choices can be all possible non-metric fields or a subset
        validators=[Optional()], 
        id="adv_filter_field_select"
    )
    custom_filter_field = StringField( # Kept if 'custom' is selected in filter_field
        'Custom Filter Field Key (Advanced)',
        validators=[Optional()],
        render_kw={"placeholder": "Key if 'Custom Field...' selected"}
    )
    filter_value = StringField(
        'Filter Value (Advanced)',
        validators=[Optional()],
        render_kw={"placeholder": "Value for the advanced filter field"}
    )

    # --- NEW: Dynamic Grouping ---
    group_by_field = SelectField(
        'Group Results By',
        validators=[Optional()],
        id="group_by_field_select"
        # Choices will be populated by __init__ initially, then by JS
    )

    submit = SubmitField('Search / Analyze')

    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
        # Populate with all possible fields initially. JS will filter based on device_type.
        self.search_metric_name.choices = [('', '-- Select Metric --')] + get_initial_choices(purpose='searchable_metric')
        self.fields_to_display.choices = get_initial_choices(purpose='displayable_multiple')
        self.group_by_field.choices = [('', '-- Select Grouping --')] + get_initial_choices(purpose='groupable')
        
        # For advanced filter_field, provide a general list initially
        # This could be all displayable fields or a more curated list.
        adv_filter_choices = [('', '-- Select Field --')] + get_initial_choices(purpose='displayable') + [('custom', 'Custom Field...')]
        self.filter_field.choices = adv_filter_choices


def coerce_int_or_none(value):
    """Coerces a value to an int or None if it's an empty string or truly None."""
    if value == '' or value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError): # Catch TypeError as well for safety
        # Let a validator handle the message if coercion fails for non-empty string
        # For WTForms, if coercion fails, data is often set to None or original,
        # and validators like NumberRange should catch it.
        # To be more explicit for SelectField with bad coerce:
        raise ValidationError('Invalid selection or non-integer value provided where integer expected.')



class TCOCalculatorForm(FlaskForm):
    annual_heat_demand = FloatField('Annual Heat Demand (kWh/year)', validators=[InputRequired(), NumberRange(min=0)], description="...")
    electricity_price = FloatField('Electricity Price (€/kWh or similar)', validators=[InputRequired(), NumberRange(min=0)], description="...")
    annual_maintenance_cost = FloatField('Annual Maintenance Cost (€/year)', validators=[InputRequired(), NumberRange(min=0)], description="...")
    system_lifetime = IntegerField('System Lifetime (Years)', validators=[InputRequired(), NumberRange(min=1, max=50)], description="...")
    discount_rate = FloatField('Discount Rate (e.g., 0.04 for 4%)', validators=[InputRequired(), NumberRange(min=0, max=1)], description="...")
    capital_cost_subsidy = FloatField('Capital Cost Subsidy (%)', validators=[Optional(), NumberRange(min=0)], default=0.0, description="...")

    hp_data_source = RadioField('Heat Pump Data Source', choices=[('custom', 'Enter Custom HP Data'), ('database', 'Select HP from Database')], default='custom', validators=[InputRequired()])

    custom_hp_price = FloatField('HP Capital Cost (€) (Custom)', validators=[Optional(), NumberRange(min=0)], description="...")
    custom_hp_scop = FloatField('SCOP (Custom HP)', validators=[Optional(), NumberRange(min=0.1)], description="...")

    db_hp_id = SelectField(
        'Select Heat Pump from Database', 
        coerce=coerce_int_or_none, # USE CUSTOM COERCE FUNCTION
        validators=[Optional()], # Validation if 'database' source is chosen is in custom validate method
        description="Choose an existing heat pump from the database."
    )
    db_hp_price_override = FloatField('HP Capital Cost (€) (DB HP)', validators=[Optional(), NumberRange(min=0)], description="...")
    
    submit = SubmitField('Calculate TCO')

    def validate(self, extra_validators=None):
        # Call parent validation first
        if not super().validate(extra_validators):
            return False
        
        valid_form = True # Assume valid initially
        if self.hp_data_source.data == 'custom':
            if self.custom_hp_price.data is None:
                self.custom_hp_price.errors.append('Capital cost is required for custom heat pump.')
                valid_form = False
            if self.custom_hp_scop.data is None:
                self.custom_hp_scop.errors.append('SCOP is required for custom heat pump.')
                valid_form = False
        elif self.hp_data_source.data == 'database':
            # self.db_hp_id.data will be an int or None due to coerce_int_or_none
            if self.db_hp_id.data is None: 
                self.db_hp_id.errors.append('Please select a heat pump from the database.')
                valid_form = False
            # Price for DB heat pump will be checked in the route (override or from DB record)
        return valid_form
