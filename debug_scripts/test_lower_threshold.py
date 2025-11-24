#!/usr/bin/env python3
"""
Test Sonic Traveller with lower threshold to ensure it works
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_lower_threshold():
    """Test Sonic Traveller with progressively lower thresholds"""
    print("🧪 Testing Sonic Traveller with Lower Thresholds")
    print("=" * 60)
    
    try:
        from app.routes import _get_track_by_id, _map_candidates_to_local_with_features
        from feature_store import fetch_track_features, fetch_batch_features
        from sonic_similarity import get_feature_stats, build_vector, compute_distance
        
        db_path = "db/local_music.db"
        
        # Get seed track
        seed_track_id = 1
        seed_track = _get_track_by_id(seed_track_id)
        print(f"Seed track: {seed_track['artist']} - {seed_track['title']}")
        
        # Get seed features and build vector
        seed_features = fetch_track_features(db_path, seed_track_id)
        stats = get_feature_stats(db_path)
        seed_vec = build_vector(seed_features, stats)
        
        # Test candidates from same artist (should be similar)
        test_candidates = [
            {'title': 'Away From The Sun', 'artist': '3 Doors Down'},
            {'title': 'Be Like That', 'artist': '3 Doors Down'},
            {'title': 'Kryptonite', 'artist': '3 Doors Down'},
            {'title': 'Here Without You', 'artist': '3 Doors Down'},
            {'title': 'Better Life', 'artist': '3 Doors Down'}
        ]
        
        # Map candidates
        mapped = _map_candidates_to_local_with_features(test_candidates)
        print(f"Mapped {len(mapped)} candidates to local tracks")
        
        if not mapped:
            print("❌ No candidates mapped - this is still the problem!")
            return False
        
        # Get features and compute distances
        track_ids = [m['id'] for m in mapped]
        features_map = fetch_batch_features(db_path, track_ids)
        
        scored = []
        for m in mapped:
            if m['id'] in features_map:
                cand_vec = build_vector(features_map[m['id']], stats)
                dist = compute_distance(seed_vec, cand_vec)
                scored.append((dist, m))
        
        scored.sort(key=lambda x: x[0])
        
        print(f"\n🔍 Distance Analysis:")
        print(f"All computed distances:")
        for i, (dist, track) in enumerate(scored):
            print(f"  {i+1}. {track['artist']} - {track['title']}: d={dist:.4f}")
        
        # Test different thresholds
        thresholds_to_test = [0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0, 1.5, 2.0]
        
        print(f"\n🔍 Testing Different Thresholds:")
        for threshold in thresholds_to_test:
            accepted = [track for dist, track in scored if dist <= threshold]
            print(f"  Threshold {threshold:4.1f}: {len(accepted):2d} tracks accepted")
            if accepted:
                for track in accepted[:3]:  # Show first 3
                    dist = next(d for d, t in scored if t['id'] == track['id'])
                    print(f"    - {track['artist']} - {track['title']} (d={dist:.4f})")
        
        # Find the minimum distance
        if scored:
            min_distance = scored[0][0]
            print(f"\n✅ Minimum distance found: {min_distance:.4f}")
            print(f"   Recommended threshold: {min_distance + 0.1:.4f} (min + 0.1)")
            
            # Test with recommended threshold
            recommended_threshold = min_distance + 0.1
            accepted = [track for dist, track in scored if dist <= recommended_threshold]
            print(f"   With recommended threshold: {len(accepted)} tracks accepted")
            
            return True
        else:
            print("❌ No distances computed")
            return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_lower_threshold()
    sys.exit(0 if success else 1)
