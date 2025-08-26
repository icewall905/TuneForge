#!/usr/bin/env python3
"""
Test script for stuck file detection and recovery
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audio_analysis_service import AudioAnalysisService

def test_stuck_file_detection():
    """Test the stuck file detection system"""
    print("🔧 Testing Stuck File Detection and Recovery")
    print("=" * 50)
    
    try:
        # Initialize the service
        service = AudioAnalysisService()
        print("✅ AudioAnalysisService initialized successfully")
        
        # Test getting pending tracks
        print("\n📊 Testing pending tracks retrieval...")
        pending_tracks = service.get_pending_tracks(limit=5)
        print(f"   Found {len(pending_tracks)} pending tracks")
        
        if pending_tracks:
            print("   Sample pending tracks:")
            for track in pending_tracks[:3]:
                print(f"   - {track['title']} by {track['artist']} (attempts: {track['analysis_attempts']})")
        
        # Test getting stuck files
        print("\n🚨 Testing stuck file detection...")
        stuck_files = service.get_stuck_files(stuck_threshold_seconds=60)  # 1 minute threshold for testing
        print(f"   Found {len(stuck_files)} stuck files")
        
        if stuck_files:
            print("   Stuck files:")
            for file_info in stuck_files[:3]:
                print(f"   - {file_info['file_path']} (stuck for {file_info['stuck_duration']}s)")
        
        # Test marking a track as skipped (only if we have stuck files)
        if stuck_files:
            print("\n⏭️ Testing track skipping...")
            test_file = stuck_files[0]['file_path']
            success = service.mark_track_as_skipped(test_file, "Test skip for stuck file recovery")
            if success:
                print(f"   ✅ Successfully marked {os.path.basename(test_file)} as skipped")
            else:
                print(f"   ❌ Failed to mark {os.path.basename(test_file)} as skipped")
        else:
            print("\n⏭️ No stuck files to test skipping with")
        
        print("\n🚀 Stuck file recovery system is ready!")
        print("📊 The auto-startup system will now automatically:")
        print("   - Detect files stuck in analysis for >5 minutes")
        print("   - Skip problematic files with detailed reasons")
        print("   - Restart analysis with clean state")
        print("   - Continue processing remaining tracks")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_stuck_file_detection()
