#!/usr/bin/env python3
"""
Test script to verify the floating progress indicator integration.
"""

import requests
import json
import time

def test_floating_indicator_integration():
    """Test the floating progress indicator integration"""
    base_url = "http://localhost:5395"
    
    print("🧪 Testing Floating Progress Indicator Integration")
    print("=" * 60)
    
    # Test 1: Check current status
    print("\n1. Checking current audio analysis status...")
    try:
        response = requests.get(f"{base_url}/api/audio-analysis/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   Status: {data.get('status', 'unknown')}")
            if data.get('status') == 'running':
                print("   ✅ Audio analysis is running - floating indicator should be visible!")
            else:
                print("   ⚠️ Audio analysis is not running")
        else:
            print(f"   ❌ Status check failed with status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Status check error: {e}")
    
    # Test 2: Start audio analysis if not running
    print("\n2. Starting audio analysis...")
    try:
        response = requests.post(
            f"{base_url}/api/audio-analysis/start",
            json={
                "max_workers": 2,
                "batch_size": 5,
                "limit": 3
            },
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("   ✅ Analysis started successfully")
                print(f"   Message: {data.get('message', 'No message')}")
                print(f"   Jobs queued: {data.get('jobs_queued', 0)}")
                
                # Wait for processing to begin
                print("   Waiting 3 seconds for processing to begin...")
                time.sleep(3)
                
                # Check status again
                response = requests.get(f"{base_url}/api/audio-analysis/status", timeout=10)
                if response.status_code == 200:
                    status_data = response.json()
                    print(f"   Current status: {status_data.get('status', 'unknown')}")
                    
                    if status_data.get('status') == 'running':
                        print("   🎯 AUDIO ANALYSIS IS RUNNING!")
                        print("   📱 NOW REFRESH YOUR BROWSER PAGE!")
                        print("   🔍 You should see a floating progress indicator in the top-right corner")
                        print("   📊 It should show real-time progress updates")
                    else:
                        print(f"   ⚠️ Analysis status: {status_data.get('status')}")
                else:
                    print("   ❌ Failed to get updated status")
            else:
                print(f"   ❌ Analysis start failed: {data.get('error', 'Unknown error')}")
        else:
            print(f"   ❌ Analysis start failed with status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Analysis start error: {e}")
    
    # Test 3: Check progress
    print("\n3. Checking analysis progress...")
    try:
        response = requests.get(f"{base_url}/api/audio-analysis/progress", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                progress = data.get('progress', {})
                total = progress.get('total_tracks', 0)
                analyzed = progress.get('analyzed_tracks', 0)
                print(f"   Progress: {analyzed}/{total} tracks analyzed")
                if total > 0:
                    percentage = (analyzed / total) * 100
                    print(f"   Percentage: {percentage:.1f}%")
            else:
                print(f"   ❌ Progress check failed: {data.get('error', 'Unknown error')}")
        else:
            print(f"   ❌ Progress check failed with status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Progress check error: {e}")
    
    print("\n🎯 TEST INSTRUCTIONS:")
    print("1. Make sure audio analysis is running (status should be 'running')")
    print("2. Open your browser and go to http://localhost:5395")
    print("3. Look for a floating progress indicator in the top-right corner")
    print("4. The indicator should show audio analysis progress with purple theme")
    print("5. If you don't see it, check the browser console for errors")
    print("\n🔧 TROUBLESHOOTING:")
    print("- Check browser console for JavaScript errors")
    print("- Verify that window.globalStatusManager is defined")
    print("- Look for 'Found running audio analysis' logs in console")
    print("- Ensure the page has loaded completely before checking")

if __name__ == "__main__":
    test_floating_indicator_integration()
