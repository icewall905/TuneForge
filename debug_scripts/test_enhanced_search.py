#!/usr/bin/env python3
"""
Test script to verify enhanced search_tracks functionality with genres, artists, and various queries.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server import search_tracks
import json

def test_search(query, platform, description):
    """Test a search query and display results."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Query: '{query}' on {platform}")
    print(f"{'='*60}")
    
    result = search_tracks(query, platform, limit=10)
    
    try:
        tracks = json.loads(result)
        if isinstance(tracks, list):
            print(f"Found {len(tracks)} tracks:")
            for i, track in enumerate(tracks[:5], 1):  # Show first 5
                print(f"  {i}. {track.get('title', 'N/A')} by {track.get('artist', 'N/A')} (ID: {track.get('id', 'N/A')})")
            if len(tracks) > 5:
                print(f"  ... and {len(tracks) - 5} more")
        else:
            print(f"Result: {result}")
    except json.JSONDecodeError:
        print(f"Error or non-JSON result: {result}")

if __name__ == "__main__":
    print("Testing Enhanced search_tracks Functionality")
    print("=" * 60)
    
    # Test various query types
    test_cases = [
        # Genre searches
        ("classic rock", "plex", "Genre search: classic rock"),
        ("jazz", "plex", "Genre search: jazz"),
        ("classic rock", "navidrome", "Genre search: classic rock (Navidrome)"),
        
        # Artist searches
        ("Oasis", "plex", "Artist search: Oasis"),
        ("The Beatles", "plex", "Artist search: The Beatles"),
        
        # Title searches
        ("Wonderwall", "plex", "Title search: Wonderwall"),
        
        # Keyword/tag searches
        ("80s", "plex", "Keyword search: 80s"),
    ]
    
    for query, platform, description in test_cases:
        test_search(query, platform, description)
    
    print(f"\n{'='*60}")
    print("Testing complete!")
    print(f"{'='*60}")

