#!/usr/bin/env python3
"""
Debug script to test TuneForge Flask application step by step
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test if all imports work correctly"""
    print("Testing imports...")
    try:
        from app import create_app
        print("✓ Successfully imported create_app")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_app_creation():
    """Test if the Flask app can be created"""
    print("\nTesting app creation...")
    try:
        from app import create_app
        app = create_app()
        print("✓ Flask app created successfully")
        return app
    except Exception as e:
        print(f"✗ App creation failed: {e}")
        return None

def test_template_rendering(app):
    """Test if templates can be rendered"""
    print("\nTesting template rendering...")
    try:
        with app.app_context():
            print("✓ App context created")
            
            # Test the root route
            response = app.test_client().get('/')
            print(f"✓ Root route response: {response.status_code}")
            print(f"✓ Response length: {len(response.data)} bytes")
            
            # Test if response contains expected content
            if b'html' in response.data.lower():
                print("✓ Response contains HTML content")
            else:
                print("⚠ Response doesn't contain HTML content")
                
            return True
    except Exception as e:
        print(f"✗ Template rendering failed: {e}")
        return False

def test_config_loading():
    """Test if configuration can be loaded"""
    print("\nTesting configuration loading...")
    try:
        from app.routes import load_config
        config = load_config()
        print("✓ Configuration loaded successfully")
        
        # Check if key sections exist
        if 'OLLAMA' in config:
            print("✓ OLLAMA section found")
        if 'APP' in config:
            print("✓ APP section found")
            
        return True
    except Exception as e:
        print(f"✗ Configuration loading failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print(" TuneForge Flask App Debug Test ")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        return False
    
    # Test app creation
    app = test_app_creation()
    if not app:
        return False
    
    # Test template rendering
    if not test_template_rendering(app):
        return False
    
    # Test configuration
    if not test_config_loading():
        return False
    
    print("\n" + "=" * 50)
    print(" ✓ All tests passed! The app should work correctly.")
    print("=" * 50)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
