# HVAC Device Database - Project Documentation

This document provides instructions on how to set up and run the HVAC Device Database project, as well as a guide for developers on how to extend it by adding new device types.

## Part 1: General Project Setup and Running Instructions

Follow these steps to get the project running on your local machine.

### 1. Prerequisites

* **Python:** Version 3.8 or higher recommended.
* **pip:** Python package installer (usually comes with Python).
* **Git:** For cloning the project repository (if applicable).
* **PostgreSQL:** A running PostgreSQL server instance. You will need to be able to create a new database and a user for this application.

### 2. Clone the repository

```bash
git clone <repository_url>
cd <project_directory_name>
```

### 3. Setting Up a Virtual Environment

It's highly recommended to use a Python virtual environment to manage project dependencies.
* Create a virtual environment:
    * On Windows:

    ```bash
    venv\Scripts\activate
    ```
    * On macOS/Linux

    ```bash
    source venv/bin/activate
    ```
### 4. Installing Dependencies
The project should have a ```requirements.txt``` file listing all necessary Python packages. Install them using:

    ```bash
    pip install -r requirements.txt
    ```

### 5. Database Setup (PostgreSQL)
* Create a PostgreSQL Database:
    * Using ````psql```` or a GUI tool (like pgAdmin), create a new database for the project (e.g., ````hvac_db````).
    * Create a new user/role with a password that has privileges on this database (e.g., user ````hvac_user````).
* Configure Database Connection:
    * The application uses a ````.env```` file (loaded by ````python-dotenv```` via ````config.py````) to manage environment variables, including the database URL.
    * Create a file named ````.env```` in the root directory of the project (the same level as ````run.py```` and ````config.py````).
    * Add your database connection string to the ````.env```` file: 

    ```
    DATABASE_URL="postgresql://hvac_user:your_password@localhost:5432/hvac_db"
    SECRET_KEY="a_very_secret_random_key_for_flask_sessions"
    # FLASK_APP=run.py (Optional, can be set in terminal if not using python run.py)
    # FLASK_DEBUG=1 (Optional, for development mode, set to 0 for production)
    ```
    Replace ````hvac_user````, ````your_password````, ````localhost:5432```` (if different), and ````hvac_db```` with your actual PostgreSQL details. The ````SECRET_KEY```` is used by Flask for session management and should be a long, random string.

### 6. Running Database Migrations
The project uses Flask-Migrate to manage database schema changes.
* Set Flask Application Environment Variable (if not running python run.py directly):
    * macOS/Linux: ````export FLASK_APP=run.py````
    * Windows: ````set FLASK_APP=run.py```` (This tells the flask command how to load your app).
* Initialize Migrations (if this is the very first time setting up migrations for the project):

```bash
flask db init
```
* Create a Migration:
After making changes to your models in ````app/models.py````, generate a new migration script:

    ```bash
    flask db migrate -m "Descriptive message about changes, e.g., initial_migration_or_add_new_feature"
    ```
* Apply Migrations:
This command applies any pending migrations to create or update your database tables.

    ```bash
    flask db upgrade
    ```

This should create all the necessary tables based on your models.

### 7. Running the Flask Application
* Ensure your virtual environment is activated.
* Ensure ````FLASK_APP=run.py```` is set (either in your shell or in the ````.env```` file if your ````run.py```` loads it early, though typically it's for the flask CLI).

    ```bash
    flask run
    ```

    or

    ```bash
    python run.py
    ```

* The application will typically be available at ````http://127.0.0.1:5000/```` in your web browser. The console output will confirm the address.

## Part 2: Adding a New Device Type
This section outlines the steps required to add support for a new type of HVAC device to the application. Let's assume you want to add a "Chiller" device type.

### Step 1: Define the Model (app/models.py)
1. Create New Model Class:
Define a new Python class for your device type (e.g., Chiller) that inherits from HVACDevice. Add specific columns (````db.Column````) for attributes unique to this new device type.

    ```Python
    # In app/models.py
    class Chiller(HVACDevice):
        __tablename__ = 'chillers' # Choose a table name
        id = db.Column(db.Integer, ForeignKey('hvacdevices.id'), primary_key=True)

        # Chiller-specific attributes
        cooling_capacity_kw = db.Column(db.Float, nullable=True)
        eer_chiller = db.Column(db.Float, nullable=True) # Energy Efficiency Ratio for chillers
        refrigerant_type_chiller = db.Column(db.String(100), nullable=True)
        # ... other chiller-specific fields ...

        __mapper_args__ = {
            'polymorphic_identity': 'chiller', # Unique key for this device type
        }

        def to_dict(self):
            data = super().to_dict()
            data.update({
                'cooling_capacity_kw': self.cooling_capacity_kw,
                'eer_chiller': self.eer_chiller,
                'refrigerant_type_chiller': self.refrigerant_type_chiller,
                # ... add other specific fields to the dictionary ...
            })
            return data
    ```
2. Update ````DEVICE_TYPES```` Dictionary:
Add the new device type key and its user-friendly display name.

    ```Python
    # In app/models.py
    DEVICE_TYPES = {
        'air_conditioner': 'Air Conditioner',
        'heat_pump': 'Heat Pump',
        'residential_ventilation_unit': 'Residential Ventilation Units',
        'chiller': 'Chiller', # New entry
    }
    ```
    3. Update ````MODEL_MAP```` Dictionary:
    Map the new device type key to its model class.

    ```Python
    # In app/models.py
    MODEL_MAP = {
        'air_conditioner': AirConditioner,
        'heat_pump': HeatPump,
        'residential_ventilation_unit': ResidentialVentilationUnit,
        'chiller': Chiller, # New entry
    }
    ```

### Step 2: Define Fields for UI and Logic
Update the ````FIELD_DEFINITIONS```` dictionary in ```app/forms.py``` to include definitions for the new device type's specific attributes.
1. Add to ````FIELD_DEFINITIONS````:
For each new attribute in your Chiller model that you want to be searchable, displayable, or groupable, add an entry.

    ```Python
    # In app/field_definitions.py (or equivalent)
    FIELD_DEFINITIONS = {
        # ... existing common and other device-specific fields ...
        'chiller_cooling_capacity': {'label': 'Cooling Capacity (kW, Chiller)', 'model_attr': 'cooling_capacity_kw', 'model_class_name': 'Chiller', 'type': 'float', 'metric': True, 'searchable': True, 'displayable': True, 'groupable': False},
        'chiller_eer': {'label': 'EER (Chiller)', 'model_attr': 'eer_chiller', 'model_class_name': 'Chiller', 'type': 'float', 'metric': True, 'searchable': True, 'displayable': True, 'groupable': False},
        'chiller_refrigerant': {'label': 'Refrigerant (Chiller)', 'model_attr': 'refrigerant_type_chiller', 'model_class_name': 'Chiller', 'type': 'string', 'metric': False, 'searchable': True, 'displayable': True, 'groupable': True},
        # ... other chiller fields ...
    }
    ```

* name (e.g., ````chiller_eer````): A unique key used in forms and JavaScript. Use a prefix (e.g., ````chiller_````) to avoid naming collisions with attributes from other device types if their ````model_attr```` names are similar.
* ````model_identifier````: User-friendly name for display.
* ````model_attr````: The actual attribute name in your Chiller SQLAlchemy model (e.g., eer_chiller).
* ````model_class_name````: The string name of your new model class (e.g., 'Chiller').
* ````model_class_name````: The string name of your new model class (e.g., 'Chiller').
* ````metric````, ````searchable````, ````displayable````, ````groupable````: Boolean flags indicating how the field can be used.

2. Update DEVICE_TYPE_MODEL_MAPPING in ```app/forms.py```:
The helper functions (like ````get_fields_for_type````) that use these definitions should then automatically pick up the new device type's fields.

### Step 3: Update Forms (```app/forms.py```)

1. ```DEVICE_TYPE_CHOICES```: This list, used by ````SelectField```` for device type selection (e.g., in ````SearchForm```` and ````HVACDeviceForm````), is typically derived from ````models.DEVICE_TYPES````. If you've updated ````models.DEVICE_TYPES````, this should reflect automatically when the application restarts. Ensure it's correctly populated, for example:

    ```Python
    # At the top of app/forms.py or where choices are defined
    from .models import DEVICE_TYPES as app_device_types # Import with an alias if needed
    DEVICE_TYPE_CHOICES_FOR_FORM = [('', 'Any')] + [(k, v) for k, v in app_device_types.items()]
    # For add form, you might not want 'Any':
    DEVICE_TYPE_CHOICES_FOR_ADD_FORM = [('', '-- Select Type --')] + [(k, v) for k, v in app_device_types.items()]
    ```

2. ````HVACDeviceForm````:
Add the new Chiller-specific fields to this "master" form if you want them to be available for manual data entry on the "Add Device" page. The field names in the form class (e.g., ````eer_chiller````) must match the ````model_attr```` names you used in ````FIELD_DEFINITIONS```` and your ````Chiller```` SQLAlchemy model.

    ```Python
    # In app/forms.py, within class HVACDeviceForm(FlaskForm):
    # ... existing common and other specific fields ...
    # Chiller Specific Fields for manual add
    cooling_capacity_kw = FloatField('Cooling Capacity (kW, Chiller)', validators=[Optional(), NumberRange(min=0)])
    eer_chiller = FloatField('EER (Chiller)', validators=[Optional(), NumberRange(min=0)])
    refrigerant_type_chiller = StringField('Refrigerant Type (Chiller)', validators=[Optional()])
    # ... other chiller fields you want on the form ...
    ```

3. ````SearchForm````: The dynamic parts of ````SearchForm```` (the "Metric to Search" dropdown, "Fields to Display" multi-select, and "Group Results By" dropdown) should adapt automatically. Their choices are populated by JavaScript using the updated ````FIELD_DEFINITIONS```` (which are passed from the search route to the template). No direct changes to ````SearchForm```` class itself should be needed for these dynamic parts, assuming the ````FIELD_DEFINITIONS```` are comprehensive.

### Step 4: Update CSV Import Logic (````app/utils.py````)

In the ````process_csv```` function, add a new ````elif```` block to handle CSVs for the ````'chiller'```` device type.

1. Add ````elif target_device_type_str == 'chiller':````
2. Inside this block, define ````current_fields_map````. This dictionary maps your ````Chiller```` model attribute names to tuples of (````expected_csv_column_name_after_cleaning````, ````data_type````). 
    ```Python
    # In app/utils.py, within process_csv function's main loop:
    # ...
                elif target_device_type_str == 'chiller': # New block for Chiller
                    current_fields_map = {
                        # Model Attribute: (CSV Column Name (cleaned), DataType)
                        'cooling_capacity_kw': ('cooling_capacity_kw', 'float'), # Ensure your Chiller CSV has a column named 'cooling_capacity_kw' (or similar, after cleaning)
                        'eer_chiller': ('eer_chiller', 'float'),
                        'refrigerant_type_chiller': ('refrigerant_type_chiller', 'string'),
                        # ... map all other Chiller-specific attributes from your model
                        # to their expected (cleaned) CSV column names ...
                    }
    # ...
    ```

 Ensure the ````csv_column_name```` here matches how columns will be named in CSV files you intend to import for chillers, after the standard cleaning (lowercase, underscores, etc.) applied at the start of the ````process_csv```` function.

 ### Step 5: Database Migrations
 After modifying ````app/models.py```` (Step 1), you must create and apply a new database migration.
 * Ensure your Flask app environment is set up (e.g., ````export FLASK_APP=run.py````).
 * Run: 
    ```bash
    flask db migrate -m "Add Chiller device type and model"
    flask db upgrade
    ```

 This will create the new ````chillers```` table (or equivalent based on your ````__tablename__````) in your database.

 ### Step 6: Template Adjustments (Mainly JavaScript Logic)
 * ````add_device.html````: The JavaScript logic in ````add_device.html```` (which uses ````FIELD_DEFINITIONS```` passed from the route) should automatically show/hide the new Chiller-specific fields when "Chiller" is selected from the ````device_type```` dropdown. This relies on: 
    * The new fields being added to the Python class ````HVACDeviceForm```` (Step 3.2).
    * ````FIELD_DEFINITIONS```` correctly defining these fields with ````model_class_name````: 'Chiller'.
* ````search.html````: Similarly, the JavaScript here should update the "Metric to Search", "Fields to Display", and "Group Results By" dropdowns to include Chiller-specific options when "Chiller" is selected as the device type filter. This also relies on ````FIELD_DEFINITIONS```` being correctly updated and passed to the template.
* Use the "Upload CSV" feature in the application to import this data. Remember to select "Chiller" as the device type for the CSV during upload.

### Step 7: Prepare and Import Data (for the new device type)
* Prepare CSV files containing data for your new "Chiller" devices. The column names in your CSV must correspond to what the ````process_csv```` function (specifically the ````chiller_fields_map```` and common field handling) expects after name cleaning.
* Use the "Upload CSV" feature in the application to import this data. Remember to select "Chiller" as the device type for the CSV during upload.
