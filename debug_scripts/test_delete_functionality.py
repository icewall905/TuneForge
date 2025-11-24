#!/usr/bin/env python3
"""
Quick test for delete functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_delete_functionality():
    """Test the delete API endpoint"""
    print("🧪 Testing Delete Functionality")
    print("=" * 50)
    
    try:
        from app.routes import api_delete_playlist, load_playlist_history, save_playlist_history
        
        # Check current history
        history = load_playlist_history()
        print(f"Current history: {len(history)} playlists")
        
        if len(history) == 0:
            print("❌ No playlists in history to test with")
            return False
        
        # Show first playlist
        first_playlist = history[0]
        print(f"First playlist: {first_playlist.get('name', 'Unknown')}")
        
        # Test the delete function directly
        print(f"\n🔍 Testing delete function...")
        
        # Create a mock request context
        from flask import Flask
        from app.routes import main_bp
        
        app = Flask(__name__)
        app.register_blueprint(main_bp)
        
        with app.test_client() as client:
            # Test delete with valid index
            response = client.post('/api/history/delete', 
                                json={'playlist_index': 0, 'playlist_id': 'test'})
            
            if response.status_code == 200:
                data = response.get_json()
                print(f"✅ Delete API working: {data}")
            else:
                print(f"❌ Delete API failed: {response.status_code}")
                print(f"Response: {response.get_data()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_delete_functionality()
    sys.exit(0 if success else 1)
