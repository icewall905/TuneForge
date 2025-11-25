#!/usr/bin/env python3
"""
Test script to verify Navidrome add_to_playlist functionality
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server import search_tracks, add_to_playlist
import json

print("=" * 60)
print("Testing Navidrome add_to_playlist")
print("=" * 60)

# Step 1: Search for some tracks
print("\n1. Searching for tracks in Navidrome...")
search_result = search_tracks("U2", platform="navidrome", limit=3)
print(f"Search result: {search_result[:200]}...")

try:
    tracks = json.loads(search_result)
    if not tracks:
        print("❌ No tracks found. Cannot test add_to_playlist.")
        sys.exit(1)
    
    track_ids = [t['id'] for t in tracks[:3]]
    print(f"\n✓ Found {len(track_ids)} tracks: {[t['title'] for t in tracks[:3]]}")
    print(f"  Track IDs: {track_ids}")
    
    # Step 2: Create a new playlist with tracks
    print("\n2. Creating new playlist with tracks...")
    result = add_to_playlist(
        playlist_id="NEW",
        track_ids=track_ids,
        platform="navidrome",
        playlist_name="MCP Test - Add Tracks"
    )
    print(f"Result: {result}")
    
    if "Successfully created" in result or "Successfully added" in result:
        print("✓ Test passed!")
    else:
        print(f"❌ Test failed: {result}")
        sys.exit(1)
        
except json.JSONDecodeError as e:
    print(f"❌ Error parsing search results: {e}")
    print(f"Raw result: {search_result}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("Test completed successfully!")
print("=" * 60)

