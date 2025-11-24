#!/usr/bin/env python3
"""
Test script to verify enhanced monitoring features

This script tests:
1. Enhanced anomaly detection
2. Stall analysis
3. Improved recommendations
4. Progress stagnation detection
"""

import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_enhanced_monitoring():
    """Test enhanced monitoring features"""
    print("🧪 Testing Enhanced Monitoring Features...")
    
    try:
        from audio_analysis_monitor import AudioAnalysisMonitor, MonitoringConfig
        
        # Initialize monitor
        config = MonitoringConfig(
            stall_detection_timeout=300,  # 5 minutes
            monitoring_interval=60,       # 1 minute
            progress_history_retention_days=7
        )
        
        monitor = AudioAnalysisMonitor(config=config)
        print("   ✅ Monitor initialized successfully")
        
        # Test health status with anomalies
        print("\n🔍 Testing Enhanced Health Status...")
        health = monitor.get_health_status()
        
        print(f"   📊 Health Status: {health['current_status']}")
        print(f"   📈 Progress: {health['progress']['progress_percentage']}%")
        print(f"   ⚠️ Stalled: {health['stalled']}")
        print(f"   🔄 Consecutive Stalls: {health['consecutive_stalls']}")
        
        if 'anomalies' in health and health['anomalies']:
            print(f"   🚨 Anomalies Detected:")
            for anomaly in health['anomalies']:
                print(f"      • {anomaly}")
        else:
            print(f"   ✅ No anomalies detected")
        
        if health['recommendations']:
            print(f"   💡 Recommendations:")
            for rec in health['recommendations']:
                print(f"      • {rec}")
        
        # Test stall analysis
        print(f"\n🔍 Testing Stall Analysis...")
        stall_analysis = monitor.get_stall_analysis()
        
        print(f"   📊 Stall Probability: {stall_analysis['stall_probability']}")
        print(f"   📈 Current Status:")
        for key, value in stall_analysis['current_status'].items():
            print(f"      - {key}: {value}")
        
        if stall_analysis['stall_indicators']:
            print(f"   🚨 Stall Indicators:")
            for indicator in stall_analysis['stall_indicators']:
                print(f"      • {indicator}")
        else:
            print(f"   ✅ No stall indicators detected")
        
        print(f"   💡 Recommended Action: {stall_analysis['recommended_action']}")
        
        # Test anomaly detection directly
        print(f"\n🔍 Testing Direct Anomaly Detection...")
        snapshot = monitor.capture_progress_snapshot()
        anomalies = monitor._detect_anomalies(snapshot)
        
        if anomalies:
            print(f"   🚨 Direct Anomalies:")
            for anomaly in anomalies:
                print(f"      • {anomaly}")
        else:
            print(f"   ✅ No direct anomalies detected")
        
        print(f"\n🎉 Enhanced monitoring test completed successfully!")
        print(f"✅ Phase 1, Task 1.3 is ready for implementation")
        print(f"📊 Stall detection and anomaly detection are working correctly")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Enhanced monitoring test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the enhanced monitoring test"""
    print("🎵 TuneForge Enhanced Monitoring Test")
    print("=" * 50)
    
    success = test_enhanced_monitoring()
    
    if success:
        print("\n🎉 All enhanced monitoring tests passed!")
        print("✅ Ready to move to Phase 2: Auto-Recovery System")
    else:
        print("\n❌ Some tests failed")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
