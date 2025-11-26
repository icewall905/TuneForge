#!/usr/bin/env python3
"""
Test script to verify Plex bulk track adding fix.
Tests that multiple tracks can be added to a playlist.
"""
import sys
sys.path.insert(0, '/opt/tuneforge')

from mcp_server import search_tracks, add_to_playlist, create_playlist
import json

print("=" * 60)
print("Testing Plex Bulk Track Add Fix")
print("=" * 60)

# Step 1: Search for tracks
print("\n1. Searching for U2 tracks in Plex...")
search_result = search_tracks("U2", platform="plex", limit=5)

try:
    tracks = json.loads(search_result)
    if not tracks:
        print("No tracks found. Test cannot continue.")
        sys.exit(1)
    
    print(f"   Found {len(tracks)} tracks:")
    for t in tracks[:5]:
        print(f"   - {t.get('title')} by {t.get('artist')} (ID: {t.get('id')})")
    
    track_ids = [t['id'] for t in tracks[:5]]
    print(f"\n   Track IDs to add: {track_ids}")

except json.JSONDecodeError:
    print(f"Error: Could not parse search results: {search_result}")
    sys.exit(1)

# Step 2: Create a new playlist with multiple tracks
print("\n2. Creating new Plex playlist with multiple tracks...")
result = add_to_playlist(
    playlist_id="NEW",
    track_ids=track_ids,
    platform="plex",
    playlist_name="Bulk Add Test"
)
print(f"   Result: {result}")

# Check if tracks were actually added
if "Successfully" in result and str(len(track_ids)) in result:
    print("\n" + "=" * 60)
    print("TEST PASSED: Multiple tracks were added!")
    print("=" * 60)
elif "Warning" in result or "0 tracks" in result:
    print("\n" + "=" * 60)
    print("TEST FAILED: Tracks were not added correctly")
    print("=" * 60)
else:
    print("\n" + "=" * 60)
    print("TEST INCONCLUSIVE: Check the result above")
    print("=" * 60)

# Step 3: Check the debug log for the actual request
print("\n3. Checking debug log for request format...")
import subprocess
log_check = subprocess.run(
    ["tail", "-20", "/opt/tuneforge/logs/mcp_debug.log"],
    capture_output=True, text=True
)
print(log_check.stdout)

