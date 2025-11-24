#!/usr/bin/env python3
"""
Test script for Sonic Traveller functionality
Tests the core components without requiring the full Flask app
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_sonic_similarity():
    """Test the sonic similarity engine"""
    print("🧪 Testing Sonic Similarity Engine...")
    
    try:
        from sonic_similarity import (
            get_feature_stats, build_vector, compute_distance,
            compute_batch_distances, ensure_database_indexes, clear_caches
        )
        print("✅ All sonic_similarity functions imported successfully")
        
        # Test vector building
        test_features = {
            'energy': 0.8,
            'valence': 0.6,
            'danceability': 0.9,
            'tempo': 120.0,
            'acousticness': 0.1,
            'instrumentalness': 0.0,
            'loudness': -5.0,
            'speechiness': 0.05
        }
        
        test_stats = {
            'energy': (0.0, 1.0),
            'valence': (0.0, 1.0),
            'danceability': (0.0, 1.0),
            'tempo': (60.0, 200.0),
            'acousticness': (0.0, 1.0),
            'instrumentalness': (0.0, 1.0),
            'loudness': (-60.0, 0.0),
            'speechiness': (0.0, 1.0)
        }
        
        vec = build_vector(test_features, test_stats)
        print(f"✅ Vector built successfully: {len(vec)} features")
        
        # Test distance computation
        vec2 = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        dist = compute_distance(vec, vec2)
        print(f"✅ Distance computed: {dist:.3f}")
        
        # Test batch distances
        batch_vecs = [vec2, vec]
        batch_dists = compute_batch_distances(vec, batch_vecs)
        print(f"✅ Batch distances computed: {len(batch_dists)} results")
        
        print("✅ Sonic Similarity Engine tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Sonic Similarity Engine test failed: {e}")
        return False

def test_feature_store():
    """Test the feature store functionality"""
    print("\n🧪 Testing Feature Store...")
    
    try:
        from feature_store import (
            check_audio_feature_schema, fetch_track_features, fetch_batch_features
        )
        print("✅ All feature_store functions imported successfully")
        
        # Test schema checking (will work even if DB doesn't exist)
        db_path = "db/local_music.db"
        schema_ok, missing = check_audio_feature_schema(db_path)
        print(f"✅ Schema check completed: ok={schema_ok}, missing={missing}")
        
        print("✅ Feature Store tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Feature Store test failed: {e}")
        return False

def test_routes_import():
    """Test that the routes can be imported (without running Flask)"""
    print("\n🧪 Testing Routes Import...")
    
    try:
        # This will import the routes but not run Flask
        import app.routes
        print("✅ Routes module imported successfully")
        
        # Check if our new endpoints are defined
        from app.routes import (
            api_sonic_start, api_sonic_status, api_sonic_stop,
            api_sonic_cleanup, api_sonic_export_json, api_sonic_export_m3u
        )
        print("✅ All Sonic Traveller endpoints imported successfully")
        
        print("✅ Routes import tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Routes import test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Sonic Traveller Test Suite")
    print("=" * 40)
    
    tests = [
        test_sonic_similarity,
        test_feature_store,
        test_routes_import
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 40)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Sonic Traveller is ready to use.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
