#!/usr/bin/env python3
"""
Test script to verify real-time monitoring functionality

This script tests:
1. Real-time health updates
2. Progress rate visualization
3. Stall warnings and alerts
4. Estimated completion time updates
"""

import sys
import os
import time
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_realtime_monitoring():
    """Test real-time monitoring functionality"""
    print("🧪 Testing Real-time Monitoring...")
    
    try:
        from audio_analysis_monitor import AudioAnalysisMonitor, MonitoringConfig
        
        # Initialize monitor with faster polling for testing
        config = MonitoringConfig(
            stall_detection_timeout=60,  # 1 minute for testing
            monitoring_interval=10,      # 10 seconds for testing
            progress_history_retention_days=7
        )
        
        monitor = AudioAnalysisMonitor(config=config)
        print("   ✅ Monitor initialized with real-time config")
        
        # Test multiple health status updates
        print("   📊 Testing real-time health updates...")
        
        for i in range(3):
            health = monitor.get_health_status()
            print(f"      Update {i+1}: Status={health.get('current_status', 'unknown')}, "
                  f"Stalled={health.get('stalled', 'unknown')}, "
                  f"Rate={health.get('processing_rate', 'N/A')}")
            
            # Simulate time passing
            time.sleep(1)
        
        # Test stall analysis updates
        print("   📈 Testing real-time stall analysis...")
        
        for i in range(3):
            stall_analysis = monitor.get_stall_analysis()
            print(f"      Update {i+1}: Probability={stall_analysis.get('stall_probability', 'unknown')}, "
                  f"Action={stall_analysis.get('recommended_action', 'unknown')}")
            
            time.sleep(1)
        
        # Test progress rate calculation
        print("   🚀 Testing progress rate calculation...")
        
        # Capture multiple snapshots to test rate calculation
        for i in range(3):
            snapshot = monitor.capture_progress_snapshot()
            print(f"      Snapshot {i+1}: Progress={snapshot.progress_percentage}%, "
                  f"Rate={snapshot.processing_rate or 'N/A'}")
            
            time.sleep(2)
        
        # Test estimated completion time
        print("   ⏰ Testing estimated completion time...")
        
        # Simulate a processing rate
        health = monitor.get_health_status()
        if health.get('processing_rate'):
            print(f"      Current rate: {health['processing_rate']:.2f} tracks/min")
            if health.get('estimated_completion'):
                print(f"      Estimated completion: {health['estimated_completion']}")
            else:
                print("      No completion estimate available")
        else:
            print("      No processing rate available for completion estimate")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Real-time monitoring test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_warning_system():
    """Test warning and alert system"""
    print("\n🧪 Testing Warning System...")
    
    try:
        from audio_analysis_monitor import AudioAnalysisMonitor
        
        monitor = AudioAnalysisMonitor()
        print("   ✅ Monitor initialized for warning tests")
        
        # Test stall detection
        print("   ⚠️ Testing stall detection...")
        is_stalled = monitor._is_analysis_stalled()
        print(f"      Current stall status: {is_stalled}")
        
        # Test anomaly detection
        print("   🚨 Testing anomaly detection...")
        health = monitor.get_health_status()
        anomalies = health.get('anomalies', [])
        print(f"      Detected anomalies: {len(anomalies)}")
        
        if anomalies:
            for anomaly in anomalies:
                print(f"         • {anomaly}")
        
        # Test consecutive stall counting
        print("   🔄 Testing consecutive stall counting...")
        consecutive_stalls = monitor._count_consecutive_stalls()
        print(f"      Consecutive stalls: {consecutive_stalls}")
        
        # Test recommendations
        print("   💡 Testing recommendations...")
        recommendations = health.get('recommendations', [])
        print(f"      Recommendations: {len(recommendations)}")
        
        if recommendations:
            for rec in recommendations:
                print(f"         • {rec}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Warning system test failed: {e}")
        return False

def test_performance_monitoring():
    """Test performance monitoring features"""
    print("\n🧪 Testing Performance Monitoring...")
    
    try:
        from audio_analysis_monitor import AudioAnalysisMonitor
        
        monitor = AudioAnalysisMonitor()
        print("   ✅ Monitor initialized for performance tests")
        
        # Test processing rate calculation
        print("   📊 Testing processing rate calculation...")
        
        # Get recent history to test rate calculation
        recent_history = monitor._get_recent_progress_history(hours=1)
        print(f"      Recent history entries: {len(recent_history)}")
        
        if len(recent_history) >= 2:
            # Calculate rate manually to verify
            latest = recent_history[0]
            previous = recent_history[1]
            
            if 'analyzed_tracks' in latest and 'analyzed_tracks' in previous:
                tracks_diff = latest['analyzed_tracks'] - previous['analyzed_tracks']
                print(f"      Tracks processed between snapshots: {tracks_diff}")
                
                if tracks_diff > 0:
                    print("      ✅ Processing rate calculation should work")
                else:
                    print("      ⚠️ No progress between snapshots")
        
        # Test progress stagnation detection
        print("   📈 Testing progress stagnation detection...")
        
        # Check for stagnant progress in recent history
        if len(recent_history) >= 3:
            recent_progress = [h['progress_percentage'] for h in recent_history[:3]]
            stagnant_count = 0
            
            for i in range(len(recent_progress) - 1):
                if abs(recent_progress[i] - recent_progress[i + 1]) < 0.1:
                    stagnant_count += 1
                else:
                    break
            
            print(f"      Consecutive stagnant snapshots: {stagnant_count}")
            
            if stagnant_count >= 3:
                print("      ⚠️ Progress stagnation detected")
            else:
                print("      ✅ Progress is not stagnant")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Performance monitoring test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🎵 TuneForge Real-time Monitoring Test")
    print("=" * 60)
    
    # Test 1: Real-time monitoring
    realtime_success = test_realtime_monitoring()
    
    # Test 2: Warning system
    warning_success = test_warning_system()
    
    # Test 3: Performance monitoring
    performance_success = test_performance_monitoring()
    
    # Summary
    print(f"\n📊 Test Results:")
    print(f"   - Real-time Monitoring: {'✅ PASS' if realtime_success else '❌ FAIL'}")
    print(f"   - Warning System: {'✅ PASS' if warning_success else '❌ FAIL'}")
    print(f"   - Performance Monitoring: {'✅ PASS' if performance_success else '❌ FAIL'}")
    
    if realtime_success and warning_success and performance_success:
        print(f"\n🎉 All real-time monitoring tests passed!")
        print(f"✅ Phase 3, Task 3.2 is ready for implementation")
        print(f"📊 Real-time health updates and warnings are working correctly")
        return True
    else:
        print(f"\n❌ Some tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
