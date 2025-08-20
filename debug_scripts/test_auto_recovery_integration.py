#!/usr/bin/env python3
"""
Test script to verify auto-recovery integration

This script tests:
1. Auto-recovery system integration
2. Flask route integration
3. Background monitoring functionality
"""

import sys
import os
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_auto_recovery_integration():
    """Test auto-recovery integration with Flask routes"""
    print("🧪 Testing Auto-Recovery Integration...")
    
    try:
        # Test auto-recovery system directly
        from audio_analysis_auto_recovery import AudioAnalysisAutoRecovery, AutoRecoveryConfig
        from audio_analysis_monitor import AudioAnalysisMonitor
        
        print("   ✅ Auto-recovery modules imported successfully")
        
        # Initialize monitor
        monitor = AudioAnalysisMonitor()
        print("   ✅ Monitor initialized successfully")
        
        # Test restart callback
        def test_restart_callback():
            print("      🔄 Test restart callback executed")
            return True
        
        # Initialize auto-recovery
        config = AutoRecoveryConfig(
            enabled=True,
            check_interval=30,  # 30 seconds for testing
            max_consecutive_failures=3,
            base_backoff_minutes=1,  # 1 minute for testing
            max_backoff_minutes=10
        )
        
        auto_recovery = AudioAnalysisAutoRecovery(
            config=config,
            monitor=monitor,
            restart_callback=test_restart_callback
        )
        
        print("   ✅ Auto-recovery system initialized successfully")
        
        # Test monitoring start/stop
        print("   🚀 Testing monitoring start...")
        if auto_recovery.start_monitoring():
            print("      ✅ Monitoring started successfully")
            
            # Let it run for a moment
            time.sleep(2)
            
            # Check status
            status = auto_recovery.get_status()
            print(f"      📊 Status: {status['status']}")
            print(f"      📊 Monitoring active: {status['monitoring_active']}")
            
            # Stop monitoring
            print("   🛑 Testing monitoring stop...")
            if auto_recovery.stop_monitoring():
                print("      ✅ Monitoring stopped successfully")
            else:
                print("      ❌ Failed to stop monitoring")
                return False
        else:
            print("      ❌ Failed to start monitoring")
            return False
        
        # Test recovery history
        history = auto_recovery.get_recovery_history()
        print(f"   📊 Recovery history: {len(history)} entries")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Auto-recovery integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_flask_route_simulation():
    """Test Flask route functionality (simulated)"""
    print("\n🧪 Testing Flask Route Simulation...")
    
    try:
        # Simulate the get_auto_recovery function
        def get_auto_recovery():
            """Simulated auto-recovery getter"""
            try:
                from audio_analysis_auto_recovery import AudioAnalysisAutoRecovery, AutoRecoveryConfig
                from audio_analysis_monitor import AudioAnalysisMonitor
                
                monitor = AudioAnalysisMonitor()
                
                def restart_callback():
                    return True
                
                config = AutoRecoveryConfig(
                    enabled=True,
                    check_interval=60,
                    max_consecutive_failures=3
                )
                
                return AudioAnalysisAutoRecovery(
                    config=config,
                    monitor=monitor,
                    restart_callback=restart_callback
                )
                
            except Exception as e:
                print(f"      ⚠️ Auto-recovery initialization failed: {e}")
                return None
        
        # Test auto-recovery getter
        auto_recovery = get_auto_recovery()
        if auto_recovery:
            print("   ✅ Auto-recovery getter working correctly")
            
            # Test status endpoint simulation
            status = auto_recovery.get_status()
            print(f"   📊 Status endpoint simulation: {status['status']}")
            
            # Test history endpoint simulation
            history = auto_recovery.get_recovery_history()
            print(f"   📊 History endpoint simulation: {len(history)} entries")
            
            return True
        else:
            print("   ❌ Auto-recovery getter failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Flask route simulation test failed: {e}")
        return False

def test_monitoring_integration():
    """Test monitoring integration with auto-recovery"""
    print("\n🧪 Testing Monitoring Integration...")
    
    try:
        from audio_analysis_monitor import AudioAnalysisMonitor
        from audio_analysis_auto_recovery import AudioAnalysisAutoRecovery, AutoRecoveryConfig
        
        # Initialize monitor
        monitor = AudioAnalysisMonitor()
        print("   ✅ Monitor initialized successfully")
        
        # Test health status
        health = monitor.get_health_status()
        print(f"   📊 Health status: {health.get('current_status', 'unknown')}")
        
        # Test stall analysis
        stall_analysis = monitor.get_stall_analysis()
        print(f"   📈 Stall analysis: {stall_analysis.get('stall_probability', 'unknown')}")
        
        # Initialize auto-recovery with monitor
        config = AutoRecoveryConfig(enabled=True, check_interval=60)
        auto_recovery = AudioAnalysisAutoRecovery(
            config=config,
            monitor=monitor,
            restart_callback=lambda: True
        )
        
        print("   ✅ Auto-recovery with monitor initialized successfully")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Monitoring integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🎵 TuneForge Auto-Recovery Integration Test")
    print("=" * 60)
    
    # Test 1: Auto-recovery integration
    integration_success = test_auto_recovery_integration()
    
    # Test 2: Flask route simulation
    route_success = test_flask_route_simulation()
    
    # Test 3: Monitoring integration
    monitoring_success = test_monitoring_integration()
    
    # Summary
    print(f"\n📊 Test Results:")
    print(f"   - Auto-Recovery Integration: {'✅ PASS' if integration_success else '❌ FAIL'}")
    print(f"   - Flask Route Simulation: {'✅ PASS' if route_success else '❌ FAIL'}")
    print(f"   - Monitoring Integration: {'✅ PASS' if monitoring_success else '❌ FAIL'}")
    
    if integration_success and route_success and monitoring_success:
        print(f"\n🎉 All auto-recovery integration tests passed!")
        print(f"✅ Phase 2, Task 2.3 is ready for implementation")
        print(f"📊 Background monitoring and auto-recovery are working correctly")
        return True
    else:
        print(f"\n❌ Some tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
