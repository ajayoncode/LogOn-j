# LogOn Streamlit Tabular View

A simple tabular view for analyzing your LogOn project data, similar to CSV output.

## Features

- **Tabular Data View**: CSV-like table showing all sessions with filtering options
- **Project Filtering**: Filter by specific projects or view all
- **Date Range Filtering**: Select specific date ranges
- **Summary Statistics**: Total time, average session, session count
- **CSV Export**: Download filtered data as CSV file

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the App

1. Start the Streamlit app:
```bash
streamlit run streamlit_app.py
```

2. Open your browser and navigate to the URL shown in the terminal (usually `http://localhost:8501`)

## Data Sources

The app reads from:
- `verticals.json` - List of all projects/verticals
- `logger_data/*.txt` - Individual project log files (parsed directly into pandas DataFrames)

## Usage

The app displays a single tabular view with the following features:
- **Session Data Table**: Shows all sessions in CSV format (Date, Start Time, Project, Goal, Total Minutes)
- **Project Filter**: Dropdown to filter by specific projects
- **Date Range Filter**: Date picker to filter by date range
- **Summary Statistics**: Real-time metrics based on filtered data
- **Project Breakdown**: Summary statistics by project
- **CSV Download**: Export filtered data as CSV file

## Data Processing

- Parses log files using the same logic as `scr.py`
- Calculates session durations from `[LogOn - HH:MM:SS]` entries
- Aggregates multiple duration entries per session
- Converts data to pandas DataFrame for analysis
