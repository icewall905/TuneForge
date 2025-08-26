#!/usr/bin/env python3
"""
Test script for auto-startup configuration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routes import get_config_value, load_config

def test_auto_startup_config():
    """Test the auto-startup configuration loading"""
    print("🔧 Testing Auto-Startup Configuration")
    print("=" * 50)
    
    try:
        # Test loading the configuration
        config = load_config()
        print(f"✅ Configuration loaded successfully")
        
        # Check if AUTO_STARTUP section exists
        if config.has_section('AUTO_STARTUP'):
            print(f"✅ AUTO_STARTUP section found")
            
            # Test individual values
            enable_scan = get_config_value('AUTO_STARTUP', 'EnableAutoScan', 'no')
            enable_analysis = get_config_value('AUTO_STARTUP', 'EnableAutoAnalysis', 'no')
            startup_delay = get_config_value('AUTO_STARTUP', 'StartupDelaySeconds', '30')
            
            print(f"📋 Auto-scan enabled: {enable_scan}")
            print(f"📋 Auto-analysis enabled: {enable_analysis}")
            print(f"📋 Startup delay: {startup_delay} seconds")
            
        else:
            print(f"⚠️  AUTO_STARTUP section not found - will be created when first configured")
            
        # Test default values
        print(f"\n🔍 Testing default values:")
        print(f"   EnableAutoScan (default): {get_config_value('AUTO_STARTUP', 'EnableAutoScan', 'no')}")
        print(f"   EnableAutoAnalysis (default): {get_config_value('AUTO_STARTUP', 'EnableAutoAnalysis', 'no')}")
        print(f"   StartupDelaySeconds (default): {get_config_value('AUTO_STARTUP', 'StartupDelaySeconds', '30')}")
        
        # Test other required configurations
        print(f"\n🔍 Testing other required configs:")
        local_folder = get_config_value('APP', 'LocalMusicFolder', '')
        print(f"   LocalMusicFolder: {local_folder if local_folder else 'Not configured'}")
        
        max_workers = get_config_value('AUDIO_ANALYSIS', 'MaxWorkers', '1')
        batch_size = get_config_value('AUDIO_ANALYSIS', 'BatchSize', '100')
        print(f"   MaxWorkers: {max_workers}")
        print(f"   BatchSize: {batch_size}")
        
        print(f"\n✅ Auto-startup configuration test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error testing auto-startup configuration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_auto_startup_config()
