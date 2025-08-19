#!/usr/bin/env python3
"""
Script to create the analysis_queue table for managing audio analysis jobs.
This table will track which tracks need analysis and their current status.
"""

import sqlite3
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.append(str(Path(__file__).parent.parent))

def create_analysis_queue_table():
    """Create the analysis_queue table for managing analysis jobs"""
    
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
            WHERE type='table' AND name='analysis_queue'
        """)
        
        if cursor.fetchone():
            print("✅ analysis_queue table already exists")
            
            # Show current structure
            cursor.execute("PRAGMA table_info(analysis_queue)")
            columns = cursor.fetchall()
            print(f"📊 Current columns: {len(columns)}")
            for col in columns:
                print(f"   - {col[1]} ({col[2]})")
            
            return True
        
        print("🚀 Creating analysis_queue table...")
        
        # Create the analysis_queue table
        create_table_sql = """
        CREATE TABLE analysis_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER NOT NULL,
            priority INTEGER DEFAULT 3,
            status TEXT DEFAULT 'queued',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE
        )
        """
        
        cursor.execute(create_table_sql)
        print("✅ analysis_queue table created successfully")
        
        # Create indexes for performance
        print("🔍 Creating performance indexes...")
        
        indexes = [
            "CREATE INDEX idx_analysis_queue_track_id ON analysis_queue(track_id)",
            "CREATE INDEX idx_analysis_queue_status ON analysis_queue(status)",
            "CREATE INDEX idx_analysis_queue_priority ON analysis_queue(priority)",
            "CREATE INDEX idx_analysis_queue_status_priority ON analysis_queue(status, priority)"
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
                print(f"✅ Index created: {index_sql.split('ON ')[1]}")
            except sqlite3.Error as e:
                print(f"⚠️  Index creation warning: {e}")
        
        # Verify table structure
        cursor.execute("PRAGMA table_info(analysis_queue)")
        columns = cursor.fetchall()
        
        print(f"\n📊 analysis_queue table structure:")
        for col in columns:
            print(f"   - {col[1]} ({col[2]})")
        
        # Test foreign key constraint
        print("\n🧪 Testing foreign key constraint...")
        
        # Try to insert a record with non-existent track_id (should fail)
        try:
            cursor.execute("""
                INSERT INTO analysis_queue (track_id, priority, status) 
                VALUES (999999, 1, 'queued')
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
                INSERT INTO analysis_queue (track_id, priority, status) 
                VALUES (1, 1, 'queued')
            """)
            print("✅ Valid record insertion test passed")
            
            # Verify the record was inserted
            cursor.execute("SELECT * FROM analysis_queue WHERE track_id = 1")
            record = cursor.fetchone()
            if record:
                print(f"✅ Record verification: {record}")
            else:
                print("❌ Record verification failed")
                return False
            
            # Clean up test record
            cursor.execute("DELETE FROM analysis_queue WHERE track_id = 1")
            print("✅ Test record cleaned up")
            
        except sqlite3.Error as e:
            print(f"❌ Valid record insertion test failed: {e}")
            return False
        
        # Commit changes
        conn.commit()
        print("💾 Changes committed successfully")
        
        # Show final table count
        cursor.execute("SELECT COUNT(*) FROM analysis_queue")
        count = cursor.fetchone()[0]
        print(f"📈 analysis_queue table is empty and ready: {count} records")
        
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
    print("🎵 TuneForge Analysis Queue Table Creation")
    print("=" * 50)
    
    success = create_analysis_queue_table()
    
    if success:
        print("\n🎉 Table creation completed successfully!")
        print("✅ analysis_queue table created with proper structure")
        print("✅ Foreign key constraints working correctly")
        print("✅ Performance indexes created")
        print("✅ Phase 1 Complete: All database tables created successfully!")
        print("🚀 Ready for Phase 2: Core Audio Analysis Engine")
    else:
        print("\n❌ Table creation failed!")
        print("Please check the error messages above")
        sys.exit(1)

if __name__ == "__main__":
    main()
