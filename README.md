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


# Sharing and Replicating Project Data

To allow others to replicate your results or work with the same dataset used in this project, you can create a data dump from your PostgreSQL database. This dump can then be imported into another PostgreSQL instance.

## Creating a Data Dump using pgAdmin

pgAdmin is a popular GUI tool for managing PostgreSQL databases.

1.  **Connect to your PostgreSQL Server:** Open pgAdmin and connect to the server instance where your `hvac_db` (or similarly named) database resides.
2.  **Locate your Database:** In the pgAdmin browser tree, find your project's database (e.g., `hvac_db`).
3.  **Initiate Backup:**
    * Right-click on the database name.
    * Select "Backup..." from the context menu.
4.  **Configure Backup Options:**
    * **General Tab:**
        * **Filename:** Choose a location and name for your dump file (e.g., `hvac_database_dump.sql` or `hvac_database_dump.dump`). The extension can vary based on the format.
        * **Format:**
            * **Plain:** This creates a plain-text SQL script file. It's human-readable and generally good for moderately sized databases or when you want to inspect the SQL commands. It can be restored using `psql`.
            * **Custom:** This creates a custom-format archive file (often `.dump`). It's compressed by default, generally smaller, and more flexible for selective restore. It's restored using `pg_restore`. This is often preferred for larger datasets or more complex scenarios.
            * **Tar:** Creates a tar archive. Usually less common for single database dumps than Plain or Custom.
            * **Directory:** Creates a directory with multiple files. Good for very large databases and parallel backup/restore, but more complex to handle as a single distributable file.
        * **Recommendation:** For ease of sharing and general use, **Custom** or **Plain** are good choices. Custom is often better for larger data or if you might want to restore parts selectively later.
    * **Data/Objects Tab (or similar, depends on pgAdmin version):**
        * **Sections:** Ensure "Pre-data" (schema definitions like `CREATE TABLE`), "Data" (the actual row data using `INSERT` or `COPY`), and "Post-data" (indexes, constraints, triggers) are selected. This is typical for a full backup.
        * **Type of objects:**
            * Ensure "Schemas" (if you used a specific one, otherwise `public` is default) and "Tables" are selected.
            * You usually want to include "Sequences", "Indexes", "Foreign keys", etc.
        * **Do not save:**
            * Typically, you **do not save** "Owner" or "Privileges" if the dump is intended for import by a different user on a different system, as these can cause permission issues during restore. The restoring user will become the owner of the restored objects.
    * **Options Tab (or Dump Options / Query Options):**
        * **Use `INSERT` commands (for Plain format):** If using Plain format, you might see an option to use `INSERT` commands (can be slower but more portable) or `COPY` commands (faster but sometimes less portable across major PostgreSQL versions or systems if binary). pgAdmin usually handles this well.
        * **`CREATE DATABASE` command (for Plain format):** Usually, you **do not** include the `CREATE DATABASE` command in the dump itself. The person restoring will typically create an empty database first and then restore into it.
        * **Clean before restore (for Plain format):** Options like "Clean objects" or "Add `DROP TABLE` statements" can be useful if restoring into a database that might already have older versions of the tables. This ensures a fresh import.
        * **Verbose messages:** Can be helpful for pgAdmin's output log.
        * **`--no-owner` and `--no-privileges` (if available as checkboxes or equivalent for Custom format):** These are good to check for portability.
5.  **Start Backup:** Click the "Backup" button. pgAdmin will generate the dump file in the location you specified.

## Creating a Data Dump using `pg_dump` (Command Line)

`pg_dump` is a powerful command-line utility that comes with PostgreSQL.

* **Open your terminal or command prompt.**
* **Basic Plain Text Dump (SQL statements):**
    ```bash
    pg_dump -U your_db_user -h localhost -p 5432 --no-owner --no-privileges --clean --if-exists -Fp your_database_name > hvac_database_dump.sql
    ```
    * `-U your_db_user`: Replace with your PostgreSQL username.
    * `-h localhost`: Replace with your database host if not localhost.
    * `-p 5432`: Replace with your database port if not 5432.
    * `--no-owner`: Excludes ownership information.
    * `--no-privileges`: Excludes privilege information.
    * `--clean`: Adds `DROP` commands for objects before creating them (useful for restoring to an existing DB).
    * `--if-exists`: Adds `IF EXISTS` clauses to `DROP` commands.
    * `-Fp`: Specifies Plain text format.
    * `your_database_name`: The name of your database (e.g., `hvac_db`).
    * `> hvac_database_dump.sql`: Redirects output to a file.
    You will likely be prompted for the user's password.

* **Custom Format Dump (Compressed, Recommended for larger data):**
    ```bash
    pg_dump -U your_db_user -h localhost -p 5432 --no-owner --no-privileges -Fc your_database_name > hvac_database_dump.dump
    ```
    * `-Fc`: Specifies Custom format (compressed by default).
    * The output file is typically named with a `.dump` or `.backup` extension.

## Sharing the Data Dump

* Once the dump file (`.sql` or `.dump`) is created, you can compress it further (e.g., using zip or gzip) if it's large, and then share it (e.g., via cloud storage, email if small enough, or version control if appropriate and not too large).
* **Important:** Be mindful of any sensitive information in your database before sharing a dump publicly. For this project, it's likely just HVAC data, but it's always good practice to consider.

## Importing a Data Dump (Instructions for the Other Person)

The person receiving the dump file will need to:

1.  **Prerequisites:**
    * Have PostgreSQL installed and running.
    * Have access to a PostgreSQL user with privileges to create databases or restore into an existing one.

2.  **Create a New, Empty Database:**
    It's best practice to restore into a fresh, empty database.
    ```sql
    -- Using psql or pgAdmin:
    CREATE DATABASE new_hvac_db; 
    -- Or use the same name as your original DB if it doesn't exist on their system:
    -- CREATE DATABASE hvac_db;
    ```

3.  **Restore the Dump:**

    * **For Plain Text Dumps (`.sql` file):**
        Use `psql`.
        ```bash
        psql -U their_db_user -h localhost -d new_hvac_db -f /path/to/your/hvac_database_dump.sql
        ```
        * `-U their_db_user`: Their PostgreSQL username.
        * `-d new_hvac_db`: The name of the empty database they created.
        * `-f /path/to/your/hvac_database_dump.sql`: The path to the downloaded SQL dump file.
        They will likely be prompted for the password.

    * **For Custom Format Dumps (`.dump` file):**
        Use `pg_restore`.
        ```bash
        pg_restore -U their_db_user -h localhost -d new_hvac_db --no-owner --no-privileges -v /path/to/your/hvac_database_dump.dump
        ```
        * `-d new_hvac_db`: The target database.
        * `--no-owner` and `--no-privileges` can also be specified during restore to avoid issues if they were accidentally included in the dump.
        * `-v`: Verbose mode, shows progress.
        * `/path/to/your/hvac_database_dump.dump`: The path to the downloaded custom format dump file.
        They will likely be prompted for the password.

    * **Using pgAdmin to Restore:**
        pgAdmin also has a "Restore..." option when you right-click on a database. Users can select the dump file and configure restore options through the GUI, similar to the backup process.

4.  **Configure their Application:**
    After restoring the database, they will need to configure their instance of your Flask application (their `.env` file) to point to this newly populated database (`DATABASE_URL`).

5.  **Run Migrations (Usually Not Needed for Restore, but good check):**
    If the dump was schema-only or if they are setting up the project from scratch and the dump only contained data for an *existing* schema, they might need to run `flask db upgrade` first to create tables. However, a full dump (schema + data) usually recreates the tables. If they restore a dump into a database that already had tables created by `flask db upgrade` from your models, options like `--clean` during dump/restore are important. It's generally safest to restore into a completely empty database.

By providing these instructions along with your data dump, others should be able to set up an identical dataset and replicate your TCO calculations or other analyses. Remember to emphasize using the dump that includes both schema and data for a complete replication.