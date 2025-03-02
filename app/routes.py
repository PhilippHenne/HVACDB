import os
import pandas as pd
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_
from .models import db, HVACDevice
from .forms import HVACDeviceForm, CSVUploadForm, SearchForm
from .utils import allowed_file, process_csv

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@main.route('/add_device', methods=['GET', 'POST'])
def add_device():
    """Add a new HVAC device manually"""
    form = HVACDeviceForm()
    
    if form.validate_on_submit():
        device = HVACDevice(
            manufacturer=form.manufacturer.data,
            market_entry_year=form.market_entry_year.data,
            device_type=form.device_type.data,
            power_rating_kw=form.power_rating_kw.data,
            airflow_volume_m3h=form.airflow_volume_m3h.data,
            eer=form.eer.data,
            seer=form.seer.data,
            sepr=form.sepr.data,
            heat_recovery_rate=form.heat_recovery_rate.data,
            fan_performance=form.fan_performance.data,
            temperature_range=form.temperature_range.data,
            noise_level_dba=form.noise_level_dba.data,
            price_currency=form.price_currency.data,
            price_amount=form.price_amount.data,
            units_sold_year=form.units_sold_year.data,
            units_sold_count=form.units_sold_count.data,
            data_source=form.data_source.data
        )
        
        db.session.add(device)
        db.session.commit()
        
        flash('HVAC device added successfully!', 'success')
        return redirect(url_for('main.devices'))
    
    return render_template('add_device.html', form=form)

@main.route('/upload_csv', methods=['GET', 'POST'])
def upload_csv():
    """Upload and process a CSV file"""
    form = CSVUploadForm()
    
    if form.validate_on_submit():
        file = form.file.data
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Process the CSV file
            success, message = process_csv(file_path)
            
            # Remove the file after processing
            os.remove(file_path)
            
            if success:
                flash(message, 'success')
                return redirect(url_for('main.devices'))
            else:
                flash(message, 'danger')
                
    return render_template('upload_csv.html', form=form)

@main.route('/devices')
def devices():
    """View all HVAC devices"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get all devices with pagination
    pagination = HVACDevice.query.order_by(HVACDevice.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    devices = pagination.items
    
    return render_template('devices.html', devices=devices, pagination=pagination)

@main.route('/search', methods=['GET', 'POST'])
def search():
    """Search HVAC devices"""
    form = SearchForm()
    results = []
    
    if form.validate_on_submit() or request.method == 'GET' and request.args:
        # Get form data or query parameters
        if request.method == 'GET':
            manufacturer = request.args.get('manufacturer', '')
            device_type = request.args.get('device_type', '')
            min_efficiency = request.args.get('min_efficiency', type=float)
            min_year = request.args.get('min_year', type=int)
            max_year = request.args.get('max_year', type=int)
        else:
            manufacturer = form.manufacturer.data
            device_type = form.device_type.data
            min_efficiency = form.min_efficiency.data
            min_year = form.min_year.data
            max_year = form.max_year.data
        
        # Build the query
        query = HVACDevice.query
        
        if manufacturer:
            query = query.filter(HVACDevice.manufacturer.ilike(f'%{manufacturer}%'))
        
        if device_type:
            query = query.filter(HVACDevice.device_type.ilike(f'%{device_type}%'))
        
        if min_efficiency is not None:
            query = query.filter(HVACDevice.eer >= min_efficiency)
        
        if min_year is not None:
            query = query.filter(HVACDevice.market_entry_year >= min_year)
        
        if max_year is not None:
            query = query.filter(HVACDevice.market_entry_year <= max_year)
        
        results = query.all()
    
    return render_template('search.html', form=form, results=results)

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
        year = device.market_entry_year
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