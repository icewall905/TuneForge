#!/usr/bin/env python3
"""
Test script to verify Sonic Traveller history save function
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_history_save():
    """Test the history save function"""
    print("🧪 Testing Sonic Traveller History Save Function")
    print("=" * 60)
    
    try:
        from app.routes import _save_sonic_traveller_to_history
        
        # Create a mock job with results
        class MockJob:
            def __init__(self):
                self.job_id = "test_123"
                self.results = [
                    {
                        'id': 1,
                        'title': 'Test Song 1',
                        'artist': 'Test Artist 1',
                        'distance': 0.15,
                        'iteration': 1
                    },
                    {
                        'id': 2,
                        'title': 'Test Song 2',
                        'artist': 'Test Artist 2',
                        'distance': 0.25,
                        'iteration': 1
                    }
                ]
                self.threshold = 0.5
                self.num_songs = 20
                self.ollama_model = 'gemma3:12b'
                self.random_seed = 'test123'
                self.attempts = 3
                self.total_candidates = 100
                self.accepted_examples = [
                    {'title': 'Test Song 1', 'artist': 'Test Artist 1'},
                    {'title': 'Test Song 2', 'artist': 'Test Artist 2'}
                ]
                self.rejected_examples = [
                    {'title': 'Bad Song', 'artist': 'Bad Artist'}
                ]
                self.iteration_history = [
                    {'accepted': [{'title': 'Test Song 1', 'artist': 'Test Artist 1'}]}
                ]
        
        mock_job = MockJob()
        seed_track = {
            'id': 1,
            'title': 'Seed Song',
            'artist': 'Seed Artist',
            'album': 'Seed Album'
        }
        
        print(f"Mock job created with {len(mock_job.results)} results")
        print(f"Current working directory: {os.getcwd()}")
        print(f"History file path: temp/playlist_history.json")
        print(f"History file exists: {os.path.exists('temp/playlist_history.json')}")
        
        # Check current history
        if os.path.exists('temp/playlist_history.json'):
            with open('temp/playlist_history.json', 'r') as f:
                current_history = f.read()
                print(f"Current history file size: {len(current_history)} characters")
                print(f"Current history ends with ']': {current_history.strip().endswith(']')}")
        
        # Test the save function
        print(f"\n🔍 Testing save function...")
        _save_sonic_traveller_to_history(mock_job, seed_track)
        
        # Check if it was saved
        print(f"\n🔍 Checking if save was successful...")
        if os.path.exists('playlist_history.json'):
            with open('playlist_history.json', 'r') as f:
                new_history = f.read()
                print(f"New history file size: {len(new_history)} characters")
                print(f"New history ends with ']': {new_history.strip().endswith(']')}")
                
                # Check if our entry was added
                if 'Sonic Traveller: Seed Artist - Seed Song' in new_history:
                    print("✅ Sonic Traveller entry found in history!")
                else:
                    print("❌ Sonic Traveller entry NOT found in history")
                
                # Validate JSON
                try:
                    import json
                    json.loads(new_history)
                    print("✅ JSON is valid")
                except Exception as e:
                    print(f"❌ JSON is invalid: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_history_save()
    sys.exit(0 if success else 1)
