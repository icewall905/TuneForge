#!/bin/bash
# Simple script to start TuneForge

# Change to the script's directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [[ -d "venv" ]]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Virtual environment not found. Do you want to create one? (y/n)"
    read -r create_venv
    if [[ "$create_venv" =~ ^[Yy]$ ]]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        echo "Installing dependencies..."
        pip install -r requirements.txt
    else
        echo "Continuing without virtual environment..."
    fi
fi

# Check if config.ini exists
if [[ ! -f "config.ini" ]]; then
    echo "Config file not found. Creating from example..."
    cp config.ini.example config.ini
    echo "Please edit config.ini with your settings."
    echo "You can continue for now with default settings."
fi

# Run the application
echo "Starting TuneForge on port 5395..."
python run.py

# Deactivate virtual environment on exit
if [[ -n "$VIRTUAL_ENV" ]]; then
    deactivate
fi
