from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, IntegerField, FloatField, SubmitField, SelectField
from wtforms.validators import DataRequired, Optional, NumberRange

class HVACDeviceForm(FlaskForm):
    manufacturer = StringField('Manufacturer', validators=[DataRequired()])
    market_entry_year = IntegerField('Market Entry Year', validators=[DataRequired(), NumberRange(min=1900, max=2100)])
    device_type = StringField('Device Type', validators=[DataRequired()])
    power_rating_kw = FloatField('Power Rating (kW)', validators=[DataRequired()])
    airflow_volume_m3h = FloatField('Airflow Volume (m³/h)', validators=[DataRequired()])
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
    submit = SubmitField('Add HVAC Device')

class CSVUploadForm(FlaskForm):
    file = FileField('CSV File', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'CSV files only!')
    ])
    submit = SubmitField('Upload CSV')

class SearchForm(FlaskForm):
    manufacturer = StringField('Manufacturer', validators=[Optional()])
    device_type = StringField('Device Type', validators=[Optional()])
    min_efficiency = FloatField('Minimum EER', validators=[Optional()])
    max_year = IntegerField('Maximum Year', validators=[Optional()])
    min_year = IntegerField('Minimum Year', validators=[Optional()])
    submit = SubmitField('Search')