import os
import pandas as pd
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app, Response
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_, extract, func, cast, String, Numeric, Date
from .models import db, HVACDevice, AirConditioner, HeatPump, ResidentialVentilationUnit, MODEL_MAP
from .forms import HVACDeviceForm, CSVUploadForm, SearchForm, DEVICE_TYPE_CHOICES
from .utils import allowed_file, process_csv
import json 
import csv
import io


main = Blueprint('main', __name__)


VALID_STANDARD_FIELDS = {
    'manufacturer': HVACDevice.manufacturer,
    'device_type': HVACDevice.device_type,
    'market_entry': HVACDevice.market_entry,
    'noise_level_dba': HVACDevice.noise_level_dba,
    'price_amount': HVACDevice.price_amount,
    'price_currency': HVACDevice.price_currency,
    'data_source': HVACDevice.data_source,
}

GROUPING_FIELDS = [
    ('', '-- Select Field --'), # Default empty choice
    ('manufacturer', 'Manufacturer'),
    ('device_type', 'Device Type'),
    ('market_entry', 'Market Entry'), # We'll extract year in backend
    ('price_currency', 'Price Currency'),
]

STANDARD_FIELDS = [
    ('manufacturer', 'Manufacturer'),
    ('device_type', 'Device Type'),
    ('market_entry', 'Market Entry Date'),
    ('power_rating_kw', 'Power Rating (kW)'),
    ('eer', 'EER'),
    ('seer', 'SEER'),
    ('sepr', 'SEPR'),
    ('noise_level_dba', 'Noise Level (dBA)'),
    ('price_amount', 'Price Amount'),
    ('price_currency', 'Price Currency'),
]


def build_and_run_search_query(search_params):
    """
    Builds and executes the search/analysis query based on parameters.

    Args:
        search_params (dict): Dictionary of search parameters,
                              typically from form.data or request.args.

    Returns:
        tuple: (results_list_of_dicts, selected_columns_list_of_tuples, is_grouped_bool)
               Returns ([], [], False) on error.
    """
    results = []
    selected_columns_tuples = [] # List of (key, header_name)
    is_grouped = False
    base_query = db.session.query(HVACDevice) # Start with query for full objects

    try:
        # --- 1. Apply Filters ---
        if search_params.get('manufacturer'):
            base_query = base_query.filter(HVACDevice.manufacturer.ilike(f'%{search_params["manufacturer"]}%'))
        if search_params.get('device_type'):
            base_query = base_query.filter(HVACDevice.device_type.ilike(f'%{search_params["device_type"]}%'))

        # Generic filter
        filter_field_name = search_params.get('filter_field')
        filter_value = search_params.get('filter_value')
        custom_filter_key = search_params.get('custom_filter_field')

        if filter_field_name and filter_value:
            if filter_field_name == 'custom' and custom_filter_key:
                base_query = base_query.filter(HVACDevice.custom_fields.op('->>')(custom_filter_key) == filter_value)
            elif filter_field_name in VALID_STANDARD_FIELDS:
                column = VALID_STANDARD_FIELDS[filter_field_name]
                if isinstance(column.type, String):
                     base_query = base_query.filter(column.ilike(f'%{filter_value}%'))
                else:
                     try: base_query = base_query.filter(column == filter_value)
                     except Exception as e: print(f"Ignoring filter error: {e}") # Log or flash?

        # --- 2. Apply Grouping ---
        group_by_col_name = search_params.get('group_by_field')
        grouping_expression = None
        query_select_list = [] # List of things to select in the query

        if group_by_col_name:
            is_grouped = True
            header_name = group_by_col_name # Default header
            if group_by_col_name == 'market_entry_year':
                grouping_expression = extract('year', HVACDevice.market_entry).label('grouping_key')
                header_name = 'Market Entry Year'
            elif group_by_col_name in VALID_STANDARD_FIELDS:
                grouping_expression = VALID_STANDARD_FIELDS[group_by_col_name].label('grouping_key')
                header_name = dict(GROUPING_FIELDS).get(group_by_col_name, group_by_col_name.replace('_',' ').title()) # Get display name

            if grouping_expression is not None:
                 query_select_list = [
                     grouping_expression,
                     func.count(HVACDevice.id).label('count')
                 ]
                 selected_columns_tuples = [('grouping_key', header_name), ('count', 'Count')]
                 base_query = db.session.query(*query_select_list).group_by(grouping_expression) # Apply group by
            else:
                 print(f"Invalid grouping field: {group_by_col_name}")
                 is_grouped = False # Grouping failed

        # --- 3. Select Columns (if not grouping) ---
        if not is_grouped:
             entities_to_select = []
             selected_columns_tuples = []
             fields_to_display = search_params.get('fields_to_display', [])
             # Ensure fields_to_display is iterable (might be None or single value from request.args)
             if isinstance(fields_to_display, str): fields_to_display = [fields_to_display]
             elif fields_to_display is None: fields_to_display = []


             for field_name in fields_to_display:
                 if field_name in VALID_STANDARD_FIELDS:
                     entities_to_select.append(VALID_STANDARD_FIELDS[field_name])
                     header = dict(STANDARD_FIELDS).get(field_name, field_name.replace('_',' ').title())
                     selected_columns_tuples.append((field_name, header))

             custom_key = search_params.get('custom_field_to_display')
             if custom_key:
                 try:
                     entities_to_select.append(HVACDevice.custom_fields.op('->>')(custom_key).label(custom_key))
                     selected_columns_tuples.append((custom_key, custom_key))
                 except Exception as e: print(f"Ignoring custom field selection error: {e}")

             if entities_to_select:
                 entities_to_select.insert(0, HVACDevice.id)
                 selected_columns_tuples.insert(0, ('id', 'ID'))
                 # IMPORTANT: If selecting specific entities, the base query needs to change *before* filtering
                 # This refactoring needs careful handling of when with_entities is applied.
                 # For simplicity here, we assume filters applied *before* this still work,
                 # OR we re-create the query. Let's re-create for clarity:
                 base_query = db.session.query(*entities_to_select)
                 # Re-apply Filters (needed because we changed the query object)
                 if search_params.get('manufacturer'): base_query = base_query.filter(HVACDevice.manufacturer.ilike(f'%{search_params["manufacturer"]}%'))
                 if search_params.get('device_type'): base_query = base_query.filter(HVACDevice.device_type.ilike(f'%{search_params["device_type"]}%'))
                 # Re-applying generic filter is complex here, might need aliases - omitted for now
             else:
                 # No specific columns selected, use default full object query
                 # selected_columns_tuples will be determined after fetching data
                 pass # Keep base_query as query(HVACDevice)


        # --- 4. Execute Query ---
        # Define order_by based on grouping status
        order_by_expr = None
        if is_grouped and grouping_expression is not None:
             order_by_expr = grouping_expression
        # Add ordering for non-grouped results if desired (e.g., by ID)
        elif not is_grouped:
             order_by_expr = HVACDevice.id # Default order

        if order_by_expr is not None:
             results_raw = base_query.order_by(order_by_expr).all()
        else:
             results_raw = base_query.all()


        # --- 5. Process Results ---
        if is_grouped: # Grouped results are KeyedTuples or similar
             results = [row._asdict() for row in results_raw]
        elif entities_to_select: # Selected specific columns (KeyedTuples)
             results = [row._asdict() for row in results_raw]
        else: # Full HVACDevice objects
             results_dict = [device.to_dict() for device in results_raw]
             if results_dict:
                 # Define selected_columns based on the dict keys
                 selected_columns_tuples = [(k, k.replace('_',' ').title()) for k in results_dict[0].keys()]
             results = results_dict

        return results, selected_columns_tuples, is_grouped

    except Exception as e:
        flash(f"Error building or executing query: {e}", "danger")
        print(f"Query Building/Execution Error: {e}") # Log the error
        return [], [], False # Return empty results on error


@main.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@main.route('/add_device', methods=['GET', 'POST'])
def add_device():
    form = HVACDeviceForm()
    if form.validate_on_submit():
        selected_type = form.device_type.data
        ModelClass = MODEL_MAP.get(selected_type) # Get the correct model class

        if not ModelClass:
            flash(f"Invalid device type selected: {selected_type}", "danger")
            return render_template('add_device.html', form=form)

        # Prepare data - common fields + specific fields based on type
        # This needs careful mapping from form fields to model fields
        common_data = {
            'manufacturer': form.manufacturer.data,
            'market_entry': form.market_entry.data,
            'noise_level_dba': form.noise_level_dba.data,
            'price_currency': form.price_currency.data,
            'price_amount': form.price_amount.data,
            'data_source': form.data_source.data,
            'device_type': selected_type, # Set the discriminator
        }
        # Add specific fields - needs checks based on 'selected_type'
        specific_data = {}
        print(selected_type)
        if selected_type == 'air_conditioner':
            specific_data['eer'] = form.eer.data
            specific_data['seer'] = form.seer.data
            specific_data['rated_power_cooling_kw'] = form.rated_power_cooling_kw.data
            specific_data['energy_class_cooling'] = form.energy_class_cooling.data
            specific_data['design_load_cooling_kw'] = form.design_load_cooling_kw.data
            specific_data['annual_consumption_cooling_kwh'] = form.annual_consumption_cooling_kwh.data
            specific_data['rated_power_heating_kw'] = form.rated_power_heating_kw.data
            specific_data['cop_standard'] = form.cop_standard.data
            specific_data['scop_average'] = form.scop_average.data
            specific_data['energy_class_heating_average'] = form.energy_class_heating_average.data
            specific_data['design_load_heating_average_kw'] = form.design_load_heating_average_kw.data
            specific_data['annual_consumption_heating_average_kwh'] = form.annual_consumption_heating_average_kwh.data
            specific_data['scop_warm'] = form.scop_warm.data
            specific_data['energy_class_heating_warm'] = form.energy_class_heating_warm.data
            specific_data['design_load_heating_warm_kw'] = form.design_load_heating_warm_kw.data
            specific_data['scop_cold'] = form.scop_cold.data
            specific_data['energy_class_heating_cold'] = form.energy_class_heating_cold.data
            specific_data['design_load_heating_cold_kw'] = form.design_load_heating_cold_kw.data
            specific_data['refrigerant_type'] = form.refrigerant_type.data
            specific_data['refrigerant_gwp'] = form.refrigerant_gwp.data
            specific_data['noise_level_outdoor_cooling_db'] = form.noise_level_outdoor_cooling_db.data
        elif selected_type == 'heat_pump':
             specific_data['sepr'] = form.sepr.data
        elif selected_type == 'residential_ventilation_unit':
             specific_data['heat_recovery_rate'] = form.heat_recovery_rate.data
             specific_data['fan_performance'] = form.fan_performance.data
        # ... add others

        # Handle custom_fields JSON
        custom_data = None
        if form.custom_fields.data:
            try: custom_data = json.loads(form.custom_fields.data)
            except json.JSONDecodeError: flash('Invalid JSON in Custom Fields.', 'warning')

        # Instantiate the correct subclass
        try:
            device = ModelClass(**common_data, **specific_data, custom_fields=custom_data)
            db.session.add(device)
            db.session.commit()
            flash(f'{ModelClass.__name__} added successfully!', 'success')
            # Redirect to a general devices view or type-specific view?
            return redirect(url_for('main.devices')) # devices view needs update too
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding device: {e}", "danger")
            print(f"Add device error: {e}")

    return render_template('add_device.html', form=form)


@main.route('/upload_csv', methods=['GET', 'POST'])
def upload_csv():
    form = CSVUploadForm()
    if form.validate_on_submit():
        file = form.file.data
        selected_type = form.device_type.data # Get type for the whole file

        if selected_type not in MODEL_MAP:
             flash(f"Invalid device type selected for CSV: {selected_type}", "danger")
             return render_template('upload_csv.html', form=form)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Consider adding user/session ID to filename if multiple users upload
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            try:
                file.save(file_path)
                # Process the CSV file, passing the selected device type string
                success, message = process_csv(file_path, selected_type)
                if success: flash(message, 'success')
                else: flash(message, 'danger')
            except Exception as e:
                 flash(f"Error processing file: {e}", "danger")
                 print(f"File processing error: {e}")
            finally:
                 # Ensure file is removed even if processing fails
                 if os.path.exists(file_path):
                     os.remove(file_path)

            # Redirect to devices view (needs update)
            return redirect(url_for('main.devices'))

    return render_template('upload_csv.html', form=form)


@main.route('/devices')
def devices():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    # Query the base class - SQLAlchemy fetches appropriate subclass data too
    pagination = HVACDevice.query.order_by(HVACDevice.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    devices = pagination.items # This list now contains instances of AC, HeatPump etc.
    # The template needs to handle potentially different fields via device.to_dict()
    return render_template('devices.html', devices=devices, pagination=pagination)


@main.route('/search', methods=['GET', 'POST'])
def search():
    """Search/Analyze HVAC devices using refactored query logic."""
    form = SearchForm()
    results = []
    query_executed = False
    selected_columns = []
    is_grouped = False
    export_params = {} # Store params for export link

    if form.validate_on_submit():
        query_executed = True
        search_params = form.data # Get data from the form
        # Remove CSRF token and submit button value from params
        search_params.pop('csrf_token', None)
        search_params.pop('submit', None)
        export_params = search_params # Use validated form data for export link

        results, selected_columns, is_grouped = build_and_run_search_query(search_params)

    elif request.method == 'GET' and request.args:
        # Handle GET request (e.g., bookmark, direct link with params)
        # Populate form from args for display (optional, but good UX)
        form.process(request.args)
        query_executed = True # Assume GET with args means user wants results
        search_params = request.args.to_dict(flat=False) # Use dict suitable for helper
        export_params = search_params # Use GET args for export link

        results, selected_columns, is_grouped = build_and_run_search_query(search_params)

    # Build export URL carefully, handling list values from multi-select
    export_url = "#" # Default
    if query_executed:
        try:
             # urlencode handles multiple values for the same key correctly
             export_url = url_for('main.export_csv', **export_params)
             # Manual encoding if url_for has issues with lists:
             # query_string = urlencode(export_params, doseq=True)
             # export_url = f"{url_for('main.export_csv')}?{query_string}"
        except Exception as url_e:
             print(f"Error building export URL: {url_e}")


    return render_template('search.html',
                           form=form,
                           results=results,
                           query_executed=query_executed,
                           selected_columns=selected_columns, # List of (key, header_name) tuples
                           is_grouped=is_grouped,
                           export_url=export_url) # Pass URL to template


@main.route('/export_csv')
def export_csv():
    """Exports search results as CSV using refactored query logic."""

    # Get search parameters from GET request arguments
    search_params = request.args.to_dict(flat=False) # Handles multi-value args like fields_to_display

    # Call the helper function
    results, selected_columns_tuples, is_grouped = build_and_run_search_query(search_params)

    if not results:
        return "No data found for export with the given criteria.", 404

    # --- Generate CSV ---
    si = io.StringIO()
    if not selected_columns_tuples: # Handle case where no columns were determined
         if results: # Infer from first result dict if possible
              selected_columns_tuples = [(k, k.replace('_',' ').title()) for k in results[0].keys()]
         else: # No data, no columns
              return "No data or columns found for export.", 404


    header_keys = [key for key, header in selected_columns_tuples]
    header_names = [header for key, header in selected_columns_tuples]

    try:
        writer = csv.DictWriter(si, fieldnames=header_keys, extrasaction='ignore')
        writer.writerow(dict(zip(header_keys, header_names))) # Write display headers
        writer.writerows(results) # Write the data rows (which are dicts)
    except Exception as csv_e:
         print(f"Error writing CSV: {csv_e}")
         return "Error generating CSV file.", 500

    # --- Create Response ---
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=hvac_export.csv"}
    )

@main.route('/api/devices')
def api_devices():
    """API endpoint to get devices JSON"""
    devices = HVACDevice.query.all()
    return jsonify([device.to_dict() for device in devices])

@main.route('/api/device/<int:device_id>')
def api_device(device_id):
    """API endpoint to get a specific device"""
    device = HVACDevice.query.get_or_404(device_id)
    return jsonify(device.to_dict())

@main.route('/api/efficiency/stats')
def api_efficiency_stats():
    """API endpoint to get efficiency statistics over time"""
    devices = HVACDevice.query.all()
    
    data = {}
    for device in devices:
        year = device.market_entry
        if year not in data:
            data[year] = {
                'count': 0,
                'eer_sum': 0,
                'seer_sum': 0,
                'sepr_sum': 0
            }
        
        data[year]['count'] += 1
        
        if device.eer:
            data[year]['eer_sum'] += device.eer
        
        if device.seer:
            data[year]['seer_sum'] += device.seer
        
        if device.sepr:
            data[year]['sepr_sum'] += device.sepr
    
    result = []
    for year, stats in data.items():
        count = stats['count']
        result.append({
            'year': year,
            'device_count': count,
            'avg_eer': stats['eer_sum'] / count if count > 0 and stats['eer_sum'] > 0 else None,
            'avg_seer': stats['seer_sum'] / count if count > 0 and stats['seer_sum'] > 0 else None,
            'avg_sepr': stats['sepr_sum'] / count if count > 0 and stats['sepr_sum'] > 0 else None
        })
    
    return jsonify(result)