# Code Heartbeats Dashboard

An interactive dashboard for visualizing code activity data from `.local_code_heartbeats.csv`.

## Features

- 📊 **Real-time Dashboard** with auto-refresh every 10 seconds
- 📈 **Interactive Charts** using Chart.js
- 📅 **Daily Reports** - View activity by day with date filters
- 📆 **Monthly Reports** - Aggregate monthly statistics
- 🏢 **Project Reports** - Analyze activity by project/workspace
- 🎨 **Beautiful UI** - Modern, responsive design
- ⚡ **Fast Performance** - Efficient data processing with pandas

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r ../requirements.txt
   ```

2. **Ensure CSV File Exists**
   The dashboard reads from `~/.local_code_heartbeats.csv`

3. **Run the Application**
   ```bash
   cd local-heart-beats
   python app.py
   ```

4. **Access Dashboard**
   Open your browser and navigate to: `http://localhost:5001`

## Structure

```
local-heart-beats/
├── app.py              # Flask application
├── utils.py            # Data processing utilities
├── templates/          # Jinja2 templates
│   ├── base.html
│   ├── dashboard.html
│   └── reports.html
├── static/
│   ├── css/
│   │   ├── style.css
│   │   └── reports.css
│   └── js/
│       ├── main.js
│       ├── dashboard.js
│       └── reports.js
└── README.md
```

## API Endpoints

- `GET /` - Main dashboard page
- `GET /reports` - Reports page
- `GET /api/data` - Dashboard data (summary, daily stats, hourly activity, recent events)
- `GET /api/reports/daily?start_date=&end_date=` - Daily reports with optional date filters
- `GET /api/reports/monthly` - Monthly reports
- `GET /api/reports/projects?project=` - Project reports with optional project filter
- `GET /api/reports/filters` - Available filters (projects, languages, events, date range)

## Dashboard Features

### Main Dashboard
- Summary cards showing total events, duration, projects, files, and languages
- Daily activity line chart
- Hourly activity bar chart
- Event types distribution (doughnut chart)
- Top projects by duration (horizontal bar chart)
- Recent events table

### Reports Page
- **Daily Reports**: View daily statistics with date range filters
- **Monthly Reports**: View monthly aggregated statistics
- **Project Reports**: View per-project statistics with project filter
- Interactive charts for each report type
- Filterable data tables

## Auto-Refresh

The dashboard automatically refreshes every 10 seconds to show the latest data. The last update time is displayed in the header.

## Data Source

The dashboard reads from `~/.local_code_heartbeats.csv` which should have the following columns:
- `timestamp` - ISO 8601 timestamp
- `event` - Event type (typing, save, activate, etc.)
- `file` - File path
- `language` - Programming language
- `workspace` - Project/workspace path
- `durationMs` - Duration in milliseconds
- `gitBranch` - Git branch name (optional)

## License

MIT

