#!/bin/bash
# Script to run the Code Heartbeats Dashboard

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q flask jinja2 pandas

# Run the application
echo "Starting dashboard on http://localhost:5001"
python app.py

