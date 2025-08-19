#!/usr/bin/env python3
"""
Test script to simulate Sonic Traveller generation flow
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_generation_flow():
    """Test the actual generation flow step by step"""
    print("🧪 Testing Sonic Traveller Generation Flow")
    print("=" * 60)
    
    try:
        # Test each component of the generation flow
        from app.routes import _get_track_by_id, _map_candidates_to_local_with_features
        from feature_store import fetch_track_features
        from sonic_similarity import get_feature_stats, build_vector, compute_distance
        
        print("✅ All required modules imported successfully")
        
        # Step 1: Get a seed track
        print("\n🔍 Step 1: Getting seed track...")
        db_path = "db/local_music.db"
        seed_track = _get_track_by_id(1)  # Use first track as test
        if not seed_track:
            print("❌ Could not get seed track")
            return False
        
        print(f"✅ Seed track: {seed_track['artist']} - {seed_track['title']}")
        
        # Step 2: Get seed track features
        print("\n🔍 Step 2: Getting seed track features...")
        seed_features = fetch_track_features(db_path, 1)
        if not seed_features:
            print("❌ Seed track has no features")
            return False
        
        print(f"✅ Seed features: {list(seed_features.keys())}")
        
        # Step 3: Get feature stats
        print("\n🔍 Step 3: Getting feature stats...")
        stats = get_feature_stats(db_path)
        if not stats:
            print("❌ Could not get feature stats")
            return False
        
        print(f"✅ Feature stats: {len(stats)} features")
        
        # Step 4: Build seed vector
        print("\n🔍 Step 4: Building seed vector...")
        seed_vec = build_vector(seed_features, stats)
        print(f"✅ Seed vector: {len(seed_vec)} dimensions")
        
        # Step 5: Test candidate mapping
        print("\n🔍 Step 5: Testing candidate mapping...")
        test_candidates = [
            {'title': 'Away From The Sun', 'artist': '3 Doors Down'},
            {'title': 'Be Like That', 'artist': '3 Doors Down'},
            {'title': 'Kryptonite', 'artist': '3 Doors Down'},
            {'title': 'When I\'m Gone', 'artist': '3 Doors Down'},
            {'title': 'Here Without You', 'artist': '3 Doors Down'}
        ]
        
        print(f"   Testing with {len(test_candidates)} test candidates...")
        mapped = _map_candidates_to_local_with_features(test_candidates)
        print(f"✅ Mapped {len(mapped)} candidates to local tracks")
        
        if mapped:
            for i, track in enumerate(mapped[:3]):
                print(f"   {i+1}. {track['artist']} - {track['title']} (ID: {track['id']})")
        else:
            print("❌ No candidates mapped! This is the problem.")
            print("   Let's investigate why...")
            
            # Test individual candidate matching
            print("\n🔍 Investigating individual candidate matching...")
            for i, candidate in enumerate(test_candidates):
                print(f"   Candidate {i+1}: {candidate['artist']} - {candidate['title']}")
                
                # Test exact match
                import sqlite3
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                
                # Try exact match first
                cur.execute(
                    "SELECT id, title, artist, album FROM tracks WHERE lower(title)=? AND lower(artist)=? LIMIT 1",
                    (candidate['title'].lower(), candidate['artist'].lower())
                )
                exact_match = cur.fetchone()
                
                if exact_match:
                    print(f"     ✅ Exact match found: ID {exact_match[0]}")
                else:
                    # Try LIKE match
                    cur.execute(
                        "SELECT id, title, artist, album FROM tracks WHERE title LIKE ? AND artist LIKE ? LIMIT 3",
                        (f"%{candidate['title']}%", f"%{candidate['artist']}%")
                    )
                    like_matches = cur.fetchall()
                    
                    if like_matches:
                        print(f"     ⚠️  LIKE matches found: {len(like_matches)}")
                        for match in like_matches[:2]:
                            print(f"       - {match[2]} - {match[1]} (ID: {match[0]})")
                    else:
                        print(f"     ❌ No matches found")
                
                conn.close()
        
        # Step 6: Test distance computation
        print("\n🔍 Step 6: Testing distance computation...")
        if mapped:
            from feature_store import fetch_batch_features
            track_ids = [m['id'] for m in mapped]
            features_map = fetch_batch_features(db_path, track_ids)
            
            print(f"   Got features for {len(features_map)} tracks")
            
            scored = []
            for m in mapped:
                if m['id'] in features_map:
                    cand_vec = build_vector(features_map[m['id']], stats)
                    dist = compute_distance(seed_vec, cand_vec)
                    scored.append((dist, m))
            
            scored.sort(key=lambda x: x[0])
            print(f"✅ Computed distances for {len(scored)} tracks")
            
            # Show distances
            for i, (dist, track) in enumerate(scored[:3]):
                print(f"   {i+1}. {track['artist']} - {track['title']}: d={dist:.3f}")
        else:
            print("   Skipping distance computation - no mapped tracks")
            scored = []
        
        # Step 7: Test threshold filtering
        print("\n🔍 Step 7: Testing threshold filtering...")
        threshold = 0.35  # Default threshold
        accepted = [track for dist, track in scored if dist <= threshold]
        print(f"✅ Accepted {len(accepted)} tracks with threshold {threshold}")
        
        if accepted:
            print("   Accepted tracks:")
            for track in accepted:
                print(f"     - {track['artist']} - {track['title']}")
        else:
            print("   No tracks accepted with current threshold")
        
        print("\n" + "=" * 60)
        print("✅ Generation flow test completed!")
        
        if len(accepted) == 0:
            print("\n⚠️  WARNING: No tracks accepted with current threshold!")
            print("   This suggests the threshold might be too strict.")
            print("   Try lowering the threshold or check if the distance calculation is working correctly.")
        
        return True
        
    except Exception as e:
        print(f"❌ Generation flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_generation_flow()
    sys.exit(0 if success else 1)
