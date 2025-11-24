#!/usr/bin/env python3
"""
Investigate why distances are so high in Sonic Traveller
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def investigate_distances():
    """Investigate the distance calculation process"""
    print("🔍 Investigating High Distances in Sonic Traveller")
    print("=" * 60)
    
    try:
        from sonic_similarity import get_feature_stats, build_vector, compute_distance
        from feature_store import fetch_track_features
        
        db_path = "db/local_music.db"
        
        # Get two similar tracks for comparison
        track1_id = 1   # 3 Doors Down - When I'm Gone (seed)
        track2_id = 11  # 3 Doors Down - Away From The Sun
        
        print(f"Comparing tracks:")
        print(f"  Track 1 (ID {track1_id}): Seed track")
        print(f"  Track 2 (ID {track2_id}): Similar track from same artist")
        
        # Get raw features
        print(f"\n🔍 Step 1: Raw Audio Features")
        features1 = fetch_track_features(db_path, track1_id)
        features2 = fetch_track_features(db_path, track2_id)
        
        if not features1 or not features2:
            print("❌ Could not fetch features")
            return False
        
        # Show raw feature values
        print(f"Track 1 raw features:")
        for key in ['energy', 'valence', 'tempo', 'danceability', 'acousticness', 'instrumentalness', 'loudness', 'speechiness']:
            if key in features1:
                print(f"  {key}: {features1[key]}")
        
        print(f"\nTrack 2 raw features:")
        for key in ['energy', 'valence', 'tempo', 'danceability', 'acousticness', 'instrumentalness', 'loudness', 'speechiness']:
            if key in features2:
                print(f"  {key}: {features2[key]}")
        
        # Get feature stats for normalization
        print(f"\n🔍 Step 2: Feature Statistics (for normalization)")
        stats = get_feature_stats(db_path)
        if not stats:
            print("❌ Could not get feature stats")
            return False
        
        print(f"Feature stats:")
        for feature, stat_tuple in stats.items():
            min_val, max_val = stat_tuple
            range_val = max_val - min_val
            print(f"  {feature}: min={min_val:.4f}, max={max_val:.4f}, range={range_val:.4f}")
        
        # Build normalized vectors
        print(f"\n🔍 Step 3: Building Normalized Vectors")
        
        # Debug the build_vector process
        print(f"Debugging build_vector process:")
        for col in ['energy', 'valence', 'tempo', 'danceability', 'acousticness', 'instrumentalness', 'loudness', 'speechiness']:
            val1 = features1.get(col)
            val2 = features2.get(col)
            min_val, max_val = stats.get(col, (None, None))
            print(f"  {col}:")
            print(f"    Track 1: {val1} (type: {type(val1)})")
            print(f"    Track 2: {val2} (type: {type(val2)})")
            print(f"    Stats: min={min_val}, max={max_val}")
        
        vec1 = build_vector(features1, stats)
        vec2 = build_vector(features2, stats)
        
        print(f"Track 1 normalized vector: {vec1}")
        print(f"Track 2 normalized vector: {vec2}")
        
        # Calculate distance manually to see each component
        print(f"\n🔍 Step 4: Manual Distance Calculation")
        if len(vec1) == len(vec2):
            squared_diff_sum = 0
            print(f"Feature-by-feature differences (with weights):")
            
            feature_names = ['energy', 'valence', 'danceability', 'tempo', 'acousticness', 'instrumentalness', 'loudness', 'speechiness']
            weights = {
                'energy': 1.0,
                'valence': 1.0,
                'danceability': 1.0,
                'tempo': 0.5,
                'acousticness': 0.5,
                'instrumentalness': 0.3,
                'loudness': 0.3,
                'speechiness': 0.2,
            }
            
            for i, (v1, v2) in enumerate(zip(vec1, vec2)):
                diff = v1 - v2
                weight = weights.get(feature_names[i], 1.0)
                weighted_squared_diff = weight * (diff ** 2)
                squared_diff_sum += weighted_squared_diff
                
                feature_name = feature_names[i] if i < len(feature_names) else f"feature_{i}"
                print(f"  {feature_name}: {v1:.4f} - {v2:.4f} = {diff:.4f} → weighted squared = {weight:.1f} × {diff**2:.4f} = {weighted_squared_diff:.4f}")
            
            euclidean_distance = (squared_diff_sum ** 0.5)
            print(f"\n  Sum of weighted squared differences: {squared_diff_sum:.4f}")
            print(f"  Weighted Euclidean distance: {euclidean_distance:.4f}")
            
            # Compare with function result
            function_distance = compute_distance(vec1, vec2)
            print(f"  Function result: {function_distance:.4f}")
            
            if abs(euclidean_distance - function_distance) > 0.001:
                print(f"  ⚠️  Mismatch between manual and function calculation!")
            else:
                print(f"  ✅ Manual and function calculations match")
        
        # Check if normalization is working correctly
        print(f"\n🔍 Step 5: Normalization Analysis")
        print(f"Expected normalized range: [0, 1]")
        
        for i, val in enumerate(vec1):
            feature_name = feature_names[i] if i < len(feature_names) else f"feature_{i}"
            if val < 0 or val > 1:
                print(f"  ⚠️  {feature_name}: {val:.4f} (outside [0,1] range)")
            else:
                print(f"  ✅ {feature_name}: {val:.4f} (within [0,1] range)")
        
        print(f"\n" + "=" * 60)
        print("✅ Distance investigation completed!")
        
        return True
        
    except Exception as e:
        print(f"❌ Distance investigation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = investigate_distances()
    sys.exit(0 if success else 1)
