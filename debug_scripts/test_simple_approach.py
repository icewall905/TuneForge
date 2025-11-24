#!/usr/bin/env python3
"""
Test a very simple approach - suggest tracks that should definitely exist
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_simple_approach():
    """Test with very simple, common track suggestions"""
    print("🧪 Testing Simple Approach - Common Tracks")
    print("=" * 50)
    
    try:
        from app.routes import _map_candidates_to_local_with_features
        
        # Test with very common tracks that should exist
        test_candidates = [
            {'title': 'Kryptonite', 'artist': '3 Doors Down'},
            {'title': 'Here Without You', 'artist': '3 Doors Down'},
            {'title': 'Be Like That', 'artist': '3 Doors Down'},
            {'title': 'Away From The Sun', 'artist': '3 Doors Down'},
            {'title': 'When I\'m Gone', 'artist': '3 Doors Down'},
            {'title': 'Loser', 'artist': '3 Doors Down'},
            {'title': 'Duck And Run', 'artist': '3 Doors Down'},
            {'title': 'Better Life', 'artist': '3 Doors Down'},
            {'title': 'It\'s Not My Time', 'artist': '3 Doors Down'},
            {'title': 'Let Me Go', 'artist': '3 Doors Down'}
        ]
        
        print(f"Testing with {len(test_candidates)} common 3 Doors Down tracks...")
        
        # Test mapping
        mapped = _map_candidates_to_local_with_features(test_candidates)
        print(f"✅ Mapped {len(mapped)} candidates to local tracks")
        
        if mapped:
            print("   Mapped tracks:")
            for i, track in enumerate(mapped[:5]):
                print(f"     {i+1}. {track['artist']} - {track['title']} (ID: {track['id']})")
        else:
            print("   ❌ Still no matches - this suggests a deeper issue")
            
            # Let me check what's in the database directly
            print("\n🔍 Checking database directly...")
            import sqlite3
            
            db_path = "db/local_music.db"
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            
            # Check for these specific tracks
            for candidate in test_candidates[:5]:
                cur.execute("""
                    SELECT id, title, artist, album 
                    FROM tracks 
                    WHERE LOWER(title) = ? AND LOWER(artist) = ?
                """, (candidate['title'].lower(), candidate['artist'].lower()))
                
                result = cur.fetchone()
                if result:
                    print(f"     ✅ Found: {result[2]} - {result[1]} (ID: {result[0]})")
                else:
                    print(f"     ❌ Not found: {candidate['artist']} - {candidate['title']}")
            
            conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_simple_approach()
    sys.exit(0 if success else 1)
