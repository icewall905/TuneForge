#!/usr/bin/env python3
"""
Test script to verify the Ollama Playlist Generator application setup.
This script checks that all required components are in place and properly configured.
"""

import os
import sys
import importlib
import configparser

def check_dependencies():
    """Check if all required Python packages are installed."""
    required_packages = ['flask', 'requests']
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"✓ {package} is installed")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} is not installed")
    
    return missing_packages

def check_project_structure():
    """Check if the project directory structure is set up correctly."""
    required_dirs = ['app', 'static', 'templates', 'static/css', 'static/js', 'static/images']
    required_files = [
        'run.py', 
        'app/__init__.py', 
        'app/routes.py',
        'templates/layout.html',
        'templates/index.html',
        'templates/history.html',
        'templates/settings.html',
        'static/css/style.css',
        'static/css/custom.css',
        'static/js/main.js',
        'static/images/logo.svg',
        'config.ini.example'
    ]
    
    missing_dirs = []
    missing_files = []
    
    for dir_path in required_dirs:
        if not os.path.isdir(dir_path):
            missing_dirs.append(dir_path)
            print(f"✗ Directory '{dir_path}' not found")
        else:
            print(f"✓ Directory '{dir_path}' exists")
    
    for file_path in required_files:
        if not os.path.isfile(file_path):
            missing_files.append(file_path)
            print(f"✗ File '{file_path}' not found")
        else:
            print(f"✓ File '{file_path}' exists")
    
    return missing_dirs, missing_files

def check_config():
    """Check if configuration is set up correctly."""
    if os.path.isfile('config.ini'):
        print("✓ Configuration file 'config.ini' exists")
        try:
            config = configparser.ConfigParser()
            config.read('config.ini')
            
            # Check essential sections and keys
            sections = ['OLLAMA', 'APP']
            required_keys = {
                'OLLAMA': ['URL', 'Model'],
                'APP': ['Likes', 'Dislikes']
            }
            
            config_issues = []
            
            for section in sections:
                if section not in config:
                    config_issues.append(f"Missing section: {section}")
                    print(f"✗ Configuration section '{section}' is missing")
                else:
                    print(f"✓ Configuration section '{section}' exists")
                    for key in required_keys.get(section, []):
                        if key not in config[section]:
                            config_issues.append(f"Missing key: {section}.{key}")
                            print(f"✗ Configuration key '{section}.{key}' is missing")
                        else:
                            print(f"✓ Configuration key '{section}.{key}' exists")
            
            return config_issues
        except Exception as e:
            print(f"✗ Error reading configuration file: {e}")
            return [f"Config parsing error: {str(e)}"]
    else:
        print("✗ Configuration file 'config.ini' not found (you need to create it from config.ini.example)")
        return ["config.ini not found"]

def main():
    """Main function to run all checks."""
    print("\n" + "="*50)
    print(" Ollama Playlist Generator - Setup Check ")
    print("="*50 + "\n")
    
    # Check Python version
    python_version = sys.version.split()[0]
    if python_version < '3.7':
        print(f"✗ Python version {python_version} is below the recommended 3.7+")
    else:
        print(f"✓ Python version {python_version} meets requirements (3.7+)")
    
    print("\n--- Checking Dependencies ---")
    missing_packages = check_dependencies()
    
    print("\n--- Checking Project Structure ---")
    missing_dirs, missing_files = check_project_structure()
    
    print("\n--- Checking Configuration ---")
    config_issues = check_config()
    
    print("\n" + "="*50)
    print(" Summary ")
    print("="*50)
    
    if not missing_packages and not missing_dirs and not missing_files and not config_issues:
        print("✓ All checks passed! Your Ollama Playlist Generator setup looks good.")
        print("\nTo start the application, run:")
        print("  python run.py")
        return 0
    else:
        print("✗ Some checks failed. Please address the following issues:")
        
        if missing_packages:
            print("\nMissing Python packages:")
            print("  Install them with: pip install " + " ".join(missing_packages))
        
        if missing_dirs or missing_files:
            print("\nMissing files or directories:")
            for item in missing_dirs + missing_files:
                print(f"  - {item}")
        
        if config_issues:
            print("\nConfiguration issues:")
            for issue in config_issues:
                print(f"  - {issue}")
            if "config.ini not found" in config_issues:
                print("  Create a configuration file by copying the example:")
                print("  cp config.ini.example config.ini")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())
