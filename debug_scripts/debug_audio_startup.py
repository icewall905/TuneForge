#!/usr/bin/env python3
"""
Debug script for audio analysis startup
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def debug_audio_startup():
    """Debug the audio analysis startup step by step"""
    print("🔧 Debugging Audio Analysis Startup")
    print("=" * 50)
    
    try:
        # Test 1: Import AudioAnalysisService
        print("\n📦 Test 1: Importing AudioAnalysisService...")
        try:
            from audio_analysis_service import AudioAnalysisService
            print("   ✅ AudioAnalysisService imported successfully")
        except ImportError as e:
            print(f"   ❌ Failed to import AudioAnalysisService: {e}")
            return False
        
        # Test 2: Initialize service
        print("\n🔧 Test 2: Initializing AudioAnalysisService...")
        try:
            service = AudioAnalysisService()
            print("   ✅ AudioAnalysisService initialized successfully")
        except Exception as e:
            print(f"   ❌ Failed to initialize AudioAnalysisService: {e}")
            return False
        
        # Test 3: Check pending tracks
        print("\n📊 Test 3: Checking pending tracks...")
        try:
            pending_tracks = service.get_pending_tracks(limit=1000)
            print(f"   ✅ Found {len(pending_tracks)} pending tracks")
        except Exception as e:
            print(f"   ❌ Failed to get pending tracks: {e}")
            return False
        
        # Test 4: Test start_analysis method
        print("\n🚀 Test 4: Testing start_analysis method...")
        try:
            processor = service.start_analysis(max_workers=1, batch_size=100)
            if processor:
                print("   ✅ start_analysis returned processor successfully")
            else:
                print("   ❌ start_analysis returned None")
                return False
        except Exception as e:
            print(f"   ❌ start_analysis failed: {e}")
            return False
        
        print("\n🎉 All tests passed! Audio analysis startup should work.")
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_audio_startup()
