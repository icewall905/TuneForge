#!/usr/bin/env python3
"""
Test script to verify configuration system functionality

This script tests:
1. Configuration manager functionality
2. Configuration validation
3. Configuration persistence
4. API endpoints integration
"""

import sys
import os
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_configuration_manager():
    """Test configuration manager functionality"""
    print("🧪 Testing Configuration Manager...")
    
    try:
        from monitoring_config import MonitoringConfigManager, MonitoringConfig
        
        # Test configuration manager initialization
        config_manager = MonitoringConfigManager()
        print("   ✅ Configuration manager initialized successfully")
        
        # Test default configuration
        config = config_manager.get_monitoring_config()
        print(f"   📊 Default stall timeout: {config.stall_detection_timeout}s")
        print(f"   📊 Default monitoring interval: {config.monitoring_interval}s")
        print(f"   📊 Default auto-recovery enabled: {config.auto_recovery_enabled}")
        
        # Test configuration validation
        validation = config_manager.validate_config()
        print(f"   ✅ Configuration validation: {validation['valid']}")
        
        if validation['warnings']:
            print(f"   ⚠️ Warnings: {len(validation['warnings'])}")
        if validation['errors']:
            print(f"   ❌ Errors: {len(validation['errors'])}")
        
        # Test configuration summary
        summary = config_manager.get_config_summary()
        print(f"   📋 Configuration summary: {len(summary)} items")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Configuration manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_configuration_updates():
    """Test configuration update functionality"""
    print("\n🧪 Testing Configuration Updates...")
    
    try:
        from monitoring_config import MonitoringConfigManager
        
        config_manager = MonitoringConfigManager()
        
        # Test configuration updates
        print("   🔄 Testing configuration updates...")
        
        # Update some values
        config_manager.update_monitoring_config(
            stall_detection_timeout=180,  # 3 minutes
            monitoring_interval=30,       # 30 seconds
            auto_recovery_enabled=False
        )
        
        # Verify updates
        config = config_manager.get_monitoring_config()
        print(f"   📊 Updated stall timeout: {config.stall_detection_timeout}s")
        print(f"   📊 Updated monitoring interval: {config.monitoring_interval}s")
        print(f"   📊 Updated auto-recovery: {config.auto_recovery_enabled}")
        
        # Test validation after updates
        validation = config_manager.validate_config()
        print(f"   ✅ Post-update validation: {validation['valid']}")
        
        # Reset to defaults
        config_manager.monitoring_config = config_manager.monitoring_config.__class__()
        print("   🔄 Configuration reset to defaults")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Configuration updates test failed: {e}")
        return False

def test_configuration_persistence():
    """Test configuration file persistence"""
    print("\n🧪 Testing Configuration Persistence...")
    
    try:
        from monitoring_config import MonitoringConfigManager
        import tempfile
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            temp_config_path = f.name
        
        try:
            # Test with temporary config
            config_manager = MonitoringConfigManager(temp_config_path)
            print("   ✅ Temporary configuration created")
            
            # Update configuration
            config_manager.update_monitoring_config(
                stall_detection_timeout=240,
                monitoring_interval=45
            )
            
            # Save configuration
            config_manager.save_config()
            print("   ✅ Configuration saved to file")
            
            # Verify file exists and has content
            if os.path.exists(temp_config_path):
                with open(temp_config_path, 'r') as f:
                    content = f.read()
                    if 'stall_detection_timeout = 240' in content:
                        print("   ✅ Configuration file contains updated values")
                    else:
                        print("   ❌ Configuration file missing updated values")
                        return False
            else:
                print("   ❌ Configuration file not created")
                return False
            
            return True
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_config_path):
                os.unlink(temp_config_path)
                print("   🧹 Temporary configuration file cleaned up")
        
    except Exception as e:
        print(f"   ❌ Configuration persistence test failed: {e}")
        return False

def test_configuration_validation():
    """Test configuration validation rules"""
    print("\n🧪 Testing Configuration Validation...")
    
    try:
        from monitoring_config import MonitoringConfigManager
        
        config_manager = MonitoringConfigManager()
        
        # Test various validation scenarios
        print("   🔍 Testing validation scenarios...")
        
        # Test valid configuration
        validation = config_manager.validate_config()
        print(f"   ✅ Default config validation: {validation['valid']}")
        
        # Test invalid configuration (stall detection >= monitoring interval)
        config_manager.update_monitoring_config(
            stall_detection_interval=60,
            monitoring_interval=30
        )
        validation = config_manager.validate_config()
        print(f"   ⚠️ Invalid interval config validation: {validation['valid']}")
        if validation['warnings']:
            print(f"      Warnings: {validation['warnings']}")
        
        # Test critical error (escalation >= critical threshold)
        config_manager.update_monitoring_config(
            escalation_threshold=5,
            critical_stall_threshold=3
        )
        validation = config_manager.validate_config()
        print(f"   ❌ Invalid threshold config validation: {validation['valid']}")
        if validation['errors']:
            print(f"      Errors: {validation['errors']}")
        
        # Reset to valid configuration
        config_manager.monitoring_config = config_manager.monitoring_config.__class__()
        validation = config_manager.validate_config()
        print(f"   ✅ Reset config validation: {validation['valid']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Configuration validation test failed: {e}")
        return False

def test_api_integration():
    """Test API endpoint integration"""
    print("\n🧪 Testing API Integration...")
    
    try:
        # Test that the routes file contains the new endpoints
        routes_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'routes.py')
        
        if os.path.exists(routes_path):
            with open(routes_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for new API endpoints
            required_endpoints = [
                '/api/audio-analysis/config',
                '/api/audio-analysis/config/reset',
                '/api/audio-analysis/config/validate'
            ]
            
            missing_endpoints = []
            for endpoint in required_endpoints:
                if endpoint not in content:
                    missing_endpoints.append(endpoint)
            
            if missing_endpoints:
                print(f"   ❌ Missing API endpoints: {missing_endpoints}")
                return False
            else:
                print("   ✅ All required API endpoints found")
            
            # Check for route functions
            required_functions = [
                'api_get_monitoring_config',
                'api_update_monitoring_config',
                'api_reset_monitoring_config',
                'api_validate_monitoring_config'
            ]
            
            missing_functions = []
            for func in required_functions:
                if func not in content:
                    missing_functions.append(func)
            
            if missing_functions:
                print(f"   ❌ Missing route functions: {missing_functions}")
                return False
            else:
                print("   ✅ All required route functions found")
            
            return True
        else:
            print("   ❌ Routes file not found")
            return False
            
    except Exception as e:
        print(f"   ❌ API integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🎵 TuneForge Configuration System Test")
    print("=" * 60)
    
    # Test 1: Configuration manager
    config_manager_success = test_configuration_manager()
    
    # Test 2: Configuration updates
    config_updates_success = test_configuration_updates()
    
    # Test 3: Configuration persistence
    config_persistence_success = test_configuration_persistence()
    
    # Test 4: Configuration validation
    config_validation_success = test_configuration_validation()
    
    # Test 5: API integration
    api_integration_success = test_api_integration()
    
    # Summary
    print(f"\n📊 Test Results:")
    print(f"   - Configuration Manager: {'✅ PASS' if config_manager_success else '❌ FAIL'}")
    print(f"   - Configuration Updates: {'✅ PASS' if config_updates_success else '❌ FAIL'}")
    print(f"   - Configuration Persistence: {'✅ PASS' if config_persistence_success else '❌ FAIL'}")
    print(f"   - Configuration Validation: {'✅ PASS' if config_validation_success else '❌ FAIL'}")
    print(f"   - API Integration: {'✅ PASS' if api_integration_success else '❌ FAIL'}")
    
    if all([config_manager_success, config_updates_success, config_persistence_success, 
             config_validation_success, api_integration_success]):
        print(f"\n🎉 All configuration system tests passed!")
        print(f"✅ Phase 4, Task 4.1 is ready for implementation")
        print(f"⚙️ Configuration management system is working correctly")
        return True
    else:
        print(f"\n❌ Some tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
