#!/usr/bin/env python3
"""
Migration script to convert legacy log files to CSV format
"""

import os
import json
import csv
import re
from datetime import datetime, timedelta
from pathlib import Path

def parse_legacy_log_file(file_path, project_name):
    """Parse individual legacy log file and return structured data"""
    sessions = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_session = None
        last_duration = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for session start
            start_pattern = re.compile(r"(\d{2}:\d{2}) (\w{3}) (\d{1,2}) (\w{3}) (\d{4}) \[ (.*?) \] : Start logging Goal: (.*)")
            start_match = start_pattern.match(line)
            
            if start_match:
                # Save previous session if exists
                if current_session:
                    if last_duration:
                        total_minutes = last_duration.total_seconds() / 60
                        current_session['duration_minutes'] = round(total_minutes, 2)
                    else:
                        current_session['duration_minutes'] = 0
                    sessions.append(current_session)
                
                # Start new session
                time_str, day_name, day, month, year, project, goal = start_match.groups()
                last_duration = None
                
                # Create datetime object
                date_str = f"{day} {month} {year}"
                datetime_str = f"{date_str} {time_str}"
                start_datetime = datetime.strptime(datetime_str, '%d %b %Y %H:%M')
                
                current_session = {
                    'start_time': start_datetime,
                    'end_time': None,
                    'project': project,
                    'goal': goal,
                    'status': 'closed',  # Assume closed since we're migrating
                    'session_type': 'manual',  # Assume manual for legacy data
                    'auto_closed': False
                }
            
            # Check for duration entries
            elif current_session and "[LogOn -" in line:
                duration_pattern = re.compile(r"\[LogOn - (\d{2}):(\d{2}):(\d{2})\]")
                duration_match = duration_pattern.search(line)
                
                if duration_match:
                    h, m, s = map(int, duration_match.groups())
                    duration = timedelta(hours=h, minutes=m, seconds=s)
                    last_duration = duration
                
                # Check for session end
                if 'closed' in line or 'auto-closed' in line:
                    current_session['auto_closed'] = 'auto-closed' in line
        
        # Add last session
        if current_session:
            if last_duration:
                total_minutes = last_duration.total_seconds() / 60
                current_session['duration_minutes'] = round(total_minutes, 2)
                current_session['end_time'] = current_session['start_time'] + last_duration
            else:
                current_session['duration_minutes'] = 0
            sessions.append(current_session)
    
    except Exception as e:
        print(f"Error parsing {file_path}: {str(e)}")
    
    return sessions

def migrate_legacy_data():
    """Migrate all legacy log files to CSV format"""
    
    # Ensure directories exist
    Path("logger_data").mkdir(exist_ok=True)
    
    csv_file = "logger_data/sessions.csv"
    
    # Load verticals
    try:
        with open('verticals.json', 'r') as f:
            verticals = json.load(f)
    except FileNotFoundError:
        verticals = ["systemOn"]
        print("No verticals.json found, using default: systemOn")
    
    all_sessions = []
    
    # Process each vertical's log file
    for project in verticals:
        filename = project.replace(' ', '_') + '.txt'
        log_file_path = f"logger_data/{filename}"
        
        if os.path.exists(log_file_path):
            print(f"Processing {log_file_path}...")
            sessions = parse_legacy_log_file(log_file_path, project)
            
            # Add session IDs
            for i, session in enumerate(sessions):
                session['session_id'] = f"migrated_{project}_{i}_{int(session['start_time'].timestamp())}"
                all_sessions.append(session)
            
            print(f"  Found {len(sessions)} sessions")
        else:
            print(f"  No log file found for {project}")
    
    # Sort sessions by start time
    all_sessions.sort(key=lambda x: x['start_time'])
    
    # Write to CSV
    if all_sessions:
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'session_id', 'start_time', 'end_time', 'duration_minutes', 
                'project', 'goal', 'session_type', 'status', 'auto_closed'
            ])
            
            for session in all_sessions:
                writer.writerow([
                    session['session_id'],
                    session['start_time'].isoformat(),
                    session['end_time'].isoformat() if session['end_time'] else '',
                    session['duration_minutes'],
                    session['project'],
                    session['goal'],
                    session['session_type'],
                    session['status'],
                    session['auto_closed']
                ])
        
        print(f"\n✅ Migration complete!")
        print(f"📊 Migrated {len(all_sessions)} sessions to {csv_file}")
        
        # Create backup of original files
        backup_dir = Path("logger_data/legacy_backup")
        backup_dir.mkdir(exist_ok=True)
        
        for project in verticals:
            filename = project.replace(' ', '_') + '.txt'
            log_file_path = f"logger_data/{filename}"
            if os.path.exists(log_file_path):
                backup_path = backup_dir / filename
                os.rename(log_file_path, backup_path)
                print(f"📁 Backed up {filename} to {backup_path}")
        
        print(f"\n🎉 Migration successful! Original files backed up to {backup_dir}")
        print("You can now use the new LogOn system with CSV data.")
        
    else:
        print("No sessions found to migrate.")

if __name__ == "__main__":
    print("🔄 LogOn Data Migration Tool")
    print("This will convert legacy log files to the new CSV format.\n")
    
    response = input("Do you want to proceed with migration? (y/N): ")
    if response.lower() in ['y', 'yes']:
        migrate_legacy_data()
    else:
        print("Migration cancelled.")
