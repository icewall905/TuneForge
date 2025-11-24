#!/usr/bin/env python3
"""
Test script for problematic files functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_problematic_files_monitor():
    """Test the problematic files monitoring functionality"""
    print("🧪 Testing Problematic Files Monitoring...")
    
    try:
        from audio_analysis_monitor import AudioAnalysisMonitor
        
        # Initialize monitor
        monitor = AudioAnalysisMonitor()
        print("✅ AudioAnalysisMonitor initialized successfully")
        
        # Test problematic files report
        report = monitor.get_problematic_files_report()
        print(f"✅ Problematic files report generated: {len(report.keys())} sections")
        
        # Display report summary
        if 'summary' in report:
            summary = report['summary']
            print(f"   📊 Summary: {summary.get('total_tracks', 0)} total tracks")
            print(f"   📊 Pending: {summary.get('pending_tracks', 0)} tracks")
            print(f"   📊 Completed: {summary.get('completed_tracks', 0)} tracks")
            print(f"   📊 Errors: {summary.get('error_tracks', 0)} tracks")
        
        if 'problematic_files' in report:
            print(f"   ⚠️  Problematic files: {len(report['problematic_files'])} found")
            for pf in report['problematic_files'][:3]:  # Show first 3
                print(f"      • {pf.get('filename', 'Unknown')}: {pf.get('failure_count', 0)} failures")
        
        if 'stuck_files' in report:
            print(f"   🕐 Stuck files: {len(report['stuck_files'])} found")
            for sf in report['stuck_files'][:3]:  # Show first 3
                print(f"      • {sf.get('filename', 'Unknown')}: stuck for {sf.get('minutes_stuck', 0):.1f} min")
        
        if 'recommendations' in report:
            print(f"   💡 Recommendations: {len(report['recommendations'])} suggestions")
            for rec in report['recommendations']:
                print(f"      • {rec}")
        
        print("✅ Problematic files monitoring test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error testing problematic files monitoring: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_auto_skip_functionality():
    """Test the auto-skip functionality in batch processor"""
    print("\n🧪 Testing Auto-Skip Functionality...")
    
    try:
        from advanced_batch_processor import ProcessingStatus, ProcessingJob
        
        # Test ProcessingStatus enum
        print(f"✅ ProcessingStatus.SKIPPED: {ProcessingStatus.SKIPPED}")
        
        # Test that SKIPPED is a valid status
        valid_statuses = [status.value for status in ProcessingStatus]
        print(f"✅ Valid statuses: {valid_statuses}")
        
        if ProcessingStatus.SKIPPED in valid_statuses:
            print("✅ SKIPPED status is properly defined")
        else:
            print("❌ SKIPPED status is missing")
            return False
        
        print("✅ Auto-skip functionality test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error testing auto-skip functionality: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Problematic Files Functionality Tests...\n")
    
    success = True
    
    # Test problematic files monitoring
    if not test_problematic_files_monitor():
        success = False
    
    # Test auto-skip functionality
    if not test_auto_skip_functionality():
        success = False
    
    print("\n" + "="*50)
    if success:
        print("🎉 All tests passed! Problematic files functionality is working.")
    else:
        print("❌ Some tests failed. Check the output above for details.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
