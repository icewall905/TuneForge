#!/usr/bin/env python3
"""
Debug why distances are > 1.0 when vectors should be normalized
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def debug_distance_calculation():
    """Debug the distance calculation process"""
    print("🔍 Debugging Distance Calculation > 1.0 Issue")
    print("=" * 60)
    
    try:
        from sonic_similarity import get_feature_stats, build_vector, compute_distance, FEATURE_ORDER, DEFAULT_WEIGHTS
        from feature_store import fetch_track_features
        
        db_path = "db/local_music.db"
        
        # Get two tracks and compute their distance
        track1_id = 1   # Seed track
        track2_id = 11  # Similar track
        
        print(f"Comparing tracks:")
        print(f"  Track 1 (ID {track1_id}): Seed track")
        print(f"  Track 2 (ID {track2_id}): Similar track")
        
        # Get features and build vectors
        features1 = fetch_track_features(db_path, track1_id)
        features2 = fetch_track_features(db_path, track2_id)
        stats = get_feature_stats(db_path)
        
        vec1 = build_vector(features1, stats)
        vec2 = build_vector(features2, stats)
        
        print(f"\n🔍 Vector Analysis:")
        print(f"Track 1 vector: {vec1}")
        print(f"Track 2 vector: {vec2}")
        
        # Check normalization
        print(f"\n🔍 Normalization Check:")
        for i, (v1, v2) in enumerate(zip(vec1, vec2)):
            feature = FEATURE_ORDER[i]
            if v1 < 0 or v1 > 1 or v2 < 0 or v2 > 1:
                print(f"  ⚠️  {feature}: v1={v1:.4f}, v2={v2:.4f} (outside [0,1] range)")
            else:
                print(f"  ✅ {feature}: v1={v1:.4f}, v2={v2:.4f}")
        
        # Manual distance calculation with weights
        print(f"\n🔍 Manual Weighted Distance Calculation:")
        print(f"Feature weights: {DEFAULT_WEIGHTS}")
        
        squared_sum = 0
        for i, feature in enumerate(FEATURE_ORDER):
            v1, v2 = vec1[i], vec2[i]
            diff = v1 - v2
            weight = DEFAULT_WEIGHTS.get(feature, 1.0)
            weighted_squared = weight * (diff ** 2)
            squared_sum += weighted_squared
            
            print(f"  {feature:15s}: diff={diff:8.4f}, weight={weight:4.1f}, weighted_sq={weighted_squared:8.4f}")
        
        manual_distance = (squared_sum ** 0.5)
        print(f"\n  Sum of weighted squared differences: {squared_sum:.6f}")
        print(f"  Manual weighted distance: {manual_distance:.6f}")
        
        # Function distance
        function_distance = compute_distance(vec1, vec2)
        print(f"  Function distance: {function_distance:.6f}")
        
        if abs(manual_distance - function_distance) > 0.001:
            print(f"  ⚠️  Mismatch between manual and function!")
        else:
            print(f"  ✅ Manual and function match")
        
        # Check if distance > 1.0
        if manual_distance > 1.0:
            print(f"\n🚨 PROBLEM: Distance {manual_distance:.6f} > 1.0!")
            print(f"   This suggests the normalization or weight calculation is wrong.")
            
            # Check individual components
            print(f"\n🔍 Individual Component Analysis:")
            for i, feature in enumerate(FEATURE_ORDER):
                v1, v2 = vec1[i], vec2[i]
                diff = v1 - v2
                weight = DEFAULT_WEIGHTS.get(feature, 1.0)
                weighted_squared = weight * (diff ** 2)
                
                if weighted_squared > 0.1:  # Show significant contributors
                    print(f"  {feature:15s}: contributes {weighted_squared:.6f} to total")
        
        else:
            print(f"\n✅ Distance {manual_distance:.6f} is reasonable (≤ 1.0)")
        
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_distance_calculation()
    sys.exit(0 if success else 1)
