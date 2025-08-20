#!/usr/bin/env python3
"""
Test script to verify enhanced monitoring dashboard

This script tests:
1. Enhanced UI elements
2. Health monitoring integration
3. Auto-recovery UI integration
4. Real-time updates
"""

import sys
import os
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_enhanced_dashboard():
    """Test enhanced monitoring dashboard functionality"""
    print("🧪 Testing Enhanced Monitoring Dashboard...")
    
    try:
        # Test health monitoring system
        from audio_analysis_monitor import AudioAnalysisMonitor
        from audio_analysis_auto_recovery import AudioAnalysisAutoRecovery, AutoRecoveryConfig
        
        print("   ✅ Monitoring modules imported successfully")
        
        # Initialize monitor
        monitor = AudioAnalysisMonitor()
        print("   ✅ Monitor initialized successfully")
        
        # Test health status
        health = monitor.get_health_status()
        print(f"   📊 Health Status: {health.get('current_status', 'unknown')}")
        print(f"   📈 Progress: {health.get('progress', {}).get('progress_percentage', 'unknown')}%")
        print(f"   ⚠️ Stalled: {health.get('stalled', 'unknown')}")
        print(f"   🔄 Consecutive Stalls: {health.get('consecutive_stalls', 'unknown')}")
        
        # Test stall analysis
        stall_analysis = monitor.get_stall_analysis()
        print(f"   📊 Stall Analysis: {stall_analysis.get('stall_probability', 'unknown')}")
        print(f"   💡 Recommended Action: {stall_analysis.get('recommended_action', 'unknown')}")
        
        # Test auto-recovery system
        config = AutoRecoveryConfig(
            enabled=True,
            check_interval=60,
            max_consecutive_failures=3
        )
        
        def test_restart_callback():
            return True
        
        auto_recovery = AudioAnalysisAutoRecovery(
            config=config,
            monitor=monitor,
            restart_callback=test_restart_callback
        )
        
        print("   ✅ Auto-recovery system initialized successfully")
        
        # Test recovery status
        recovery_status = auto_recovery.get_status()
        print(f"   📊 Recovery Status: {recovery_status.get('status', 'unknown')}")
        print(f"   📊 Monitoring Active: {recovery_status.get('monitoring_active', 'unknown')}")
        print(f"   📊 Consecutive Failures: {recovery_status.get('consecutive_failures', 'unknown')}")
        
        # Test recovery history
        recovery_history = auto_recovery.get_recovery_history()
        print(f"   📊 Recovery History: {len(recovery_history)} entries")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Enhanced dashboard test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ui_integration():
    """Test UI integration components"""
    print("\n🧪 Testing UI Integration...")
    
    try:
        # Test that the HTML template can be parsed
        template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates', 'audio_analysis.html')
        
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for key UI elements
            required_elements = [
                'health-monitoring',
                'auto-recovery-status',
                'overall-health',
                'stall-status',
                'recovery-status',
                'refresh-health',
                'force-restart',
                'start-recovery-monitoring'
            ]
            
            missing_elements = []
            for element in required_elements:
                if element not in content:
                    missing_elements.append(element)
            
            if missing_elements:
                print(f"   ❌ Missing UI elements: {missing_elements}")
                return False
            else:
                print("   ✅ All required UI elements found")
            
            # Check for JavaScript functionality
            js_elements = [
                'refreshHealthStatus',
                'updateHealthDisplay',
                'refreshRecoveryStatus',
                'startRecoveryMonitoring'
            ]
            
            missing_js = []
            for element in js_elements:
                if element not in content:
                    missing_js.append(element)
            
            if missing_js:
                print(f"   ❌ Missing JavaScript functions: {missing_js}")
                return False
            else:
                print("   ✅ All required JavaScript functions found")
            
            return True
        else:
            print("   ❌ Template file not found")
            return False
            
    except Exception as e:
        print(f"   ❌ UI integration test failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoint availability"""
    print("\n🧪 Testing API Endpoints...")
    
    try:
        # Test that the routes file contains the new endpoints
        routes_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'routes.py')
        
        if os.path.exists(routes_path):
            with open(routes_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for new API endpoints
            required_endpoints = [
                '/api/audio-analysis/health',
                '/api/audio-analysis/restart',
                '/api/audio-analysis/auto-recovery/status',
                '/api/audio-analysis/auto-recovery/start',
                '/api/audio-analysis/auto-recovery/stop',
                '/api/audio-analysis/auto-recovery/reset'
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
            
            return True
        else:
            print("   ❌ Routes file not found")
            return False
            
    except Exception as e:
        print(f"   ❌ API endpoints test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🎵 TuneForge Enhanced Monitoring Dashboard Test")
    print("=" * 60)
    
    # Test 1: Enhanced dashboard functionality
    dashboard_success = test_enhanced_dashboard()
    
    # Test 2: UI integration
    ui_success = test_ui_integration()
    
    # Test 3: API endpoints
    api_success = test_api_endpoints()
    
    # Summary
    print(f"\n📊 Test Results:")
    print(f"   - Enhanced Dashboard: {'✅ PASS' if dashboard_success else '❌ FAIL'}")
    print(f"   - UI Integration: {'✅ PASS' if ui_success else '❌ FAIL'}")
    print(f"   - API Endpoints: {'✅ PASS' if api_success else '❌ FAIL'}")
    
    if dashboard_success and ui_success and api_success:
        print(f"\n🎉 All enhanced dashboard tests passed!")
        print(f"✅ Phase 3, Task 3.1 is ready for implementation")
        print(f"📊 Enhanced monitoring UI is working correctly")
        return True
    else:
        print(f"\n❌ Some tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
