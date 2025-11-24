#!/usr/bin/env python3
"""
Detailed debug script for feature fetching
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def debug_feature_fetch():
    """Debug the feature fetching process step by step"""
    print("🔍 Debugging Feature Fetching Process")
    print("=" * 50)
    
    try:
        import sqlite3
        
        db_path = "db/local_music.db"
        
        # Test track ID 1
        track_id = 1
        print(f"Testing track ID: {track_id} (type: {type(track_id)})")
        
        # Direct database query
        print(f"\n🔍 Direct database query...")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        cur.execute('SELECT * FROM audio_features WHERE track_id = ?', (track_id,))
        row = cur.fetchone()
        
        if row:
            print(f"✅ Row found: {len(row)} columns")
            
            # Get column names
            cur.execute('PRAGMA table_info(audio_features)')
            columns = [col[1] for col in cur.fetchall()]
            print(f"   Columns: {columns}")
            
            # Show the data
            data = {columns[i]: row[i] for i in range(len(row))}
            print(f"   track_id value: {data.get('track_id')} (type: {type(data.get('track_id'))})")
            print(f"   energy value: {data.get('energy')} (type: {type(data.get('energy'))})")
            
            # Test the type conversion
            try:
                tid = int(data.get('track_id'))
                print(f"   track_id as int: {tid} (type: {type(tid)})")
            except Exception as e:
                print(f"   ❌ Error converting track_id to int: {e}")
        else:
            print(f"❌ No row found for track_id = {track_id}")
        
        # Test batch query
        print(f"\n🔍 Testing batch query...")
        track_ids = [1, 8, 11]
        print(f"   Querying for track IDs: {track_ids}")
        
        q_marks = ','.join('?' for _ in track_ids)
        query = f'SELECT * FROM audio_features WHERE track_id IN ({q_marks})'
        print(f"   Query: {query}")
        
        cur.execute(query, track_ids)
        rows = cur.fetchall()
        print(f"   Found {len(rows)} rows")
        
        if rows:
            col_names = [d[1] for d in cur.description]
            print(f"   Column names: {col_names}")
            
            for i, row in enumerate(rows):
                data = {col_names[j]: row[j] for j in range(len(row))}
                tid = data.get('track_id')
                print(f"   Row {i+1}: track_id={tid} (type: {type(tid)})")
                
                # Test the exact logic from fetch_batch_features
                try:
                    tid_int = int(tid) if tid is not None else None
                    print(f"     Converted to int: {tid_int}")
                    if tid_int is not None:
                        print(f"     ✅ Would be included in result")
                    else:
                        print(f"     ❌ Would be excluded (None)")
                except Exception as e:
                    print(f"     ❌ Error converting: {e}")
        
        conn.close()
        
        # Now test the actual function
        print(f"\n🔍 Testing fetch_batch_features function...")
        from feature_store import fetch_batch_features
        
        result = fetch_batch_features(db_path, track_ids)
        print(f"   Function result: {len(result)} tracks")
        print(f"   Result keys: {list(result.keys())}")
        
        print("\n" + "=" * 50)
        print("✅ Debug completed!")
        
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_feature_fetch()
    sys.exit(0 if success else 1)
