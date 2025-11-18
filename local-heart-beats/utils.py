import pandas as pd
import os
from datetime import datetime
from pathlib import Path
import json

CSV_PATH = os.path.expanduser('~/.local_code_heartbeats.csv')

def load_csv_data():
    """Load CSV data into pandas DataFrame"""
    try:
        if not os.path.exists(CSV_PATH):
            return pd.DataFrame()
        
        df = pd.read_csv(CSV_PATH)
        
        # Parse timestamp with UTC timezone, then convert to naive datetime
        # This avoids warnings when converting to Period later
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', utc=True)
        
        # Convert to naive datetime (remove timezone) to avoid Period warnings
        if df['timestamp'].dt.tz is not None:
            df['timestamp'] = df['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)
        
        # Convert durationMs to numeric
        df['durationMs'] = pd.to_numeric(df['durationMs'], errors='coerce').fillna(0)
        
        # Extract date components
        df['date'] = df['timestamp'].dt.date
        df['month'] = df['timestamp'].dt.strftime('%Y-%m')  # Use strftime instead of to_period to avoid timezone warning
        df['year_month'] = df['timestamp'].dt.strftime('%Y-%m')
        df['day_of_week'] = df['timestamp'].dt.day_name()
        df['hour'] = df['timestamp'].dt.hour
        
        return df.dropna(subset=['timestamp'])
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return pd.DataFrame()

def get_summary_stats(df):
    """Get summary statistics"""
    if df.empty:
        return {}
    
    total_events = len(df)
    total_duration = df['durationMs'].sum() / 1000 / 60  # Convert to minutes
    unique_projects = df['workspace'].nunique()
    unique_files = df['file'].nunique()
    unique_languages = df['language'].dropna().nunique()
    
    # Event types
    event_counts = df['event'].value_counts().to_dict()
    
    # Top projects by duration
    project_duration = df.groupby('workspace')['durationMs'].sum().sort_values(ascending=False).head(10)
    top_projects = project_duration.to_dict()
    
    # Top languages
    language_counts = df['language'].value_counts().head(10).to_dict()
    
    return {
        'total_events': int(total_events),
        'total_duration_minutes': float(round(total_duration, 2)),
        'unique_projects': int(unique_projects),
        'unique_files': int(unique_files),
        'unique_languages': int(unique_languages),
        'event_counts': {k: int(v) for k, v in event_counts.items()},
        'top_projects': {k: float(round(v/1000/60, 2)) for k, v in top_projects.items()},
        'language_counts': {k: int(v) for k, v in language_counts.items()}
    }

def get_daily_stats(df):
    """Get daily statistics"""
    if df.empty:
        return []
    
    daily = df.groupby('date').agg({
        'durationMs': ['sum', 'count'],
        'workspace': 'nunique',
        'file': 'nunique'
    }).reset_index()
    
    daily.columns = ['date', 'total_duration', 'event_count', 'project_count', 'file_count']
    daily['total_duration'] = daily['total_duration'] / 1000 / 60  # minutes
    daily['date'] = daily['date'].astype(str)
    # Convert numpy types to native Python types
    daily['total_duration'] = daily['total_duration'].astype(float)
    daily['event_count'] = daily['event_count'].astype(int)
    daily['project_count'] = daily['project_count'].astype(int)
    daily['file_count'] = daily['file_count'].astype(int)
    
    return daily.to_dict('records')

def get_monthly_stats(df):
    """Get monthly statistics"""
    if df.empty:
        return []
    
    monthly = df.groupby('year_month').agg({
        'durationMs': ['sum', 'count'],
        'workspace': 'nunique',
        'file': 'nunique'
    }).reset_index()
    
    monthly.columns = ['month', 'total_duration', 'event_count', 'project_count', 'file_count']
    monthly['total_duration'] = monthly['total_duration'] / 1000 / 60  # minutes
    # Convert numpy types to native Python types
    monthly['total_duration'] = monthly['total_duration'].astype(float)
    monthly['event_count'] = monthly['event_count'].astype(int)
    monthly['project_count'] = monthly['project_count'].astype(int)
    monthly['file_count'] = monthly['file_count'].astype(int)
    
    return monthly.to_dict('records')

def get_project_stats(df):
    """Get project-wise statistics"""
    if df.empty:
        return []
    
    project_stats = df.groupby('workspace').agg({
        'durationMs': ['sum', 'count', 'mean'],
        'file': 'nunique',
        'timestamp': ['min', 'max']
    }).reset_index()
    
    project_stats.columns = [
        'workspace', 'total_duration', 'event_count', 
        'avg_duration', 'file_count', 'first_seen', 'last_seen'
    ]
    
    project_stats['total_duration'] = project_stats['total_duration'] / 1000 / 60  # minutes
    project_stats['avg_duration'] = project_stats['avg_duration'] / 1000  # seconds
    
    # Format dates - handle both Timestamp and already-formatted strings
    if pd.api.types.is_datetime64_any_dtype(project_stats['first_seen']):
        project_stats['first_seen'] = project_stats['first_seen'].dt.strftime('%Y-%m-%d %H:%M')
    if pd.api.types.is_datetime64_any_dtype(project_stats['last_seen']):
        project_stats['last_seen'] = project_stats['last_seen'].dt.strftime('%Y-%m-%d %H:%M')
    
    # Convert numpy types to native Python types
    project_stats['total_duration'] = project_stats['total_duration'].astype(float)
    project_stats['event_count'] = project_stats['event_count'].astype(int)
    project_stats['avg_duration'] = project_stats['avg_duration'].astype(float)
    project_stats['file_count'] = project_stats['file_count'].astype(int)
    
    return project_stats.to_dict('records')

def get_hourly_activity(df):
    """Get hourly activity distribution"""
    if df.empty:
        return {}
    
    hourly = df.groupby('hour')['durationMs'].sum().reset_index()
    hourly['duration_minutes'] = hourly['durationMs'] / 1000 / 60
    hourly = hourly.sort_values('hour')
    
    # Convert numpy types to native Python types
    hourly['hour'] = hourly['hour'].astype(int)
    hourly['duration_minutes'] = hourly['duration_minutes'].astype(float)
    
    return {
        'hours': hourly['hour'].tolist(),
        'duration': hourly['duration_minutes'].tolist()
    }

def get_event_timeline(df, limit=100):
    """Get recent events timeline"""
    if df.empty:
        return []
    
    recent = df.sort_values('timestamp', ascending=False).head(limit)
    
    # Select columns and convert to dict
    result = recent[[
        'timestamp', 'event', 'file', 'language', 
        'workspace', 'durationMs', 'gitBranch'
    ]].copy()
    
    # Convert durationMs to native Python types and fill NaN
    result['durationMs'] = result['durationMs'].fillna(0).astype(float)
    
    # Replace NaN/None with empty strings or None for JSON serialization
    result = result.fillna('')
    
    # Convert to dict and ensure all values are JSON serializable
    records = result.to_dict('records')
    
    # Convert any remaining pandas/numpy types
    for record in records:
        for key, value in record.items():
            if pd.isna(value):
                record[key] = ''
            elif isinstance(value, pd.Timestamp):
                record[key] = value.strftime('%Y-%m-%d %H:%M:%S')
            elif hasattr(value, 'item'):  # numpy scalar
                try:
                    record[key] = value.item()
                except (AttributeError, ValueError):
                    record[key] = value
    
    return records

def filter_by_date_range(df, start_date=None, end_date=None):
    """Filter DataFrame by date range"""
    if df.empty:
        return df
    
    if start_date:
        start_date = pd.to_datetime(start_date)
        df = df[df['timestamp'] >= start_date]
    
    if end_date:
        end_date = pd.to_datetime(end_date)
        df = df[df['timestamp'] <= end_date]
    
    return df

def filter_by_project(df, project=None):
    """Filter DataFrame by project"""
    if df.empty or not project:
        return df
    
    return df[df['workspace'] == project]

def get_day_of_week_stats(df):
    """Get statistics by day of week"""
    if df.empty:
        return []
    
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    day_stats = df.groupby('day_of_week').agg({
        'durationMs': ['sum', 'count'],
        'workspace': 'nunique',
        'file': 'nunique'
    }).reset_index()
    
    day_stats.columns = ['day', 'total_duration', 'event_count', 'project_count', 'file_count']
    day_stats['total_duration'] = day_stats['total_duration'] / 1000 / 60  # minutes
    
    # Ensure all days are present
    day_map = {day: {'total_duration': 0.0, 'event_count': 0, 'project_count': 0, 'file_count': 0} 
               for day in day_order}
    
    for _, row in day_stats.iterrows():
        day_map[row['day']] = {
            'total_duration': float(row['total_duration']),
            'event_count': int(row['event_count']),
            'project_count': int(row['project_count']),
            'file_count': int(row['file_count'])
        }
    
    result = [{'day': day, **day_map[day]} for day in day_order]
    return result

def get_daily_project_breakdown(df):
    """Get daily breakdown by project"""
    if df.empty:
        return []
    
    daily_projects = df.groupby(['date', 'workspace']).agg({
        'durationMs': 'sum'
    }).reset_index()
    
    daily_projects['duration_minutes'] = daily_projects['durationMs'] / 1000 / 60
    daily_projects['date'] = daily_projects['date'].astype(str)
    
    # Get top projects
    top_projects = df.groupby('workspace')['durationMs'].sum().nlargest(5).index.tolist()
    
    # Pivot to get projects as columns
    pivot = daily_projects[daily_projects['workspace'].isin(top_projects)].pivot(
        index='date', 
        columns='workspace', 
        values='duration_minutes'
    ).fillna(0)
    
    result = []
    for date in pivot.index:
        row = {'date': str(date)}
        for project in top_projects:
            row[project] = float(pivot.loc[date, project]) if project in pivot.columns else 0.0
        result.append(row)
    
    return result

def get_cumulative_time(df):
    """Get cumulative time worked over time"""
    if df.empty:
        return []
    
    daily = df.groupby('date')['durationMs'].sum().reset_index()
    daily['date'] = daily['date'].astype(str)
    daily = daily.sort_values('date')
    daily['duration_minutes'] = daily['durationMs'] / 1000 / 60
    daily['cumulative_minutes'] = daily['duration_minutes'].cumsum()
    
    result = []
    for _, row in daily.iterrows():
        result.append({
            'date': str(row['date']),
            'daily_minutes': float(row['duration_minutes']),
            'cumulative_minutes': float(row['cumulative_minutes'])
        })
    
    return result

def get_working_hours_analysis(df):
    """Get analysis of working hours per day"""
    if df.empty:
        return []
    
    # Calculate working hours per day (consider active hours)
    daily_hours = df.groupby('date').agg({
        'hour': ['min', 'max', 'nunique'],
        'durationMs': 'sum'
    }).reset_index()
    
    daily_hours.columns = ['date', 'start_hour', 'end_hour', 'active_hours', 'duration_ms']
    daily_hours['date'] = daily_hours['date'].astype(str)
    # Use active_hours (hours with actual activity) instead of span
    # This is more accurate than counting all hours between start and end
    daily_hours['working_hours'] = daily_hours['active_hours']
    daily_hours['duration_minutes'] = daily_hours['duration_ms'] / 1000 / 60
    # Productivity: actual coding time / active hours
    daily_hours['productivity'] = daily_hours['duration_minutes'] / (daily_hours['working_hours'] * 60) * 100
    
    result = []
    for _, row in daily_hours.iterrows():
        result.append({
            'date': str(row['date']),
            'start_hour': int(row['start_hour']) if pd.notna(row['start_hour']) else 0,
            'end_hour': int(row['end_hour']) if pd.notna(row['end_hour']) else 0,
            'working_hours': float(row['working_hours']) if pd.notna(row['working_hours']) else 0.0,
            'duration_minutes': float(row['duration_minutes']),
            'productivity': float(row['productivity']) if pd.notna(row['productivity']) else 0.0,
            'active_hours': int(row['active_hours']) if pd.notna(row['active_hours']) else 0
        })
    
    return result

