import re
import csv
from datetime import datetime, timedelta

# Input log file path
log_file = "/home/ajay-dev/Documents/HangOn/LogOn/logger_data/Project_AI_Data_Agent.txt"

# Output CSV file path (same folder)
csv_file = "/home/ajay-dev/Documents/HangOn/LogOn/logger_data/work_log.csv"

# Regex patterns
start_pattern = re.compile(r"(\d{2}:\d{2}) (\w{3}) (\d{2}) (\w{3}) (\d{4}) \[ (.*?) \] : Start logging Goal: (.*)")
duration_pattern = re.compile(r"\[LogOn - (\d{2}):(\d{2}):(\d{2})\]")

rows = []
current_entry = None

# Read log file
with open(log_file, "r") as f:
    for line in f:
        line = line.strip()
        start_match = start_pattern.match(line)
        duration_match = duration_pattern.match(line)

        if start_match:
            # Save previous entry if exists
            if current_entry:
                rows.append(current_entry)

            time_str, day_name, day, month, year, project, goal = start_match.groups()
            start_datetime = datetime.strptime(f"{day} {month} {year} {time_str}", "%d %b %Y %H:%M")

            current_entry = {
                "date": f"{day} {month} {year}",
                "start_time": time_str,
                "project": project,
                "goal": goal,
                "durations": [],
            }

        elif duration_match and current_entry:
            h, m, s = map(int, duration_match.groups())
            duration = timedelta(hours=h, minutes=m, seconds=s)
            current_entry["durations"].append(duration)

# Add last entry
if current_entry:
    rows.append(current_entry)

# Process totals
csv_rows = []
for entry in rows:
    total_minutes = sum([d.total_seconds() for d in entry["durations"]]) / 60
    csv_rows.append([
        entry["date"],
        entry["start_time"],
        entry["project"],
        entry["goal"],
        round(total_minutes, 2)
    ])

# Write CSV
with open(csv_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Date", "Start Time", "Project", "Goal", "Total Minutes"])
    writer.writerows(csv_rows)

print(f"✅ CSV file created: {csv_file}")
