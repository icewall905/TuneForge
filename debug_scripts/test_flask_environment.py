#!/usr/bin/env python3
"""
Test script to debug Flask environment and import issues.
"""

import sys
import os

def test_environment():
    """Test the current Python environment"""
    print("🔍 Flask Environment Test")
    print("=" * 50)
    
    # Python version and path
    print(f"Python Version: {sys.version}")
    print(f"Python Executable: {sys.executable}")
    print(f"Python Path: {sys.path[:3]}...")
    
    # Check virtual environment
    venv = os.environ.get('VIRTUAL_ENV')
    if venv:
        print(f"Virtual Environment: {venv}")
    else:
        print("Virtual Environment: None (running in system Python)")
    
    # Test basic imports
    print("\n📦 Testing Basic Imports:")
    try:
        import flask
        print(f"✅ Flask: {flask.__version__}")
    except ImportError as e:
        print(f"❌ Flask: {e}")
    
    try:
        import sqlite3
        print(f"✅ SQLite3: {sqlite3.sqlite_version}")
    except ImportError as e:
        print(f"❌ SQLite3: {e}")
    
    # Test audio analysis imports
    print("\n🎵 Testing Audio Analysis Imports:")
    try:
        import librosa
        print(f"✅ librosa: {librosa.__version__}")
    except ImportError as e:
        print(f"❌ librosa: {e}")
    
    try:
        import numpy
        print(f"✅ numpy: {numpy.__version__}")
    except ImportError as e:
        print(f"❌ numpy: {e}")
    
    try:
        import scipy
        print(f"✅ scipy: {scipy.__version__}")
    except ImportError as e:
        print(f"❌ scipy: {e}")
    
    # Test our custom modules
    print("\n🔧 Testing Custom Modules:")
    
    # Add parent directory to path
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
        print(f"Added {parent_dir} to Python path")
    
    try:
        from audio_analyzer import AudioAnalyzer
        print("✅ AudioAnalyzer imported successfully")
    except ImportError as e:
        print(f"❌ AudioAnalyzer: {e}")
    
    try:
        from audio_analysis_service import AudioAnalysisService
        print("✅ AudioAnalysisService imported successfully")
    except ImportError as e:
        print(f"❌ AudioAnalysisService: {e}")
    
    try:
        from advanced_batch_processor import AdvancedBatchProcessor
        print("✅ AdvancedBatchProcessor imported successfully")
    except ImportError as e:
        print(f"❌ AdvancedBatchProcessor: {e}")
    
    # Test database connection
    print("\n🗄️ Testing Database Connection:")
    try:
        db_path = os.path.join(parent_dir, 'db', 'local_music.db')
        if os.path.exists(db_path):
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT COUNT(*) FROM tracks")
            count = cursor.fetchone()[0]
            print(f"✅ Database connected: {count} tracks found")
            conn.close()
        else:
            print(f"❌ Database file not found: {db_path}")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

if __name__ == "__main__":
    test_environment()
