#!/usr/bin/env python3
"""
Check what rock/alternative rock artists are available in the local library
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_local_rock_artists():
    """Check available rock artists in local library"""
    print("🔍 Checking Local Rock Artists")
    print("=" * 50)
    
    try:
        import sqlite3
        
        db_path = "db/local_music.db"
        
        if not os.path.exists(db_path):
            print("❌ Database not found")
            return False
        
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Check total tracks
        cur.execute("SELECT COUNT(*) FROM tracks")
        total_tracks = cur.fetchone()[0]
        print(f"Total tracks in library: {total_tracks}")
        
        # Check artists with most tracks
        print("\n🔍 Top Artists by Track Count:")
        cur.execute("""
            SELECT artist, COUNT(*) as track_count 
            FROM tracks 
            WHERE artist IS NOT NULL AND artist != ''
            GROUP BY artist 
            ORDER BY track_count DESC 
            LIMIT 20
        """)
        
        artists = cur.fetchall()
        for i, (artist, count) in enumerate(artists, 1):
            print(f"  {i:2d}. {artist:30s} - {count:3d} tracks")
        
        # Check for specific rock artists
        print("\n🔍 Looking for Rock Artists:")
        rock_keywords = ['rock', 'alternative', 'grunge', 'post-grunge', 'punk', 'metal']
        
        for keyword in rock_keywords:
            cur.execute("""
                SELECT DISTINCT artist 
                FROM tracks 
                WHERE LOWER(artist) LIKE ? OR LOWER(genre) LIKE ?
                LIMIT 10
            """, (f'%{keyword}%', f'%{keyword}%'))
            
            matches = cur.fetchall()
            if matches:
                print(f"  {keyword.title()}:")
                for artist, in matches:
                    print(f"    - {artist}")
            else:
                print(f"  {keyword.title()}: No matches")
        
        # Check genres
        print("\n🔍 Genre Distribution:")
        cur.execute("""
            SELECT genre, COUNT(*) as count 
            FROM tracks 
            WHERE genre IS NOT NULL AND genre != ''
            GROUP BY genre 
            ORDER BY count DESC
        """)
        
        genres = cur.fetchall()
        for genre, count in genres[:10]:
            print(f"  {genre:20s}: {count:3d} tracks")
        
        # Check for 3 Doors Down specifically
        print("\n🔍 3 Doors Down Tracks:")
        cur.execute("""
            SELECT title, album, genre 
            FROM tracks 
            WHERE LOWER(artist) LIKE '%3 doors down%'
            ORDER BY title
        """)
        
        tracks = cur.fetchall()
        if tracks:
            print(f"  Found {len(tracks)} tracks:")
            for title, album, genre in tracks:
                print(f"    - {title} ({album}) - {genre}")
        else:
            print("  No 3 Doors Down tracks found")
        
        # Check for similar artists
        print("\n🔍 Similar Artists (same genre):")
        cur.execute("""
            SELECT DISTINCT artist 
            FROM tracks 
            WHERE genre = 'Rock' AND artist != '3 Doors Down'
            ORDER BY artist
            LIMIT 15
        """)
        
        similar = cur.fetchall()
        if similar:
            print("  Rock artists in library:")
            for artist, in similar:
                print(f"    - {artist}")
        else:
            print("  No other rock artists found")
        
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Check failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_local_rock_artists()
    sys.exit(0 if success else 1)
