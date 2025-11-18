from flask import Flask, render_template, jsonify, request
from utils import (
    load_csv_data, get_summary_stats, get_daily_stats,
    get_monthly_stats, get_project_stats, get_hourly_activity,
    get_event_timeline, filter_by_date_range, filter_by_project,
    get_day_of_week_stats, get_daily_project_breakdown,
    get_cumulative_time, get_working_hours_analysis
)
import pandas as pd
import os
import numpy as np
import json

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

def convert_to_serializable(obj):
    """Convert numpy/pandas types to native Python types for JSON serialization"""
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Timestamp):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    return obj

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/reports')
def reports():
    """Reports page"""
    return render_template('reports.html')

@app.route('/api/data')
def api_data():
    """API endpoint to get all dashboard data"""
    df = load_csv_data()
    
    if df.empty:
        return jsonify({
            'summary': {},
            'daily_stats': [],
            'hourly_activity': {},
            'recent_events': []
        })
    
    summary = get_summary_stats(df)
    daily = get_daily_stats(df)
    hourly = get_hourly_activity(df)
    recent = get_event_timeline(df, limit=50)
    day_of_week = get_day_of_week_stats(df)
    daily_projects = get_daily_project_breakdown(df)
    cumulative = get_cumulative_time(df)
    working_hours = get_working_hours_analysis(df)
    
    # Recent events timestamps are already converted in utils.py
    # Just ensure all values are JSON serializable
    for event in recent:
        for key, value in event.items():
            event[key] = convert_to_serializable(value)
    
    # Convert all data to JSON-serializable format
    summary = convert_to_serializable(summary)
    daily = convert_to_serializable(daily)
    hourly = convert_to_serializable(hourly)
    recent = convert_to_serializable(recent)
    day_of_week = convert_to_serializable(day_of_week)
    daily_projects = convert_to_serializable(daily_projects)
    cumulative = convert_to_serializable(cumulative)
    working_hours = convert_to_serializable(working_hours)
    
    return jsonify({
        'summary': summary,
        'daily_stats': daily,
        'hourly_activity': hourly,
        'recent_events': recent,
        'day_of_week_stats': day_of_week,
        'daily_project_breakdown': daily_projects,
        'cumulative_time': cumulative,
        'working_hours_analysis': working_hours
    })

@app.route('/api/reports/daily')
def api_reports_daily():
    """API endpoint for daily reports"""
    df = load_csv_data()
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date or end_date:
        df = filter_by_date_range(df, start_date, end_date)
    
    daily = get_daily_stats(df)
    
    # Convert to JSON-serializable format
    daily = convert_to_serializable(daily)
    
    return jsonify({
        'data': daily,
        'total_days': len(daily)
    })

@app.route('/api/reports/monthly')
def api_reports_monthly():
    """API endpoint for monthly reports"""
    df = load_csv_data()
    
    monthly = get_monthly_stats(df)
    
    # Convert to JSON-serializable format
    monthly = convert_to_serializable(monthly)
    
    return jsonify({
        'data': monthly,
        'total_months': len(monthly)
    })

@app.route('/api/reports/projects')
def api_reports_projects():
    """API endpoint for project-wise reports"""
    df = load_csv_data()
    
    project = request.args.get('project')
    if project:
        df = filter_by_project(df, project)
    
    project_stats = get_project_stats(df)
    
    # Convert to JSON-serializable format
    project_stats = convert_to_serializable(project_stats)
    
    return jsonify({
        'data': project_stats,
        'total_projects': len(project_stats)
    })

@app.route('/api/reports/filters')
def api_reports_filters():
    """API endpoint to get available filters"""
    df = load_csv_data()
    
    if df.empty:
        return jsonify({
            'projects': [],
            'languages': [],
            'events': [],
            'date_range': {
                'min': None,
                'max': None
            }
        })
    
    projects = sorted(df['workspace'].dropna().unique().tolist())
    languages = sorted(df['language'].dropna().unique().tolist())
    events = sorted(df['event'].dropna().unique().tolist())
    
    date_range = {
        'min': df['timestamp'].min().strftime('%Y-%m-%d') if not df.empty else None,
        'max': df['timestamp'].max().strftime('%Y-%m-%d') if not df.empty else None
    }
    
    return jsonify({
        'projects': projects,
        'languages': languages,
        'events': events,
        'date_range': date_range
    })

if __name__ == '__main__':
    # Check if pandas is imported
    try:
        import pandas as pd
    except ImportError:
        print("Error: pandas is required. Install it with: pip install pandas")
        exit(1)
    
    app.run(debug=True, host='0.0.0.0', port=5001)

