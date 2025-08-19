#!/usr/bin/env python3
"""
Test Sonic Traveller with tracks we know exist in the library
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_working_sonic_traveller():
    """Test Sonic Traveller with known existing tracks"""
    print("🧪 Testing Working Sonic Traveller (Known Tracks)")
    print("=" * 60)
    
    try:
        from app.routes import _get_track_by_id, _map_candidates_to_local_with_features
        from feature_store import fetch_track_features, fetch_batch_features
        from sonic_similarity import get_feature_stats, build_vector, compute_distance
        
        db_path = "db/local_music.db"
        
        # Use tracks we know exist
        seed_track_id = 1   # 3 Doors Down - When I'm Gone
        test_candidates = [
            {'title': 'Kryptonite', 'artist': '3 Doors Down'},
            {'title': 'Here Without You', 'artist': '3 Doors Down'},
            {'title': 'Be Like That', 'artist': '3 Doors Down'},
            {'title': 'Away From The Sun', 'artist': '3 Doors Down'},
            {'title': 'Loser', 'artist': '3 Doors Down'},
            {'title': 'Duck And Run', 'artist': '3 Doors Down'},
            {'title': 'Better Life', 'artist': '3 Doors Down'},
            {'title': 'It\'s Not My Time', 'artist': '3 Doors Down'},
            {'title': 'Let Me Go', 'artist': '3 Doors Down'},
            {'title': 'Citizen/Soldier', 'artist': '3 Doors Down'}
        ]
        
        print(f"Seed track: {_get_track_by_id(seed_track_id)['artist']} - {_get_track_by_id(seed_track_id)['title']}")
        print(f"Testing with {len(test_candidates)} known 3 Doors Down tracks")
        
        # Test the full pipeline
        print(f"\n🔍 Step 1: Candidate Mapping")
        mapped = _map_candidates_to_local_with_features(test_candidates)
        print(f"✅ Mapped {len(mapped)} candidates to local tracks")
        
        if not mapped:
            print("❌ No candidates mapped - this is the problem!")
            return False
        
        # Test feature fetching
        print(f"\n🔍 Step 2: Feature Fetching")
        seed_features = fetch_track_features(db_path, seed_track_id)
        stats = get_feature_stats(db_path)
        
        if not seed_features:
            print("❌ Seed track has no features")
            return False
        
        print(f"✅ Seed features: {list(seed_features.keys())}")
        print(f"✅ Feature stats: {len(stats)} features")
        
        # Test vector building
        print(f"\n🔍 Step 3: Vector Building")
        seed_vec = build_vector(seed_features, stats)
        print(f"✅ Seed vector: {len(seed_vec)} dimensions")
        
        # Test distance calculation
        print(f"\n🔍 Step 4: Distance Calculation")
        track_ids = [m['id'] for m in mapped]
        features_map = fetch_batch_features(db_path, track_ids)
        
        scored = []
        for m in mapped:
            if m['id'] in features_map:
                cand_vec = build_vector(features_map[m['id']], stats)
                dist = compute_distance(seed_vec, cand_vec)
                scored.append((dist, m))
        
        scored.sort(key=lambda x: x[0])
        print(f"✅ Computed distances for {len(scored)} tracks")
        
        # Show distances
        print(f"\n🔍 Distance Results:")
        for i, (dist, track) in enumerate(scored[:5]):
            print(f"  {i+1}. {track['artist']} - {track['title']}: d={dist:.4f}")
        
        # Test threshold filtering
        print(f"\n🔍 Step 5: Threshold Testing")
        thresholds = [0.2, 0.3, 0.4, 0.5, 0.75, 1.0, 1.5, 2.0]
        
        for threshold in thresholds:
            accepted = [track for dist, track in scored if dist <= threshold]
            print(f"  Threshold {threshold:4.1f}: {len(accepted):2d} tracks accepted")
            if accepted:
                print(f"    First: {accepted[0]['artist']} - {accepted[0]['title']} (d={next(d for d, t in scored if t['id'] == accepted[0]['id']):.4f})")
        
        print(f"\n" + "=" * 60)
        print("✅ Sonic Traveller pipeline test completed!")
        
        if len(scored) > 0:
            min_distance = scored[0][0]
            print(f"\n🎯 Minimum distance: {min_distance:.4f}")
            print(f"   Recommended threshold: {min_distance + 0.1:.4f}")
            print(f"   With this threshold: {len([t for d, t in scored if d <= min_distance + 0.1])} tracks accepted")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_working_sonic_traveller()
    sys.exit(0 if success else 1)
