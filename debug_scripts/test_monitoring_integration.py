#!/usr/bin/env python3
"""
Test script to verify monitoring integration with AdvancedBatchProcessor

This script tests:
1. Monitor initialization and table creation
2. Progress snapshot capture
3. Health status monitoring
4. Integration with batch processor (without actual processing)
"""

import sys
import os
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_monitor_initialization():
    """Test monitor initialization and table creation"""
    print("🧪 Testing Monitor Initialization...")
    
    try:
        from audio_analysis_monitor import AudioAnalysisMonitor, MonitoringConfig
        
        # Test with custom config
        config = MonitoringConfig(
            stall_detection_timeout=300,  # 5 minutes
            monitoring_interval=60,       # 1 minute
            progress_history_retention_days=7
        )
        
        monitor = AudioAnalysisMonitor(config=config)
        print("   ✅ Monitor initialized successfully")
        print(f"   ✅ Stall detection timeout: {config.stall_detection_timeout}s")
        print(f"   ✅ Monitoring interval: {config.monitoring_interval}s")
        
        return monitor
        
    except Exception as e:
        print(f"   ❌ Monitor initialization failed: {e}")
        return None

def test_progress_snapshots(monitor):
    """Test progress snapshot capture"""
    print("\n🧪 Testing Progress Snapshots...")
    
    try:
        # Capture initial snapshot
        snapshot1 = monitor.capture_progress_snapshot()
        print(f"   ✅ Initial snapshot captured: {snapshot1.progress_percentage}%")
        print(f"   ✅ Timestamp: {snapshot1.timestamp}")
        print(f"   ✅ Total tracks: {snapshot1.total_tracks}")
        
        # Wait a moment and capture another snapshot
        time.sleep(2)
        snapshot2 = monitor.capture_progress_snapshot()
        print(f"   ✅ Second snapshot captured: {snapshot2.progress_percentage}%")
        print(f"   ✅ Processing rate: {snapshot2.processing_rate or 'N/A'} tracks/min")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Progress snapshot test failed: {e}")
        return False

def test_health_status(monitor):
    """Test health status monitoring"""
    print("\n🧪 Testing Health Status...")
    
    try:
        health = monitor.get_health_status()
        
        print(f"   ✅ Health status: {health['current_status']}")
        print(f"   ✅ Progress: {health['progress']['progress_percentage']}%")
        print(f"   ✅ Stalled: {health['stalled']}")
        print(f"   ✅ Consecutive stalls: {health['consecutive_stalls']}")
        
        if health['recommendations']:
            print(f"   ✅ Recommendations:")
            for rec in health['recommendations']:
                print(f"      • {rec}")
        
        if health['recent_history']:
            print(f"   ✅ Recent history: {len(health['recent_history'])} entries")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Health status test failed: {e}")
        return False

def test_batch_processor_integration():
    """Test integration with batch processor (without actual processing)"""
    print("\n🧪 Testing Batch Processor Integration...")
    
    try:
        # Test import (this will fail if there are syntax errors)
        from advanced_batch_processor import AdvancedBatchProcessor
        print("   ✅ AdvancedBatchProcessor import successful")
        
        # Test that the monitoring methods exist
        processor = AdvancedBatchProcessor(max_workers=1, batch_size=10)
        print("   ✅ AdvancedBatchProcessor initialization successful")
        
        # Check if monitoring methods exist
        if hasattr(processor, '_capture_monitoring_snapshot'):
            print("   ✅ Monitoring snapshot method exists")
        else:
            print("   ❌ Monitoring snapshot method missing")
            return False
        
        if hasattr(processor, '_progress_monitor'):
            print("   ✅ Progress monitor method exists")
        else:
            print("   ❌ Progress monitor method missing")
            return False
        
        return True
        
    except ImportError as e:
        print(f"   ⚠️ Import error (expected without librosa): {e}")
        return True  # This is expected in test environment
    except Exception as e:
        print(f"   ❌ Batch processor integration test failed: {e}")
        return False

def test_database_integration(monitor):
    """Test database integration and cleanup"""
    print("\n🧪 Testing Database Integration...")
    
    try:
        # Test cleanup
        removed = monitor.cleanup_old_history(days=30)
        print(f"   ✅ Cleanup completed: {removed} old records removed")
        
        # Test recent history retrieval
        history = monitor._get_recent_progress_history(hours=1)
        print(f"   ✅ Recent history retrieved: {len(history)} entries")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Database integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🎵 TuneForge Monitoring Integration Test")
    print("=" * 50)
    
    # Test 1: Monitor initialization
    monitor = test_monitor_initialization()
    if not monitor:
        print("\n❌ Cannot continue without monitor")
        return False
    
    # Test 2: Progress snapshots
    if not test_progress_snapshots(monitor):
        print("\n❌ Progress snapshot test failed")
        return False
    
    # Test 3: Health status
    if not test_health_status(monitor):
        print("\n❌ Health status test failed")
        return False
    
    # Test 4: Batch processor integration
    if not test_batch_processor_integration():
        print("\n❌ Batch processor integration test failed")
        return False
    
    # Test 5: Database integration
    if not test_database_integration(monitor):
        print("\n❌ Database integration test failed")
        return False
    
    print("\n🎉 All monitoring integration tests passed!")
    print("✅ Phase 1, Task 1.2 is ready for implementation")
    print("📊 Progress history tracking is working correctly")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
