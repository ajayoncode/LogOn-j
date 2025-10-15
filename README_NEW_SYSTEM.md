# LogOn - Session Tracking System

A comprehensive session tracking system that automatically monitors your work time based on screen lock/unlock events and provides manual session controls through a Streamlit web interface.

## Features

### 🤖 Auto Session Management
- **Automatic Start**: Auto sessions start with "systemOn" project when screen unlocks
- **Automatic Stop**: All sessions stop when screen locks
- **Session Resumption**: Previous incomplete sessions resume after screen unlock
- **Manual Override**: Auto sessions can be stopped manually from the UI

### 👤 Manual Session Management
- **Project Selection**: Choose from available verticals/projects
- **Goal Setting**: Set specific goals for each manual session
- **Auto-Timeout**: Manual sessions automatically end after 20 minutes
- **Auto Transition**: Auto session starts automatically after manual session timeout

### 📊 Unified Data Storage
- **Single CSV**: All session data stored in `logger_data/sessions.csv`
- **Rich Metadata**: Includes session type, duration, status, and timing
- **Pandas Integration**: Efficient data handling and analysis
- **Export Capability**: Download filtered data as CSV

### 🌐 Web Interface
- **Real-time Status**: View current session status and duration
- **Session Controls**: Start/stop sessions from the web interface
- **Data Visualization**: Comprehensive statistics and project breakdowns
- **Filtering**: Filter by project, type, and date range

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **System Requirements** (Linux):
   - `gnome-screensaver-command` or `loginctl` for screen lock detection
   - Python 3.7+

## Usage

### Quick Start
```bash
python launcher.py
```

This will start both the session manager and Streamlit dashboard at `http://localhost:8501`

### Migration from Legacy System
If you have existing log files, migrate them first:
```bash
python migrate_data.py
```

### Manual Components
- **Session Manager Only**: `python session_manager.py`
- **Streamlit Dashboard Only**: `streamlit run streamlit_app.py`

## Session Types

### Auto Sessions
- **Trigger**: Screen unlock
- **Project**: "systemOn"
- **Goal**: "auto start sessess"
- **Behavior**: Continues until screen lock or manual stop
- **Resumption**: Resumes previous incomplete session if available

### Manual Sessions
- **Trigger**: User action via web interface
- **Project**: User selected
- **Goal**: User defined
- **Timeout**: 20 minutes (then transitions to auto session)
- **Override**: Can override auto sessions

## Data Structure

### CSV Format (`logger_data/sessions.csv`)
```csv
session_id,start_time,end_time,duration_minutes,project,goal,session_type,status,auto_closed
session_1234567890_1234,2024-01-15T10:30:00,2024-01-15T11:00:00,30.0,systemOn,auto start sessess,auto,closed,False
```

### Fields
- `session_id`: Unique identifier
- `start_time`: ISO format datetime
- `end_time`: ISO format datetime (empty if in progress)
- `duration_minutes`: Total session duration
- `project`: Project/vertical name
- `goal`: Session goal/description
- `session_type`: "auto" or "manual"
- `status`: "in_progress" or "closed"
- `auto_closed`: Boolean indicating if session ended automatically

## Web Interface Features

### Session Controls
- **Current Status**: Shows active session details
- **Manual Session**: Start new manual sessions
- **Session Actions**: Stop current sessions

### Data Visualization
- **Summary Statistics**: Total time, sessions, averages
- **Project Breakdown**: Time distribution across projects
- **Filtering**: By project, type, and date range
- **Export**: Download filtered data as CSV

## Configuration

### Projects/Verticals
Edit `verticals.json` to add/remove projects:
```json
[
  "Project AI Data Agent",
  "LogOn",
  "Reading",
  "systemOn",
  "youtube ai comment responder"
]
```

### Timeouts
Modify `AUTO_END_SECONDS` in `session_manager.py` for manual session timeout (default: 20 minutes).

## File Structure
```
LogOn/
├── session_manager.py      # Core session management
├── streamlit_app.py        # Web interface
├── launcher.py            # Combined launcher
├── migrate_data.py        # Legacy data migration
├── verticals.json         # Project definitions
├── logger_data/
│   ├── sessions.csv       # Unified session data
│   └── legacy_backup/     # Migrated legacy files
└── requirements.txt       # Dependencies
```

## Troubleshooting

### Screen Lock Detection Issues
If screen lock detection doesn't work:
1. Check if `gnome-screensaver-command` is installed
2. Try `loginctl` alternative
3. Check system permissions

### Session Not Starting
1. Ensure `logger_data/` directory exists
2. Check `verticals.json` is valid
3. Verify screen is unlocked

### Web Interface Issues
1. Check if port 8501 is available
2. Ensure Streamlit is installed
3. Check browser console for errors

## Development

### Adding New Features
1. Modify `session_manager.py` for core logic
2. Update `streamlit_app.py` for UI changes
3. Test with `launcher.py`

### Data Analysis
Use the exported CSV with pandas for advanced analysis:
```python
import pandas as pd
df = pd.read_csv('logger_data/sessions.csv')
# Your analysis here
```

## Migration Notes

- Legacy `.txt` files are backed up during migration
- Original session timing is preserved
- All sessions are marked as "manual" type for legacy data
- Status is set to "closed" for completed legacy sessions

## License

This project maintains the same license as the original LogOn system.
