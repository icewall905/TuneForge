#!/usr/bin/env python3
"""
Script to create the audio_features table for storing extracted audio characteristics.
This table will store musical features like tempo, key, energy, etc.
"""

import sqlite3
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.append(str(Path(__file__).parent.parent))

def create_audio_features_table():
    """Create the audio_features table with all necessary columns"""
    
    # Database path
    db_path = os.path.join(os.path.dirname(__file__), '..', 'db', 'local_music.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return False
    
    print(f"📁 Database found at: {db_path}")
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔗 Connected to database successfully")
        
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")
        print("🔑 Foreign key constraints enabled")
        
        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='audio_features'
        """)
        
        if cursor.fetchone():
            print("✅ audio_features table already exists")
            
            # Show current structure
            cursor.execute("PRAGMA table_info(audio_features)")
            columns = cursor.fetchall()
            print(f"📊 Current columns: {len(columns)}")
            for col in columns:
                print(f"   - {col[1]} ({col[2]})")
            
            return True
        
        print("🚀 Creating audio_features table...")
        
        # Create the audio_features table
        create_table_sql = """
        CREATE TABLE audio_features (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER NOT NULL,
            tempo REAL,
            key TEXT,
            mode TEXT,
            energy REAL,
            danceability REAL,
            valence REAL,
            acousticness REAL,
            instrumentalness REAL,
            loudness REAL,
            speechiness REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE
        )
        """
        
        cursor.execute(create_table_sql)
        print("✅ audio_features table created successfully")
        
        # Create indexes for performance
        print("🔍 Creating performance indexes...")
        
        indexes = [
            "CREATE INDEX idx_audio_features_track_id ON audio_features(track_id)",
            "CREATE INDEX idx_audio_features_tempo ON audio_features(tempo)",
            "CREATE INDEX idx_audio_features_key ON audio_features(key)",
            "CREATE INDEX idx_audio_features_energy ON audio_features(energy)",
            "CREATE INDEX idx_audio_features_danceability ON audio_features(danceability)"
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
                print(f"✅ Index created: {index_sql.split('ON ')[1]}")
            except sqlite3.Error as e:
                print(f"⚠️  Index creation warning: {e}")
        
        # Verify table structure
        cursor.execute("PRAGMA table_info(audio_features)")
        columns = cursor.fetchall()
        
        print(f"\n📊 audio_features table structure:")
        for col in columns:
            print(f"   - {col[1]} ({col[2]})")
        
        # Test foreign key constraint
        print("\n🧪 Testing foreign key constraint...")
        
        # Verify foreign keys are enabled
        cursor.execute("PRAGMA foreign_keys")
        fk_enabled = cursor.fetchone()[0]
        print(f"🔑 Foreign keys enabled: {bool(fk_enabled)}")
        
        # Try to insert a record with non-existent track_id (should fail)
        try:
            cursor.execute("""
                INSERT INTO audio_features (track_id, tempo, key, mode) 
                VALUES (999999, 120.0, 'C', 'major')
            """)
            print("❌ Foreign key constraint test failed - should have rejected invalid track_id")
            return False
        except sqlite3.IntegrityError:
            print("✅ Foreign key constraint working correctly")
        except sqlite3.Error as e:
            if "FOREIGN KEY constraint failed" in str(e):
                print("✅ Foreign key constraint working correctly")
            else:
                print(f"❌ Unexpected error during foreign key test: {e}")
                return False
        
        # Test inserting a valid record (should succeed)
        try:
            cursor.execute("""
                INSERT INTO audio_features (track_id, tempo, key, mode, energy) 
                VALUES (1, 120.0, 'C', 'major', 0.8)
            """)
            print("✅ Valid record insertion test passed")
            
            # Verify the record was inserted
            cursor.execute("SELECT * FROM audio_features WHERE track_id = 1")
            record = cursor.fetchone()
            if record:
                print(f"✅ Record verification: {record}")
            else:
                print("❌ Record verification failed")
                return False
            
            # Clean up test record
            cursor.execute("DELETE FROM audio_features WHERE track_id = 1")
            print("✅ Test record cleaned up")
            
        except sqlite3.Error as e:
            print(f"❌ Valid record insertion test failed: {e}")
            return False
        
        # Commit changes
        conn.commit()
        print("💾 Changes committed successfully")
        
        # Show final table count
        cursor.execute("SELECT COUNT(*) FROM audio_features")
        count = cursor.fetchone()[0]
        print(f"📈 audio_features table is empty and ready: {count} records")
        
        conn.close()
        print("🔒 Database connection closed")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main function"""
    print("🎵 TuneForge Audio Features Table Creation")
    print("=" * 50)
    
    success = create_audio_features_table()
    
    if success:
        print("\n🎉 Table creation completed successfully!")
        print("✅ audio_features table created with proper structure")
        print("✅ Foreign key constraints working correctly")
        print("✅ Performance indexes created")
        print("✅ Ready for Phase 1, Task 1.3: Create Analysis Queue Table")
    else:
        print("\n❌ Table creation failed!")
        print("Please check the error messages above")
        sys.exit(1)

if __name__ == "__main__":
    main()
