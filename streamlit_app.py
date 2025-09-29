import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import re
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="LogOn Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .project-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2e8b57;
        margin-top: 2rem;
        margin-bottom: 1rem;
        padding: 0.5rem;
        background-color: #f0f8ff;
        border-left: 4px solid #2e8b57;
    }
    /* Center align Date & Time column */
    .dataframe th:nth-child(1),
    .dataframe td:nth-child(1) {
        text-align: center !important;
    }
    /* Left align Total Minutes column */
    .dataframe th:nth-child(4),
    .dataframe td:nth-child(4) {
        text-align: left !important;
    }
    /* Left align all project breakdown columns */
    .dataframe th:nth-child(2),
    .dataframe td:nth-child(2),
    .dataframe th:nth-child(3),
    .dataframe td:nth-child(3),
    .dataframe th:nth-child(4),
    .dataframe td:nth-child(4),
    .dataframe th:nth-child(5),
    .dataframe td:nth-child(5) {
        text-align: left !important;
    }
</style>
""", unsafe_allow_html=True)

def load_verticals():
    """Load verticals from JSON file"""
    try:
        with open('verticals.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def parse_log_file(file_path, project_name):
    """Parse individual log file and return structured data similar to scr.py logic"""
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
            
            # Check for session start - using same pattern as scr.py
            start_pattern = re.compile(r"(\d{2}:\d{2}) (\w{3}) (\d{1,2}) (\w{3}) (\d{4}) \[ (.*?) \] : Start logging Goal: (.*)")
            start_match = start_pattern.match(line)
            
            if start_match:
                # Save previous session if exists
                if current_session:
                    # Use the last duration as the actual working time
                    if last_duration:
                        total_minutes = last_duration.total_seconds() / 60
                        current_session['total_minutes'] = round(total_minutes, 2)
                    else:
                        current_session['total_minutes'] = 0
                    sessions.append(current_session)
                
                # Start new session
                time_str, day_name, day, month, year, project, goal = start_match.groups()
                last_duration = None
                
                current_session = {
                    'date': f"{day} {month} {year}",
                    'start_time': time_str,
                    'project': project,
                    'goal': goal,
                    'durations': [],
                    'entries': [],
                    'status': 'in_progress'
                }
            
            # Check for duration entries - using same pattern as scr.py
            elif current_session and "[LogOn -" in line:
                duration_pattern = re.compile(r"\[LogOn - (\d{2}):(\d{2}):(\d{2})\]")
                duration_match = duration_pattern.search(line)
                
                if duration_match:
                    h, m, s = map(int, duration_match.groups())
                    duration = timedelta(hours=h, minutes=m, seconds=s)
                    # Store the latest duration (this is the actual working time)
                    last_duration = duration
                    current_session['durations'].append(duration)
                
                # Also capture notes and status
                note_match = re.search(r'NOTE: (.+)', line)
                status_match = re.search(r'(closed|in progress|auto-closed)', line)
                
                entry = {
                    'duration': duration_match.group(0) if duration_match else None,
                    'note': note_match.group(1) if note_match else None,
                    'status': status_match.group(1) if status_match else None,
                    'raw_line': line
                }
                current_session['entries'].append(entry)
        
        # Add last session
        if current_session:
            # Use the last duration as the actual working time
            if last_duration:
                total_minutes = last_duration.total_seconds() / 60
                current_session['total_minutes'] = round(total_minutes, 2)
            else:
                current_session['total_minutes'] = 0
            sessions.append(current_session)
    
    except Exception as e:
        st.error(f"Error parsing {file_path}: {str(e)}")
    
    return sessions


def create_tabular_view():
    """Create a tabular view similar to scr.py CSV output"""
    verticals = load_verticals()
    tabular_data = []
    
    for project in verticals:
        filename = project.replace(' ', '_') + '.txt'
        log_file_path = f"logger_data/{filename}"
        
        if os.path.exists(log_file_path):
            sessions = parse_log_file(log_file_path, project)
            for session in sessions:
                # Combine date and time into a single column
                datetime_str = f"{session['date']} {session['start_time']}"
                tabular_data.append({
                    'Date & Time': datetime_str,
                    'Project': session['project'],
                    'Goal': session['goal'],
                    'Total Minutes': session['total_minutes']
                })
    
    return pd.DataFrame(tabular_data)



def main():
    # Header
    st.markdown('<h1 class="main-header">📊 LogOn View</h1>', unsafe_allow_html=True)
    
    # Load data
    verticals = load_verticals()
    
    
    tabular_df = create_tabular_view()
    
    if not tabular_df.empty:
        # Convert date & time column for proper display and filtering
        tabular_df['Date & Time'] = pd.to_datetime(tabular_df['Date & Time'], format='%d %b %Y %H:%M', errors='coerce')
        
        # Add filters
        col1, col2 = st.columns(2)
        
        with col1:
            # Project filter
            projects = ['All'] + list(tabular_df['Project'].unique())
            selected_project = st.selectbox("Filter by Project", projects)
            
        with col2:
            # Date range filter
            if len(tabular_df) > 1:
                date_range = st.date_input(
                    "Select Date Range",
                    value=(tabular_df['Date & Time'].min().date(), tabular_df['Date & Time'].max().date()),
                    min_value=tabular_df['Date & Time'].min().date(),
                    max_value=tabular_df['Date & Time'].max().date()
                )
            else:
                date_range = None
        
        # Apply filters
        filtered_df = tabular_df.copy()
        
        if selected_project != 'All':
            filtered_df = filtered_df[filtered_df['Project'] == selected_project]
        
        if date_range and len(date_range) == 2:
            filtered_df = filtered_df[
                (filtered_df['Date & Time'].dt.date >= date_range[0]) &
                (filtered_df['Date & Time'].dt.date <= date_range[1])
            ]
        

        
        # Summary statistics
        st.subheader("Summary Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_minutes = filtered_df['Total Minutes'].sum()
            st.metric("Total Time (minutes)", f"{total_minutes:.1f}")
        
        with col2:
            total_hours = total_minutes / 60
            st.metric("Total Time (hours)", f"{total_hours:.1f}")
        
        with col3:
            avg_time = filtered_df['Total Minutes'].mean()
            st.metric("Average Session (minutes)", f"{avg_time:.1f}")
        
        with col4:
            session_count = len(filtered_df)
            st.metric("Total Sessions", session_count)
        
        # Project breakdown
        if len(filtered_df['Project'].unique()) > 1:
            st.subheader("Project Breakdown")
            project_breakdown = filtered_df.groupby('Project').agg({
                'Total Minutes': ['sum', 'mean', 'count']
            }).round(2)
            project_breakdown.columns = ['Total Minutes', 'Avg Minutes', 'Sessions']
            
            # Add Total Hours column
            project_breakdown['Total Hours'] = (project_breakdown['Total Minutes'] / 60).round(2)
            
            # Reorder columns to show Total Hours after Total Minutes
            project_breakdown = project_breakdown[['Total Minutes', 'Total Hours', 'Avg Minutes', 'Sessions']]
            
            # Format the values for better readability
            formatted_breakdown = project_breakdown.copy()
            formatted_breakdown['Total Minutes'] = formatted_breakdown['Total Minutes'].apply(lambda x: f"{int(x)} min")
            formatted_breakdown['Total Hours'] = formatted_breakdown['Total Hours'].apply(lambda x: f"{x:.1f} hrs")
            formatted_breakdown['Avg Minutes'] = formatted_breakdown['Avg Minutes'].apply(lambda x: f"{int(x)} min")
            formatted_breakdown['Sessions'] = formatted_breakdown['Sessions'].apply(lambda x: f"{int(x)} sessions")
            
            st.dataframe(formatted_breakdown, use_container_width=True)
        
                # Display the tabular data
        st.subheader("Session Data (CSV Format)")
        st.dataframe(filtered_df, use_container_width=True)
        # Download CSV option
        csv_data = filtered_df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv_data,
            file_name="logon_sessions.csv",
            mime="text/csv"
        )
    else:
        st.warning("No session data available")

if __name__ == "__main__":
    main()
