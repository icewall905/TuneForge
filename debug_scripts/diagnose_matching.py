#!/usr/bin/env python3
"""
Diagnostic script for Sonic Traveller matching issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def diagnose_matching():
    """Diagnose potential matching issues"""
    print("🔍 Sonic Traveller Matching Diagnosis")
    print("=" * 50)
    
    try:
        # Test database connectivity and content
        from app.routes import _get_db_path, search_local_tracks
        db_path = _get_db_path()
        
        print(f"✅ Database path: {db_path}")
        print(f"✅ Database exists: {os.path.exists(db_path)}")
        
        if not os.path.exists(db_path):
            print("❌ Database does not exist!")
            return False
        
        # Test search functionality
        print("\n🔍 Testing search functionality...")
        test_queries = ["test", "rock", "pop", "a", "the"]
        
        for query in test_queries:
            results = search_local_tracks(query, limit=5)
            print(f"   Query '{query}': {len(results)} results")
            if results:
                print(f"     Sample: {results[0]['artist']} - {results[0]['title']}")
        
        # Test audio features availability
        print("\n🔍 Testing audio features availability...")
        try:
            from feature_store import check_audio_feature_schema, fetch_track_features
            schema_ok, missing = check_audio_feature_schema(db_path)
            print(f"✅ Audio features schema: {'OK' if schema_ok else 'INCOMPLETE'}")
            if not schema_ok:
                print(f"   Missing columns: {missing}")
            
            # Check if any tracks have features
            import sqlite3
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            
            # Count tracks with features
            cur.execute("SELECT COUNT(*) FROM audio_features")
            features_count = cur.fetchone()[0]
            print(f"✅ Tracks with audio features: {features_count}")
            
            # Count total tracks
            cur.execute("SELECT COUNT(*) FROM tracks")
            total_tracks = cur.fetchone()[0]
            print(f"✅ Total tracks in database: {total_tracks}")
            
            if features_count == 0:
                print("❌ NO TRACKS HAVE AUDIO FEATURES!")
                print("   This is why matching is failing - Sonic Traveller needs audio features to work")
                return False
            
            # Check feature coverage percentage
            coverage = (features_count / total_tracks) * 100 if total_tracks > 0 else 0
            print(f"✅ Feature coverage: {coverage:.1f}%")
            
            if coverage < 10:
                print("⚠️  Very low feature coverage - this will severely limit Sonic Traveller")
            elif coverage < 50:
                print("⚠️  Low feature coverage - Sonic Traveller will have limited success")
            else:
                print("✅ Good feature coverage - Sonic Traveller should work well")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Error checking audio features: {e}")
            return False
        
        # Test Ollama integration
        print("\n🔍 Testing Ollama integration...")
        try:
            from app.routes import get_config_value
            ollama_url = get_config_value('OLLAMA', 'URL')
            ollama_model = get_config_value('OLLAMA', 'Model', 'llama3')
            
            print(f"✅ Ollama URL: {ollama_url}")
            print(f"✅ Ollama Model: {ollama_model}")
            
            if not ollama_url:
                print("❌ Ollama URL not configured!")
                return False
                
        except Exception as e:
            print(f"❌ Error checking Ollama config: {e}")
            return False
        
        print("\n" + "=" * 50)
        print("✅ Diagnosis completed!")
        
        if features_count == 0:
            print("\n🚨 CRITICAL ISSUE FOUND:")
            print("   No tracks have audio features. Sonic Traveller cannot work without them.")
            print("   You need to run the audio analysis system first to extract features.")
            return False
        elif coverage < 50:
            print("\n⚠️  WARNING:")
            print("   Low audio feature coverage. Sonic Traveller will have limited success.")
            print("   Consider running audio analysis on more tracks.")
            return False
        else:
            print("\n✅ Sonic Traveller should work correctly!")
            print("   If matching is still failing, the issue might be:")
            print("   1. Ollama not responding properly")
            print("   2. LLM suggestions not matching local track names")
            print("   3. Threshold too strict for available tracks")
        
        return True
        
    except Exception as e:
        print(f"❌ Diagnosis failed: {e}")
        return False

if __name__ == "__main__":
    success = diagnose_matching()
    sys.exit(0 if success else 1)
