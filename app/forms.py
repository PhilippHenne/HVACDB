# app/forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, IntegerField, FloatField, SubmitField, SelectField, TextAreaField, SelectMultipleField
from wtforms.fields import DateField
from wtforms.validators import DataRequired, Optional, NumberRange, ValidationError, InputRequired
import json
from .models import DEVICE_TYPES


DEVICE_TYPE_CHOICES = [ (k, v) for k, v in DEVICE_TYPES.items() ]

# Custom validator for JSON
def validate_json(form, field):
    if field.data:
        try:
            json.loads(field.data)
        except json.JSONDecodeError:
            raise ValidationError('Invalid JSON format in custom fields.')


class HVACDeviceForm(FlaskForm):
    device_type = SelectField('Device Type', choices=[('', '-- Select Type --')] + DEVICE_TYPE_CHOICES, validators=[InputRequired()])
    manufacturer = StringField('Manufacturer', validators=[DataRequired()])
    model_identifier = StringField('Model Identifier', validators=[DataRequired()])
    market_entry = DateField('Market Entry Date', format='%Y-%m-%d', validators=[Optional()])
    market_exit = DateField('Market Exit Date (Optional)', format='%Y-%m-%d', validators=[Optional()])
    noise_level_dba = FloatField('Noise Level (dBA)', validators=[Optional()])
    price_currency = SelectField('Currency', choices=[('', '--'), ('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP'), ('JPY', 'JPY')], validators=[Optional()])
    price_amount = FloatField('Price Amount', validators=[Optional()])
    data_source = StringField('Data Source', validators=[Optional()])
    custom_fields = TextAreaField('Other Custom Fields (JSON format)', validators=[Optional()])

    eer = FloatField('EER', validators=[Optional()])
    seer = FloatField('SEER', validators=[Optional()])
    rated_power_cooling_kw = FloatField('Rated Power Cooling (kw)', validators=[Optional()])
    energy_class_cooling = StringField('Energy Class Cooling', validators=[Optional()])
    design_load_cooling_kw = FloatField('Design Load Cooling (kw)', validators=[Optional()])
    annual_consumption_cooling_kwh = FloatField('Annual Consumption Cooling (kw/h)', validators=[Optional()])
    rated_power_heating_kw = FloatField('Rated Power Heating (kw)', validators=[Optional()])
    cop_standard = FloatField('COP Standard', validators=[Optional()])
    scop_average = FloatField('SCOP Average', validators=[Optional()])
    energy_class_heating_average = StringField('Energy Class Heating avg', validators=[Optional()])
    design_load_heating_average_kw = FloatField('Design Load Heating avg (kw)', validators=[Optional()])
    annual_consumption_heating_average_kwh = FloatField('Annual consumption heating avg (kw)', validators=[Optional()])
    scop_warm = FloatField('SCOP Warm', validators=[Optional()])
    energy_class_heating_warm = StringField('Energy Class Heating Warm', validators=[Optional()])
    design_load_heating_warm_kw = FloatField('Design Load Heating Warm (kw)', validators=[Optional()])
    scop_cold = FloatField('SCOP Cold', validators=[Optional()])
    energy_class_heating_cold = StringField('Energy Class Heating Cold', validators=[Optional()])
    design_load_heating_cold_kw = FloatField('Design Load Heating Cold (kw)', validators=[Optional()])
    refrigerant_type = StringField('Refrigerant Type', validators=[Optional()])
    refrigerant_gwp = IntegerField('Refrigerant GWP', validators=[Optional()])
    noise_level_outdoor_cooling_db = FloatField('Noise Level Outdoor Cooling (db)', validators=[Optional()])
    maximumflowrate = FloatField('Maximum Flow Rate (m³/h) (Ventilator Only)', validators=[Optional()])
    specificpowerinput = FloatField('Specific Power Input (W/(m³/h)) (Ventilator Only)', validators=[Optional()])
    thermalefficiencyheatrecovery = FloatField('Heat Recovery Thermal Efficiency (%) (Ventilator Only)', validators=[Optional()])
    referenceflowrate = FloatField('Reference Flow Rate', validators=[Optional()])
    referencepressuredifference = FloatField('Reference Pressure Difference', validators=[Optional()])
    typology = StringField('Typology', validators=[Optional()])
    heatrecoverysystem = StringField('Heat Recovery System', validators=[Optional()])
    fandrivepowerinput = FloatField('Fan Drive Power Input', validators=[Optional()])
    drivetype = StringField('Drive Type', validators=[Optional()])
    ductedunit = StringField('Ducted Unit', validators=[Optional()])
    controltypology = StringField('Control Typology', validators=[Optional()])
    specificenergyconsumptionwarm = FloatField('Specific Energy Consumption Warm', validators=[Optional()])
    specificenergyconsumptionaverage = FloatField('Specific Energy Consumption Average', validators=[Optional()])
    specificenergyconsumptioncold = FloatField('Specific Energy Consumption Cold', validators=[Optional()])
    annualheatingsavedaverageclimate = FloatField('Annual Heating Saved Average Climate', validators=[Optional()])
    annualheatingsavedwarmclimate = FloatField('Annual Heating Saved Warm Climate', validators=[Optional()])
    annualheatingsavedcoldclimate = FloatField('Annual Heating Saved Cold Climate', validators=[Optional()])
    energyclass = StringField('Energy Class (Ventilator Only)', validators=[Optional()])
    maximuminternalleakagerate = FloatField('Maximum Internal Leakage Rate', validators=[Optional()])
    maximumexternalleakagerate = FloatField('Maximum External Leakage Rate', validators=[Optional()])

    submit = SubmitField('Add HVAC Device')


class CSVUploadForm(FlaskForm):
    # Add device type selection for the whole CSV file
    device_type = SelectField('Device Type for this CSV', choices=[('', '-- Select Type --')] + DEVICE_TYPE_CHOICES, validators=[InputRequired()])
    file = FileField('CSV File', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'CSV files only!')
    ])
    submit = SubmitField('Upload CSV')

STANDARD_FIELDS = [
    ('manufacturer', 'Manufacturer'),
    ('device_type', 'Device Type'),
    ('model_identifier', 'Model Identifier'),
    ('market_entry', 'Market Entry Date'),
    ('airflow_volume_m3h', 'Airflow Volume (m³/h)'),
    ('eer', 'EER'),
    ('seer', 'SEER'),
    ('sepr', 'SEPR'),
    ('noise_level_dba', 'Noise Level (dBA)'),
    ('price_amount', 'Price Amount'),
    ('price_currency', 'Price Currency'),
]

# Fields suitable for grouping
GROUPING_FIELDS = [
    ('', '-- Select Field --'),
    ('manufacturer', 'Manufacturer'),
    ('device_type', 'Device Type'),
    ('market_entry', 'Market Entry'),
    ('price_currency', 'Price Currency'),
]

class SearchForm(FlaskForm):
    # Keep existing simple filters
    manufacturer = StringField('Filter by Manufacturer', validators=[Optional()])
    device_type = SelectField('Filter by Device Type', choices=[('', 'Any')] + DEVICE_TYPE_CHOICES, validators=[Optional()]) # Filter by type
    
    # --- New Fields for Display ---
    fields_to_display = SelectMultipleField(
        'Select Standard Fields to Display',
        choices=STANDARD_FIELDS,
        validators=[Optional()],
        description="Select one or more standard fields to show in results."
    )
    custom_field_to_display = StringField(
        'Also Display Custom Field (Enter Key)',
        validators=[Optional()],
        render_kw={"placeholder": "e.g., design_load_cooling_kw"},
        description="Enter the exact key of one custom field to display."
    )

    # --- New Fields for Generic Filtering ---
    # (This is a simple filter, more complex filtering could be added)
    filter_field = SelectField(
        'Filter by Field',
        choices=[('', '-- Select Field --')] + STANDARD_FIELDS + [('custom', 'Custom Field...')],
        validators=[Optional()]
    )
    custom_filter_field = StringField(
        'Custom Filter Field Key',
        validators=[Optional()],
        render_kw={"placeholder": "Key if 'Custom Field...' selected above"}
    )
    filter_value = StringField(
        'Filter Value',
        validators=[Optional()],
        render_kw={"placeholder": "Value for the filter field"}
    )

    # --- New Field for Grouping ---
    group_by_field = SelectField(
        'Group Results By',
        choices=GROUPING_FIELDS,
        validators=[Optional()]
    )


    submit = SubmitField('Search / Analyze')
    # You might want a different submit button text