#!/usr/bin/env python3
"""
Debug live Sonic Traveller generation to see what's happening
"""

import sys
import os
import time
import requests
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def debug_live_generation():
    """Start a Sonic Traveller generation and monitor it in real-time"""
    print("🔍 Debugging Live Sonic Traveller Generation")
    print("=" * 60)
    
    try:
        # Test the API endpoints directly
        base_url = "http://localhost:5395"
        
        print("1. Testing API connectivity...")
        try:
            response = requests.get(f"{base_url}/api/local-search?q=test", timeout=5)
            if response.status_code == 200:
                print("✅ API is accessible")
            else:
                print(f"❌ API returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot connect to API: {e}")
            print("   Make sure the Flask app is running on port 5395")
            return False
        
        # Start a generation job
        print("\n2. Starting Sonic Traveller generation...")
        start_payload = {
            "seed_track_id": 1,  # Use track ID 1
            "num_songs": 5,      # Small number for testing
            "threshold": 1.0,    # High threshold to ensure matches
            "ollama_model": "gemma3:12b"
        }
        
        try:
            response = requests.post(f"{base_url}/api/sonic/start", json=start_payload, timeout=10)
            if response.status_code == 200:
                job_data = response.json()
                job_id = job_data.get('job_id')
                print(f"✅ Generation started! Job ID: {job_id}")
            else:
                print(f"❌ Failed to start generation: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error starting generation: {e}")
            return False
        
        # Monitor the job
        print(f"\n3. Monitoring job {job_id}...")
        max_attempts = 30  # 30 seconds max
        
        for attempt in range(max_attempts):
            try:
                response = requests.get(f"{base_url}/api/sonic/status?job_id={job_id}", timeout=5)
                if response.status_code == 200:
                    job_status = response.json()
                    job = job_status.get('job', {})
                    
                    status = job.get('status', 'unknown')
                    progress = job.get('progress', 0)
                    current_step = job.get('current_step', 'Unknown')
                    attempts = job.get('attempts', 0)
                    total_candidates = job.get('total_candidates', 0)
                    accepted_tracks = job.get('accepted_tracks', 0)
                    random_seed = job.get('random_seed', 'N/A')
                    
                    print(f"   [{attempt+1:2d}] Status: {status}, Progress: {progress:.1f}%, Step: {current_step}")
                    print(f"       Iterations: {attempts}, Candidates: {total_candidates}, Accepted: {accepted_tracks}")
                    print(f"       Random Seed: {random_seed}")
                    
                    if status in ['completed', 'failed', 'stopped']:
                        print(f"\n✅ Job finished with status: {status}")
                        if status == 'completed':
                            results = job.get('results', [])
                            print(f"   Generated {len(results)} tracks:")
                            for i, track in enumerate(results[:5]):  # Show first 5
                                distance = track.get('distance', 'N/A')
                                print(f"     {i+1}. {track['artist']} - {track['title']} (d={distance})")
                        elif status == 'failed':
                            error = job.get('error', 'Unknown error')
                            print(f"   Error: {error}")
                        break
                    
                    time.sleep(1)  # Wait 1 second between checks
                    
                else:
                    print(f"   ❌ Status check failed: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Error checking status: {e}")
            
            if attempt == max_attempts - 1:
                print(f"\n⏰ Timeout after {max_attempts} seconds")
                break
        
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_live_generation()
    sys.exit(0 if success else 1)
