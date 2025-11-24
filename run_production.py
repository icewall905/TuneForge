#!/usr/bin/env python3
"""
Production runner for TuneForge using Gunicorn WSGI server
"""
import os
import sys
from app import create_app

# Add the application directory to Python path
sys.path.insert(0, '/opt/tuneforge')

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    # For development/testing, use Flask's built-in server
    # In production, this should be run with Gunicorn
    app.run(host='0.0.0.0', port=5395, debug=False)