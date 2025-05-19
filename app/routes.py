import os
import pandas as pd
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app, Response
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_, extract, func, cast, String, Numeric, Date 
from .models import db, HVACDevice, AirConditioner, HeatPump, ResidentialVentilationUnit, MODEL_MAP, DEVICE_TYPES
from .forms import HVACDeviceForm, CSVUploadForm, SearchForm, SPECIAL_GROUPING_OPTIONS, FIELD_DEFINITIONS, DEVICE_TYPE_CHOICES, DEVICE_TYPE_MODEL_MAPPING, TCOCalculatorForm
from .utils import allowed_file, process_csv
import json
import csv
import io
from sqlalchemy.orm import aliased
from datetime import date 


main = Blueprint('main', __name__)


# Updated VALID_STANDARD_FIELDS
# These are fields primarily on the HVACDevice base model or common identifiers
VALID_STANDARD_FIELDS = {
    'id': HVACDevice.id, # Added ID
    'manufacturer': HVACDevice.manufacturer,
    'device_type': HVACDevice.device_type,
    'model_identifier': HVACDevice.model_identifier, # Corrected mapping
    'market_entry': HVACDevice.market_entry,
    'noise_level_dba': HVACDevice.noise_level_dba,
    'price_amount': HVACDevice.price_amount,
    'price_currency': HVACDevice.price_currency,
    'data_source': HVACDevice.data_source,
    # Note: Specific metrics like seer, scop, specificpowerinput are handled via dedicated search fields and joins,
    # but can be added here if you want them available in the generic 'Filter by Field' dropdown for display purposes,
    # though it might be less intuitive for filtering that way.
    # For display, they are handled by the forms.STANDARD_FIELDS list now.
}

# GROUPING_FIELDS and STANDARD_FIELDS from forms.py are used by the form,
# this VALID_STANDARD_FIELDS is for the backend query building for generic filters.

# Constants for device type strings from models.py or forms.py (ensure consistency)
# from .models import DEVICE_TYPES # Not strictly needed here if using strings directly
AIR_CONDITIONER_TYPE = 'air_conditioner'
HEAT_PUMP_TYPE = 'heat_pump' # Currently not used for specific metric search in this update
RESIDENTIAL_VENTILATION_UNIT_TYPE = 'residential_ventilation_unit'
MODEL_CLASSES = {
    'HVACDevice': HVACDevice,
    'AirConditioner': AirConditioner,
    'HeatPump': HeatPump,
    'ResidentialVentilationUnit': ResidentialVentilationUnit
}


def build_and_run_search_query(search_params, page=None, per_page=None):
    results_data = []
    selected_columns_tuples = []
    is_grouped = False
    pagination_obj = None
    base_query = db.session.query(HVACDevice) 

    current_app.logger.debug(f"Received search_params: {search_params}")

    try:
        def get_single_param(param_name):
            val = search_params.get(param_name) 
            if isinstance(val, list):
                return val[0] if len(val) > 0 and val[0] is not None and str(val[0]).strip() != '' else None
            elif isinstance(val, str):
                return val if val.strip() != '' else None
            elif val is not None: # Handles non-string, non-list types that are not None
                return val 
            return None

        # --- 1. Apply Basic Filters (on HVACDevice model) ---
        manufacturer_val = get_single_param('manufacturer')
        if manufacturer_val:
            base_query = base_query.filter(HVACDevice.manufacturer.ilike(f'%{manufacturer_val}%'))
        
        device_type_filter_key = get_single_param('device_type')
        current_app.logger.debug(f"Device type filter key (processed): '{device_type_filter_key}'")
        if device_type_filter_key:
            base_query = base_query.filter(HVACDevice.device_type == device_type_filter_key)

        id_or_model_val = get_single_param('id_or_model_identifier')
        if id_or_model_val:
            try:
                device_id = int(id_or_model_val)
                base_query = base_query.filter(HVACDevice.id == device_id)
            except ValueError:
                base_query = base_query.filter(HVACDevice.model_identifier.ilike(f'%{id_or_model_val}%'))

        # --- 2. Apply Generic Metric Filter ---
        metric_name_key = get_single_param('search_metric_name') 
        metric_operator = get_single_param('search_metric_operator')
        metric_value_str = get_single_param('search_metric_value')

        current_app.logger.debug(f"Metric filter attempt: Name='{metric_name_key}', Op='{metric_operator}', Val='{metric_value_str}'")

        if metric_name_key and metric_operator and metric_value_str is not None: 
            metric_def = FIELD_DEFINITIONS.get(metric_name_key)
            if metric_def and metric_def.get('searchable'):
                model_class_name_for_metric = metric_def['model_class_name']
                model_attr_name = metric_def['model_attr']
                attr_type = metric_def.get('type', 'string')
                
                TargetModelClassForMetric = MODEL_CLASSES.get(model_class_name_for_metric)

                if not TargetModelClassForMetric:
                    flash(f"Config error (metric): Model class '{model_class_name_for_metric}' not found for '{metric_def['label']}'.", "danger")
                elif not hasattr(TargetModelClassForMetric, model_attr_name):
                    flash(f"Config error (metric): Attribute '{model_attr_name}' not found on '{model_class_name_for_metric}' for '{metric_def['label']}'.", "danger")
                else:
                    column_to_filter = getattr(TargetModelClassForMetric, model_attr_name)
                    
                    # Explicitly join if filtering on a subclass attribute
                    if TargetModelClassForMetric != HVACDevice:
                        current_app.logger.debug(f"Metric filter: Explicitly joining to {TargetModelClassForMetric.__name__} for attribute {model_attr_name}")
                        base_query = base_query.join(TargetModelClassForMetric)
                        # This join works because of the polymorphic setup; SQLAlchemy knows how HVACDevice relates to its subclasses.
                                        
                    processed_value = None
                    if metric_value_str.strip() == '':
                        flash(f"Metric value for '{metric_def['label']}' cannot be empty.", "warning")
                    else:
                        try:
                            if attr_type == 'float': processed_value = float(metric_value_str)
                            elif attr_type == 'integer': processed_value = int(metric_value_str)
                            elif attr_type == 'date': processed_value = date.fromisoformat(metric_value_str)
                            else: processed_value = metric_value_str
                        except ValueError:
                            flash(f"Invalid value '{metric_value_str}' for metric '{metric_def['label']}'. Expected {attr_type}.", "warning")
                    
                    if processed_value is not None:
                        current_app.logger.debug(f"Applying metric filter: {model_class_name_for_metric}.{model_attr_name} {metric_operator} {processed_value}")
                        if metric_operator == '>=': base_query = base_query.filter(column_to_filter >= processed_value)
                        elif metric_operator == '<=': base_query = base_query.filter(column_to_filter <= processed_value)
                        elif metric_operator == '==': base_query = base_query.filter(column_to_filter == processed_value)
                        elif metric_operator == 'like' and attr_type == 'string': base_query = base_query.filter(column_to_filter.ilike(f'%{processed_value}%'))
                        else: flash(f"Unsupported operator '{metric_operator}' for metric type '{attr_type}'.", "warning")
            elif metric_name_key:
                flash(f"Metric '{metric_name_key}' not found or not searchable.", "warning")
        
        # --- 3. Advanced Generic Filter (if kept) ---
        adv_filter_field_key = get_single_param('filter_field')
        adv_filter_value = get_single_param('filter_value')
        # Removed adv_custom_filter_key as custom_fields were removed from models
        # If you re-add custom_fields, this part needs to be reinstated carefully.

        if adv_filter_field_key and adv_filter_value is not None:
            # if adv_filter_field_key == 'custom' and adv_custom_filter_key: # Logic for custom JSON fields removed
            #    base_query = base_query.filter(HVACDevice.custom_fields[adv_custom_filter_key].astext().ilike(f'%{str(adv_filter_value)}%'))
            # else:
            adv_filter_def = FIELD_DEFINITIONS.get(adv_filter_field_key)
            if adv_filter_def:
                adv_model_class_name = adv_filter_def['model_class_name']
                adv_model_attr_name = adv_filter_def['model_attr']
                adv_attr_type = adv_filter_def.get('type', 'string')
                AdvTargetModelClass = MODEL_CLASSES.get(adv_model_class_name)

                if AdvTargetModelClass and hasattr(AdvTargetModelClass, adv_model_attr_name):
                    adv_column_to_filter = getattr(AdvTargetModelClass, adv_model_attr_name)
                    
                    if AdvTargetModelClass != HVACDevice:
                        current_app.logger.debug(f"Advanced filter: Explicitly joining to {AdvTargetModelClass.__name__}")
                        base_query = base_query.join(AdvTargetModelClass)
                        
                    adv_processed_value = None
                    try:
                        if adv_attr_type == 'float': adv_processed_value = float(adv_filter_value)
                        elif adv_attr_type == 'integer': adv_processed_value = int(adv_filter_value)
                        elif adv_attr_type == 'date': adv_processed_value = date.fromisoformat(adv_filter_value)
                        else: adv_processed_value = str(adv_filter_value)
                    except ValueError:
                        flash(f"Invalid value for advanced filter on '{adv_filter_def['label']}'.", "warning")

                    if adv_processed_value is not None:
                        if isinstance(adv_column_to_filter.type, String):
                            base_query = base_query.filter(adv_column_to_filter.ilike(f'%{adv_processed_value}%'))
                        else: 
                            base_query = base_query.filter(adv_column_to_filter == adv_processed_value)
                else:
                    flash(f"Advanced filter field '{adv_filter_field_key}' misconfigured or attribute not found.", "warning")
            # Removed 'else' for 'custom' key, as custom_fields are gone.
            # else:
            #    flash(f"Advanced filter field '{adv_filter_field_key}' not defined.", "warning")


        current_app.logger.debug(f"Query after all filters, before grouping/ordering: {str(base_query.statement.compile(compile_kwargs={'literal_binds': True}))}")

        # --- 4. Grouping ---
        group_by_field_key = get_single_param('group_by_field')
        query_before_grouping = base_query # Save state before potentially changing query for grouping

        if group_by_field_key:
            group_def = FIELD_DEFINITIONS.get(group_by_field_key) or \
                        SPECIAL_GROUPING_OPTIONS.get(group_by_field_key)
            
            if group_def and group_def.get('groupable', True):
                is_grouped = True 
                header_name = group_def['label']
                grouping_expression_col = None
                
                # query_for_grouping starts from the already filtered base_query
                query_for_grouping = base_query 

                if group_by_field_key == 'market_entry_year':
                    grouping_expression_col = extract('year', HVACDevice.market_entry).label('grouping_key')
                else:
                    group_model_class_name = group_def.get('model_class_name')
                    group_model_attr = group_def['model_attr']
                    GroupModelClass = MODEL_CLASSES.get(group_model_class_name) if group_model_class_name else HVACDevice

                    if GroupModelClass and hasattr(GroupModelClass, group_model_attr):
                        if GroupModelClass != HVACDevice:
                            current_app.logger.debug(f"Grouping: Explicitly joining to {GroupModelClass.__name__} for attribute {group_model_attr}")
                            # Apply join to the query that will be used for grouping
                            query_for_grouping = query_for_grouping.join(GroupModelClass)
                        grouping_expression_col = getattr(GroupModelClass, group_model_attr).label('grouping_key')
                    else:
                        flash(f"Cannot group by '{header_name}', attribute or model definition error.", "warning")
                        is_grouped = False
                
                if is_grouped and grouping_expression_col is not None:
                    # Apply grouping to the (potentially joined) query_for_grouping
                    base_query = query_for_grouping.with_entities(
                                       grouping_expression_col, 
                                       func.count(HVACDevice.id).label('count')
                                   ).group_by(grouping_expression_col) 
                    selected_columns_tuples = [('grouping_key', header_name), ('count', 'Count')]
                else: 
                    is_grouped = False
                    base_query = query_before_grouping # Revert if grouping failed
            else:
                flash(f"Grouping field '{group_by_field_key}' not found or not groupable.", "warning")
                is_grouped = False
                base_query = query_before_grouping # Revert if grouping field invalid
        
        # --- 5. Execute Query / Paginate ---
        if not is_grouped:
            order_by_expr = HVACDevice.id.desc()
            base_query = base_query.order_by(order_by_expr) 
            current_app.logger.debug(f"Final Ungrouped Query for pagination/all: {str(base_query.statement.compile(compile_kwargs={'literal_binds': True}))}")
            if page and per_page:
                pagination_obj = base_query.paginate(page=page, per_page=per_page, error_out=False)
                results_raw = pagination_obj.items
            else: 
                results_raw = base_query.all()
        elif is_grouped: 
            base_query = base_query.order_by('grouping_key') 
            current_app.logger.debug(f"Final Grouped Query: {str(base_query.statement.compile(compile_kwargs={'literal_binds': True}))}")
            results_raw = base_query.all()

        # --- 6. Process Results for Display ---
        if is_grouped:
            results_data = [row._asdict() for row in results_raw]
        else: 
            raw_device_dicts = [device.to_dict() for device in results_raw] 
            temp_selected_columns = []
            
            fields_to_display_keys_val = search_params.get('fields_to_display', [])
            if not isinstance(fields_to_display_keys_val, list):
                fields_to_display_keys = [str(fields_to_display_keys_val)] if fields_to_display_keys_val else []
            else:
                fields_to_display_keys = [str(k) for k in fields_to_display_keys_val if k is not None and str(k).strip()]
            current_app.logger.debug(f"Processed 'fields_to_display_keys' for column selection: {fields_to_display_keys}")

            if fields_to_display_keys: 
                current_keys_for_processing = list(fields_to_display_keys) 
                id_def = FIELD_DEFINITIONS.get('id')
                if id_def and 'id' not in current_keys_for_processing and id_def.get('displayable'):
                    current_keys_for_processing.insert(0, 'id')
                
                for def_name in current_keys_for_processing:
                    field_def = FIELD_DEFINITIONS.get(def_name)
                    if field_def and field_def.get('displayable'):
                        temp_selected_columns.append((def_name, field_def['label']))
                    elif not field_def and def_name: 
                        current_app.logger.warning(f"Display field '{def_name}' not in FIELD_DEFINITIONS, using default label.")
                        temp_selected_columns.append((def_name, def_name.replace('_',' ').title()))
            elif raw_device_dicts: 
                for def_name, f_def in FIELD_DEFINITIONS.items():
                    if f_def['model_class_name'] == 'HVACDevice' and f_def.get('displayable'):
                        temp_selected_columns.append((def_name, f_def['label']))
                if device_type_filter_key:
                    device_model_class_name = DEVICE_TYPE_MODEL_MAPPING.get(device_type_filter_key)
                    if device_model_class_name:
                        for def_name, f_def in FIELD_DEFINITIONS.items():
                            if f_def['model_class_name'] == device_model_class_name and f_def.get('displayable'):
                                if not any(sc[0] == def_name for sc in temp_selected_columns):
                                    temp_selected_columns.append((def_name, f_def['label']))
            selected_columns_tuples = temp_selected_columns
            
            results_data = []
            for device_dict_original in raw_device_dicts:
                new_display_dict = {}
                for def_name, _ in selected_columns_tuples: 
                    field_def_for_display = FIELD_DEFINITIONS.get(def_name)
                    if field_def_for_display:
                        model_attr_for_value = field_def_for_display['model_attr']
                        new_display_dict[def_name] = device_dict_original.get(model_attr_for_value)
                    else: 
                        new_display_dict[def_name] = device_dict_original.get(def_name)
                results_data.append(new_display_dict)

        current_app.logger.debug(f"Final selected_columns_tuples for template: {selected_columns_tuples}")
        if results_data:
            current_app.logger.debug(f"First processed result for template: {results_data[0]}")

        return results_data, selected_columns_tuples, is_grouped, pagination_obj

    except Exception as e:
        current_app.logger.error(f"Build and Run Query Exception: {e}", exc_info=True)
        flash(f"An unexpected error occurred while processing your search: {e}", "danger")
        return [], [], False, None

    

@main.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@main.route('/add_device', methods=['GET', 'POST'])
def add_device():
    form = HVACDeviceForm() # This form contains ALL possible fields
    if form.validate_on_submit():
        selected_type_key = form.device_type.data # e.g., 'air_conditioner'
        ModelClass = MODEL_MAP.get(selected_type_key) 

        if not ModelClass:
            flash(f"Invalid device type selected: {selected_type_key}", "danger")
            # Return with form and definitions for re-rendering
            return render_template('add_device.html', 
                                   title="Add HVAC Device", 
                                   form=form,
                                   field_definitions_json=json.dumps(FIELD_DEFINITIONS),
                                   device_type_model_mapping_json=json.dumps(DEVICE_TYPE_MODEL_MAPPING),
                                   device_types_json=json.dumps(DEVICE_TYPES))

        # Prepare data for the selected model class
        data_for_model = {'device_type': selected_type_key}
        
        # Iterate through form fields and assign data if it's relevant for the selected ModelClass
        for field_name, field_obj in form._fields.items():
            if field_name in ['csrf_token', 'submit', 'device_type']:
                continue

            # Check if this form field (field_name) corresponds to an attribute in FIELD_DEFINITIONS
            # and if that attribute belongs to the selected ModelClass or is common (HVACDevice)
            field_def_key = None # The key in FIELD_DEFINITIONS that matches this form field
            
            # Try to find the definition for the form field.
            # Form field names should ideally match the 'name' in FIELD_DEFINITIONS or be derivable.
            # For simplicity, let's assume form field names directly match model attributes
            # or the 'name' in FIELD_DEFINITIONS if they are prefixed (e.g. 'ac_seer').
            # The HVACDeviceForm currently uses model attribute names directly.
            
            definition_to_check = None
            # Find the definition whose 'model_attr' matches the form field_name
            for def_key, f_def in FIELD_DEFINITIONS.items():
                if f_def['model_attr'] == field_name:
                    definition_to_check = f_def
                    field_def_key = def_key # Use the definition's unique name
                    break
            
            if definition_to_check:
                field_model_class_name = definition_to_check['model_class_name']
                selected_model_class_name = DEVICE_TYPE_MODEL_MAPPING.get(selected_type_key)

                if field_model_class_name == 'HVACDevice' or field_model_class_name == selected_model_class_name:
                    # This field is relevant, get its data
                    if field_obj.data is not None:
                         # Handle empty strings for optional fields that are not numbers/dates
                        if isinstance(field_obj.data, str) and field_obj.data.strip() == "" and definition_to_check.get('type') not in ['float', 'integer', 'date']:
                            data_for_model[field_name] = None # Or skip if None is not desired
                        elif isinstance(field_obj.data, str) and field_obj.data.strip() == "" and definition_to_check.get('type') in ['float', 'integer']:
                            data_for_model[field_name] = None # Treat empty string as None for numeric
                        else:
                            data_for_model[field_name] = field_obj.data
            # else:
            #    current_app.logger.warning(f"Field {field_name} from form not found in FIELD_DEFINITIONS or not relevant for {selected_type_key}")


        # Note: custom_fields was removed from the model in previous steps.
        # If you had a general custom_fields TextArea in HVACDeviceForm, it would be handled here.
        # current_app.logger.debug(f"Data for model {ModelClass.__name__}: {data_for_model}")

        try:
            device = ModelClass(**data_for_model)
            db.session.add(device)
            db.session.commit()
            flash(f'{DEVICE_TYPES.get(selected_type_key, selected_type_key)} added successfully!', 'success')
            return redirect(url_for('main.search')) # Or to a success page, or add another
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding device: {e}", "danger")
            current_app.logger.error(f"Add device error: {e}", exc_info=True)
            # Fall through to render template with form and definitions

    # For GET request or POST with errors
    return render_template('add_device.html', 
                           title="Add HVAC Device", 
                           form=form,
                           field_definitions_json=json.dumps(FIELD_DEFINITIONS),
                           device_type_model_mapping_json=json.dumps(DEVICE_TYPE_MODEL_MAPPING),
                           device_types_json=json.dumps(DEVICE_TYPES) # Pass display names for device types
                           )

@main.route('/upload_csv', methods=['GET', 'POST'])
def upload_csv():
    form = CSVUploadForm()
    if form.validate_on_submit():
        file = form.file.data
        selected_type = form.device_type.data 

        if selected_type not in MODEL_MAP:
             flash(f"Invalid device type selected for CSV: {selected_type}", "danger")
             return render_template('upload_csv.html', form=form)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            try:
                file.save(file_path)
                success, message = process_csv(file_path, selected_type)
                if success: flash(message, 'success')
                else: flash(message, 'danger')
            except Exception as e:
                 flash(f"Error processing file: {e}", "danger")
                 current_app.logger.error(f"File processing error: {e}", exc_info=True)
            finally:
                 if os.path.exists(file_path):
                     os.remove(file_path)
            return redirect(url_for('main.devices'))
    return render_template('upload_csv.html', form=form)


PER_PAGE = 25 

@main.route('/search', methods=['GET', 'POST'])
def search():
    form = SearchForm() 
    page = request.args.get('page', 1, type=int)
    
    results_data, selected_columns, is_grouped, pagination = [], [], False, None
    query_executed = False
    
    persistent_search_args = {}
    for key in request.args:
        if key != 'page':
            values = request.args.getlist(key)
            persistent_search_args[key] = values if len(values) > 1 else values[0] if values else ''
    current_app.logger.debug(f"Persistent search args for URL generation: {persistent_search_args}")

    if request.method == 'POST':
        form = SearchForm(request.form)
        if form.validate():
            query_params_for_redirect = {}
            for field_name, field_obj in form._fields.items():
                if field_name not in ['csrf_token', 'submit']:
                    data = field_obj.data
                    if field_obj.type == 'SelectMultipleField':
                        if data: 
                            query_params_for_redirect[field_name] = data
                    elif data is not None and (not isinstance(data, str) or data.strip() != ""):
                        if isinstance(data, date):
                            query_params_for_redirect[field_name] = data.isoformat()
                        else:
                            query_params_for_redirect[field_name] = data
            query_params_for_redirect['page'] = 1 
            return redirect(url_for('main.search', **query_params_for_redirect))
        else: 
            flash("Please correct the errors in the form.", "warning")
            # Pass field definitions even on POST validation error for form re-rendering
            return render_template('search.html', form=form, results=[], query_executed=False,
                                   selected_columns=[], is_grouped=False, pagination=None,
                                   export_url="#", persistent_search_args={},
                                   field_definitions_json=json.dumps(FIELD_DEFINITIONS),
                                   device_type_model_mapping_json=json.dumps(DEVICE_TYPE_MODEL_MAPPING),
                                   device_types_json=json.dumps(DEVICE_TYPES)
                                   )

    if request.method == 'GET':
        form.process(request.args) 
        
        actionable_args = {k: v for k, v in request.args.items() if k != 'page'}
        if actionable_args:
            query_executed = True
            search_active_params = request.args.to_dict(flat=False) 
            current_app.logger.debug(f"GET request: search_active_params for query: {search_active_params}")
            #flash(search_active_params)
            results_data, selected_columns, is_grouped, pagination = build_and_run_search_query(
                search_active_params,
                page=page if not is_grouped else None,
                per_page=PER_PAGE if not is_grouped else None
            )
            if not results_data and query_executed:
                flash("No devices found matching your criteria.", "info")

    export_url = "#"
    if query_executed and (results_data or (pagination and pagination.total > 0)):
        try:
            from urllib.parse import urlencode
            query_string = urlencode(persistent_search_args, doseq=True) 
            export_url = f"{url_for('main.export_csv')}?{query_string}"
        except Exception as url_e:
            current_app.logger.error(f"Error building export URL: {url_e}", exc_info=True)

    return render_template('search.html',
                           form=form,
                           results=results_data,
                           query_executed=query_executed,
                           selected_columns=selected_columns,
                           is_grouped=is_grouped,
                           pagination=pagination,
                           export_url=export_url,
                           persistent_search_args=persistent_search_args,
                           # Pass definitions as JSON strings for JavaScript
                           field_definitions_json=json.dumps(FIELD_DEFINITIONS),
                           device_type_model_mapping_json=json.dumps(DEVICE_TYPE_MODEL_MAPPING),
                           device_types_json=json.dumps(DEVICE_TYPES) # DEVICE_TYPES from models.py
                           )

@main.route('/export_csv')
def export_csv():
    # request.args will contain the persistent search args from the export link
    search_params_for_export = request.args.to_dict(flat=False) 
    
    current_fields_to_display = search_params_for_export.get('fields_to_display', [])
    if not isinstance(current_fields_to_display, list):
        search_params_for_export['fields_to_display'] = [str(current_fields_to_display)] if current_fields_to_display else []
    else:
        search_params_for_export['fields_to_display'] = [str(f) for f in current_fields_to_display if f is not None]

    # Fetch ALL results for CSV
    results_for_csv, selected_columns_tuples, _, _ = build_and_run_search_query(
        search_params_for_export, page=None, per_page=None # No pagination for export
    )

    if not results_for_csv:
        flash("No data found for export with the given criteria.", "info")
        return redirect(url_for('main.search', **search_params_for_export)) # Redirect with original search params

    # ... (CSV generation logic from previous version using results_for_csv and selected_columns_tuples)
    si = io.StringIO()
    if not selected_columns_tuples and results_for_csv: 
        selected_columns_tuples = [(k, k.replace('_',' ').title()) for k in results_for_csv[0].keys()]
    
    if not selected_columns_tuples: # Still no columns (e.g. results_for_csv was empty after all)
        flash("No columns to export.", "warning")
        return redirect(url_for('main.search', **search_params_for_export))

    header_keys = [key for key, header in selected_columns_tuples]
    header_names = [header for key, header in selected_columns_tuples]

    try:
        writer = csv.DictWriter(si, fieldnames=header_keys, extrasaction='ignore', quoting=csv.QUOTE_ALL)
        writer.writerow(dict(zip(header_keys, header_names))) 
        writer.writerows(results_for_csv) 
    except Exception as csv_e:
         current_app.logger.error(f"Error writing CSV: {csv_e}", exc_info=True)
         flash("Error generating CSV file.", "danger")
         return redirect(url_for('main.search', **search_params_for_export))

    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=hvac_export.csv"}
    )



# API Routes
@main.route('/api/devices')
def api_devices():
    devices = HVACDevice.query.all()
    return jsonify([device.to_dict() for device in devices])


@main.route('/api/device/<int:device_id>')
def api_device(device_id):
    """API endpoint to get a specific device"""
    device = db.session.get(HVACDevice, device_id) # Use db.session.get for primary key lookup
    if device is None:
        return jsonify({"error": "Device not found"}), 404
    return jsonify(device.to_dict())

@main.route('/api/efficiency/stats') # Minor change: Ensure date handling is robust
def api_efficiency_stats():
    """API endpoint to get efficiency statistics over time"""
    # This query might become slow with many devices. Consider optimizations if needed.
    
    # Select distinct years from market_entry
    # This example aggregates in Python, which is not ideal for large datasets.
    # A database-level aggregation would be much more efficient.
    
    # For simplicity, keeping Python aggregation but acknowledging its limits.
    # It would be better to group by year in SQL and calculate averages there.

    stats_data = {}

    # Example: Aggregate SEER for Air Conditioners by market entry year
    # This is a simplified example. A real implementation would need to be more robust
    # and potentially use SQL aggregation.

    # Query to get relevant data (example for SEER)
    # This still fetches all devices, then processes in Python.
    devices = db.session.query(
        HVACDevice.market_entry, 
        AirConditioner.seer # Querying a subclass field
    ).join(AirConditioner, HVACDevice.id == AirConditioner.id)\
     .filter(HVACDevice.market_entry.isnot(None))\
     .filter(AirConditioner.seer.isnot(None))\
     .all()

    for market_entry_date, seer_value in devices:
        if market_entry_date and seer_value is not None:
            year = market_entry_date.year
            if year not in stats_data:
                stats_data[year] = {'seer_sum': 0, 'count': 0}
            stats_data[year]['seer_sum'] += seer_value
            stats_data[year]['count'] += 1
    
    result = []
    for year, data in sorted(stats_data.items()):
        if data['count'] > 0:
            result.append({
                'year': year,
                'avg_seer': data['seer_sum'] / data['count'],
                'device_count': data['count'] # Count of devices contributing to this avg_seer
            })
    
    # This is a very basic example for one metric (SEER). 
    # Expanding this for multiple metrics (EER, SCOP, SEPR etc.) across different device types
    # would require more complex queries or processing logic.

    return jsonify(result)

@main.route('/tco_calculator', methods=['GET', 'POST'])
def tco_calculator():
    form = TCOCalculatorForm()
    available_heat_pumps = HeatPump.query.with_entities(
        HeatPump.id, HeatPump.manufacturer, HeatPump.model_identifier,
        HeatPump.scop_avg_lwt35, # Ensure this attribute exists on your unified HeatPump model
        HeatPump.price_amount
    ).order_by(HeatPump.manufacturer, HeatPump.model_identifier).all()
    
    form.db_hp_id.choices = [('', '-- Select from Database --')] + \
                            [(hp.id, f"{hp.manufacturer} - {hp.model_identifier} (SCOP LWT35: {hp.scop_avg_lwt35 if hp.scop_avg_lwt35 else 'N/A'})") 
                             for hp in available_heat_pumps]
    tco_result = None

    if form.validate_on_submit():
        try:
            # General assumptions
            H = form.annual_heat_demand.data
            F = form.electricity_price.data
            M = form.annual_maintenance_cost.data
            T_lifetime = form.system_lifetime.data # Renamed to avoid conflict with TCO
            i_rate = form.discount_rate.data
            s_subsidy = form.capital_cost_subsidy.data if form.capital_cost_subsidy.data is not None else 0.0

            hp_capital_cost = 0
            hp_scop = 0
            selected_hp_info = "N/A"
            if form.hp_data_source.data == 'custom':
                hp_capital_cost = form.custom_hp_price.data
                hp_scop = form.custom_hp_scop.data
                selected_hp_info = "Custom Heat Pump"
            elif form.hp_data_source.data == 'database':
                hp_id = form.db_hp_id.data # Already coerced to int or None
                if hp_id is None: # Should have been caught by form.validate()
                    flash("Invalid Heat Pump selection from database.", "danger")
                    raise ValueError("Database HP ID is None after validation.")

                selected_hp = db.session.get(HeatPump, hp_id)
                if not selected_hp:
                    flash(f"Heat Pump with ID {hp_id} not found.", "danger")
                    raise ValueError(f"HP ID {hp_id} not found.")

                selected_hp_info = f"{selected_hp.manufacturer} - {selected_hp.model_identifier}"
                
                if form.db_hp_price_override.data is not None:
                    hp_capital_cost = form.db_hp_price_override.data
                elif selected_hp.price_amount is not None:
                    hp_capital_cost = selected_hp.price_amount
                else:
                    flash(f"Capital cost for '{selected_hp_info}' must be provided or exist in DB.", "danger")
                    raise ValueError("Missing capital cost for DB HP.")
                
                # Use a representative SCOP field from your unified HeatPump model
                # Ensure 'scop_avg_lwt35' or your chosen field exists on the HeatPump model
                if hasattr(selected_hp, 'scop_avg_lwt35') and selected_hp.scop_avg_lwt35:
                    hp_scop = selected_hp.scop_avg_lwt35
                else:
                    flash(f"Representative SCOP (e.g., scop_avg_lwt35) missing for '{selected_hp_info}'.", "danger")
                    raise ValueError("Missing SCOP for DB HP.")
            
            if not (hp_capital_cost > 0): raise ValueError("Heat pump capital cost must be positive.")
            if not (hp_scop > 0): raise ValueError("Heat pump SCOP must be positive.")

            # --- TCO Calculation ---
            # 1. Net Investment Cost (C_inv)
            C_inv = hp_capital_cost * (1 - s_subsidy)

            # 2. Annual Energy Consumption (E_a)
            E_a = H / hp_scop  # kWh_electric / year

            # 3. Annual Energy Cost (E_c)
            E_c = E_a * F  # € / year

            # 4. Total Annual Operational Expenditure (A_opex)
            A_opex = E_c + M # € / year

            # 5. NPV of Operational Expenditures (NPV_opex)
            NPV_opex = 0
            if i_rate > 0: # Standard annuity formula
                NPV_opex = A_opex * ( (1 - (1 + i_rate)**(-T_lifetime) ) / i_rate )
            elif i_rate == 0: # No discounting
                NPV_opex = A_opex * T_lifetime
            else: # Negative discount rate - unusual, handle as error or specific logic
                flash("Negative discount rate is not typical for this TCO calculation.", "warning")
                # Decide how to handle: for now, treat as i_rate = 0 or raise error
                NPV_opex = A_opex * T_lifetime # Defaulting to no discount

            # 6. Total Cost of Ownership (TCO)
            TCO = C_inv + NPV_opex
            print(TCO)

            tco_result = {
                "selected_hp_info": selected_hp_info,
                "inputs": {
                    "Annual Heat Demand (kWh)": H,
                    "Electricity Price (€/kWh)": F,
                    "Annual Maintenance (€)": M,
                    "System Lifetime (Years)": T_lifetime,
                    "Discount Rate": f"{i_rate*100:.2f}%",
                    "Capital Cost Subsidy": f"{s_subsidy*100:.2f}%",
                    "Heat Pump Capital Cost (for calc) (€)": hp_capital_cost,
                    "Heat Pump SCOP (for calc)": round(hp_scop, 2),
                },
                "intermediate_calculations": {
                    "Net Investment Cost (€)": round(C_inv, 2),
                    "Annual Energy Consumption (kWh)": round(E_a, 2),
                    "Annual Energy Cost (€)": round(E_c, 2),
                    "Total Annual Operational Cost (€)": round(A_opex, 2),
                    "NPV of Operational Costs (€)": round(NPV_opex, 2),
                },
                "total_tco_value": round(TCO, 2)
            }
            flash(f"TCO calculated successfully for {selected_hp_info}.", "success")

        except ValueError as ve: # Catch specific errors for missing data
            flash(str(ve), "danger") # Display the specific error message
            tco_result = None # Ensure no partial result is shown
        except Exception as e:
            flash(f"An error occurred during TCO calculation: {e}", "danger")
            current_app.logger.error(f"TCO Calculation error: {e}", exc_info=True)
            tco_result = None
            
    return render_template('tco_calculator.html', 
                           title="Total Cost of Ownership Calculator", 
                           form=form, 
                           tco_result=tco_result)