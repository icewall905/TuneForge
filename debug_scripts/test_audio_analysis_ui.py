#!/usr/bin/env python3
"""
Test script to verify audio analysis UI integration.
"""

import requests
import json
import time

def test_audio_analysis_ui():
    """Test the audio analysis UI integration"""
    base_url = "http://localhost:5395"
    
    print("🧪 Testing Audio Analysis UI Integration")
    print("=" * 50)
    
    # Test 1: Check if the page loads
    print("\n1. Testing page load...")
    try:
        response = requests.get(f"{base_url}/audio-analysis", timeout=10)
        if response.status_code == 200:
            print("✅ Audio analysis page loads successfully")
        else:
            print(f"❌ Page load failed with status {response.status_code}")
    except Exception as e:
        print(f"❌ Page load error: {e}")
    
    # Test 2: Check API endpoints
    print("\n2. Testing API endpoints...")
    
    # Progress endpoint
    try:
        response = requests.get(f"{base_url}/api/audio-analysis/progress", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                progress = data.get('progress', {})
                print(f"✅ Progress API: {progress.get('analyzed_tracks', 0)}/{progress.get('total_tracks', 0)} tracks analyzed")
            else:
                print(f"❌ Progress API error: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ Progress API failed with status {response.status_code}")
    except Exception as e:
        print(f"❌ Progress API error: {e}")
    
    # Status endpoint
    try:
        response = requests.get(f"{base_url}/api/audio-analysis/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status API: {data.get('status', 'unknown')}")
        else:
            print(f"❌ Status API failed with status {response.status_code}")
    except Exception as e:
        print(f"❌ Status API error: {e}")
    
    # Test 3: Test start analysis (this will trigger the floating progress indicator)
    print("\n3. Testing start analysis...")
    try:
        response = requests.post(
            f"{base_url}/api/audio-analysis/start",
            json={
                "max_workers": 2,
                "batch_size": 10,
                "limit": 5  # Only process 5 tracks for testing
            },
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ Analysis started successfully")
                print(f"   Message: {data.get('message', 'No message')}")
                print(f"   Jobs queued: {data.get('jobs_queued', 0)}")
                
                # Wait a moment for processing to start
                print("   Waiting 3 seconds for processing to begin...")
                time.sleep(3)
                
                # Check status again
                response = requests.get(f"{base_url}/api/audio-analysis/status", timeout=10)
                if response.status_code == 200:
                    status_data = response.json()
                    print(f"   Current status: {status_data.get('status', 'unknown')}")
                    
                    if status_data.get('status') == 'running':
                        print("   ✅ Analysis is running - floating progress indicator should be visible!")
                    else:
                        print(f"   ⚠️ Analysis status: {status_data.get('status')}")
                else:
                    print("   ❌ Failed to get updated status")
                
            else:
                print(f"❌ Analysis start failed: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ Analysis start failed with status {response.status_code}")
    except Exception as e:
        print(f"❌ Analysis start error: {e}")
    
    print("\n🎯 Test Summary:")
    print("If the analysis started successfully, you should now see:")
    print("1. A floating progress indicator in the top-right corner")
    print("2. Real-time updates of the analysis progress")
    print("3. The ability to stop the analysis from the floating indicator")
    print("\nCheck your browser to see the floating progress indicator!")

if __name__ == "__main__":
    test_audio_analysis_ui()
