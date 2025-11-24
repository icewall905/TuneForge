#!/usr/bin/env python3
"""
Test script to check audio feature availability
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_feature_fetching():
    """Test audio feature fetching for specific tracks"""
    print("🔍 Testing Audio Feature Fetching")
    print("=" * 50)
    
    try:
        from feature_store import fetch_batch_features
        import sqlite3
        
        db_path = "db/local_music.db"
        
        # Test tracks that should have features
        test_track_ids = [1, 8, 11, 110, 113]  # From our previous test
        
        print(f"Testing feature fetch for track IDs: {test_track_ids}")
        
        # Fetch features
        features_map = fetch_batch_features(db_path, test_track_ids)
        print(f"✅ Features fetched for {len(features_map)} tracks")
        
        # Check each track
        for track_id in test_track_ids:
            if track_id in features_map:
                features = features_map[track_id]
                print(f"   Track {track_id}: ✅ Has features")
                print(f"     Energy: {features.get('energy', 'N/A')}")
                print(f"     Valence: {features.get('valence', 'N/A')}")
                print(f"     Tempo: {features.get('tempo', 'N/A')}")
            else:
                print(f"   Track {track_id}: ❌ No features")
        
        # Check what's in the audio_features table
        print(f"\n🔍 Checking audio_features table directly...")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Count total features
        cur.execute("SELECT COUNT(*) FROM audio_features")
        total_features = cur.fetchone()[0]
        print(f"✅ Total tracks with features: {total_features}")
        
        # Check specific track
        cur.execute("SELECT * FROM audio_features WHERE track_id = 1 LIMIT 1")
        track1_features = cur.fetchone()
        if track1_features:
            print(f"✅ Track 1 features found: {len(track1_features)} columns")
            # Get column names
            cur.execute("PRAGMA table_info(audio_features)")
            columns = [col[1] for col in cur.fetchall()]
            print(f"   Columns: {columns}")
            
            # Show first few values
            for i, col in enumerate(columns[:5]):
                if i < len(track1_features):
                    print(f"   {col}: {track1_features[i]}")
        else:
            print(f"❌ Track 1 has no features")
        
        # Check if track 1 exists in tracks table
        cur.execute("SELECT id, title, artist FROM tracks WHERE id = 1")
        track1_info = cur.fetchone()
        if track1_info:
            print(f"✅ Track 1 exists: {track1_info[2]} - {track1_info[1]}")
        else:
            print(f"❌ Track 1 not found in tracks table")
        
        conn.close()
        
        print("\n" + "=" * 50)
        print("✅ Feature fetching test completed!")
        
        return True
        
    except Exception as e:
        print(f"❌ Feature fetching test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_feature_fetching()
    sys.exit(0 if success else 1)
