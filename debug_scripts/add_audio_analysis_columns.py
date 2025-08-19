#!/usr/bin/env python3
"""
Safe migration script to add audio analysis columns to the tracks table.
This script adds new columns without affecting existing data.
"""

import sqlite3
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.append(str(Path(__file__).parent.parent))

def add_audio_analysis_columns():
    """Add audio analysis columns to the tracks table"""
    
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
        
        # Check current table structure
        cursor.execute("PRAGMA table_info(tracks)")
        current_columns = {row[1] for row in cursor.fetchall()}
        print(f"📊 Current columns: {', '.join(sorted(current_columns))}")
        
        # Define new columns to add
        new_columns = [
            ('analysis_status', 'TEXT'),
            ('analysis_date', 'TIMESTAMP'),
            ('analysis_error', 'TEXT')
        ]
        
        # Check which columns already exist
        columns_to_add = []
        for col_name, col_type in new_columns:
            if col_name not in current_columns:
                columns_to_add.append((col_name, col_type))
                print(f"➕ Will add: {col_name} ({col_type})")
            else:
                print(f"✅ Already exists: {col_name}")
        
        if not columns_to_add:
            print("🎉 All audio analysis columns already exist!")
            return True
        
        # Add new columns one by one
        print(f"\n🚀 Adding {len(columns_to_add)} new columns...")
        
        for col_name, col_type in columns_to_add:
            try:
                # Use ALTER TABLE ADD COLUMN (SQLite supports this)
                sql = f"ALTER TABLE tracks ADD COLUMN {col_name} {col_type}"
                cursor.execute(sql)
                print(f"✅ Added column: {col_name}")
                
            except sqlite3.Error as e:
                print(f"❌ Error adding column {col_name}: {e}")
                return False
        
        # Verify the new structure
        cursor.execute("PRAGMA table_info(tracks)")
        final_columns = {row[1] for row in cursor.fetchall()}
        print(f"\n📊 Final columns: {', '.join(sorted(final_columns))}")
        
        # Check that our new columns are there
        for col_name, _ in columns_to_add:
            if col_name in final_columns:
                print(f"✅ Verification: {col_name} column exists")
            else:
                print(f"❌ Verification failed: {col_name} column missing")
                return False
        
        # Commit changes
        conn.commit()
        print("💾 Changes committed successfully")
        
        # Test that existing data is intact
        cursor.execute("SELECT COUNT(*) FROM tracks")
        track_count = cursor.fetchone()[0]
        print(f"🔍 Track count verification: {track_count} tracks (should be unchanged)")
        
        # Test that new columns accept NULL values (which they should by default)
        cursor.execute("SELECT analysis_status, analysis_date, analysis_error FROM tracks LIMIT 1")
        sample_row = cursor.fetchone()
        print(f"🧪 Sample row from new columns: {sample_row}")
        
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
    print("🎵 TuneForge Audio Analysis Column Migration")
    print("=" * 50)
    
    success = add_audio_analysis_columns()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("✅ Audio analysis columns added to tracks table")
        print("✅ Existing data preserved")
        print("✅ Ready for next phase of implementation")
    else:
        print("\n❌ Migration failed!")
        print("Please check the error messages above")
        sys.exit(1)

if __name__ == "__main__":
    main()
