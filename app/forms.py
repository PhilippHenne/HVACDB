# app/forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, IntegerField, FloatField, SubmitField, SelectField, SelectMultipleField, TextAreaField, DateField
from wtforms.validators import DataRequired, Optional, NumberRange, ValidationError
import json # To validate JSON input

# Custom validator for JSON
def validate_json(form, field):
    if field.data:
        try:
            json.loads(field.data)
        except json.JSONDecodeError:
            raise ValidationError('Invalid JSON format in custom fields.')

class HVACDeviceForm(FlaskForm):
    manufacturer = StringField('Manufacturer', validators=[DataRequired()])
    market_entry = DateField('Market Entry Date', format='%Y-%m-%d', validators=[DataRequired()])
    device_type = StringField('Device Type', validators=[DataRequired()])
    power_rating_kw = FloatField('Power Rating (kW)', validators=[Optional()])
    airflow_volume_m3h = FloatField('Airflow Volume (m³/h)', validators=[Optional()])
    eer = FloatField('Energy Efficiency Ratio (EER)', validators=[Optional()])
    seer = FloatField('Seasonal Energy Efficiency Ratio (SEER)', validators=[Optional()])
    sepr = FloatField('Seasonal Energy Performance Ratio (SEPR)', validators=[Optional()])
    heat_recovery_rate = FloatField('Heat Recovery Rate (%)', validators=[Optional()])
    fan_performance = FloatField('Fan Performance', validators=[Optional()])
    temperature_range = StringField('Temperature Range', validators=[Optional()])
    noise_level_dba = FloatField('Noise Level (dBA)', validators=[Optional()])
    price_currency = SelectField('Currency', choices=[('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP'), ('JPY', 'JPY')], validators=[Optional()])
    price_amount = FloatField('Price Amount', validators=[Optional()])
    units_sold_year = IntegerField('Units Sold Year', validators=[Optional()])
    units_sold_count = IntegerField('Units Sold Count', validators=[Optional()])
    data_source = StringField('Data Source', validators=[Optional()])

    # Add TextArea for custom fields (e.g., JSON format)
    custom_fields = TextAreaField('Custom Fields (JSON format)',
                                  description='Enter additional fields as a JSON object, e.g., {"certification": "Energy Star", "warranty_years": 5}',
                                  validators=[Optional()]) # Add validate_json if strict validation is needed immediately: , validate_json

    submit = SubmitField('Add HVAC Device')

class CSVUploadForm(FlaskForm):
    file = FileField('CSV File', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'CSV files only!')
    ])
    submit = SubmitField('Upload CSV')


STANDARD_FIELDS = [
    ('manufacturer', 'Manufacturer'),
    ('device_type', 'Device Type'),
    ('market_entry', 'Market Entry Date'),
    ('power_rating_kw', 'Power Rating (kW)'),
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
    ('', '-- Select Field --'), # Default empty choice
    ('manufacturer', 'Manufacturer'),
    ('device_type', 'Device Type'),
    ('market_entry', 'Market Entry'), # We'll extract year in backend
    ('price_currency', 'Price Currency'),
]

class SearchForm(FlaskForm):
    # Keep existing simple filters
    manufacturer = StringField('Filter by Manufacturer', validators=[Optional()], render_kw={"placeholder": "Enter manufacturer name"})
    device_type = StringField('Filter by Device Type', validators=[Optional()], render_kw={"placeholder": "Enter device type"})

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