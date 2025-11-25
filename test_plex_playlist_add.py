#!/usr/bin/env python3
"""
Quick test to verify Plex playlist adding works correctly.
This demonstrates the fix for the add_to_playlist function.
"""
import requests

# Plex configuration
PLEX_URL = "http://10.0.10.14:32400"
PLEX_TOKEN = "TQnt4Qsj3sNhcjJoSuvu"
MACHINE_ID = "d4e3b2b01d4ad0e86caa1dbcd438751ed360d0e7"

def get_playlist_tracks(playlist_id):
    """Get current tracks in a playlist."""
    headers = {'X-Plex-Token': PLEX_TOKEN, 'Accept': 'application/json'}
    resp = requests.get(f"{PLEX_URL}/playlists/{playlist_id}/items", headers=headers)
    data = resp.json()
    return data.get('MediaContainer', {}).get('Metadata', [])

def add_tracks_to_playlist(playlist_id, track_ids):
    """Add tracks to playlist using the FIXED method."""
    headers = {'X-Plex-Token': PLEX_TOKEN, 'Accept': 'application/json'}
    
    items_uris = [f"server://{MACHINE_ID}/com.plexapp.plugins.library/library/metadata/{tid}" for tid in track_ids]
    
    # CRITICAL: Include playlistID parameter to ADD (not replace)
    put_params = {
        'uri': ','.join(items_uris),
        'playlistID': playlist_id,  # This is the fix!
        'X-Plex-Token': PLEX_TOKEN
    }
    
    resp = requests.put(f"{PLEX_URL}/playlists/{playlist_id}/items", headers=headers, params=put_params)
    resp.raise_for_status()
    return resp

if __name__ == "__main__":
    print("Plex Playlist Add Test")
    print("=" * 50)
    print("\nThis script demonstrates the fix for adding tracks to Plex playlists.")
    print("\nThe FIX: Include 'playlistID' parameter in PUT request")
    print("  - Without it: PUT replaces all tracks")
    print("  - With it: PUT adds/appends tracks\n")
    
    playlist_id = input("Enter Playlist ID to test: ").strip()
    
    print(f"\n1. Getting current playlist state...")
    before = get_playlist_tracks(playlist_id)
    print(f"   Tracks before: {len(before)}")
    if before:
        print(f"   First track: {before[0].get('title')} by {before[0].get('grandparentTitle')}")
    
    track_id = input("\n2. Enter a Track ID (ratingKey) to add: ").strip()
    
    print(f"\n3. Adding track {track_id} to playlist...")
    add_tracks_to_playlist(playlist_id, [track_id])
    print("   ✓ Added successfully")
    
    print(f"\n4. Verifying playlist state...")
    after = get_playlist_tracks(playlist_id)
    print(f"   Tracks after: {len(after)}")
    print(f"   Change: +{len(after) - len(before)} tracks")
    
    if len(after) == len(before) + 1:
        print("\n   ✅ SUCCESS: Track was ADDED (not replaced)")
    elif len(after) == 1:
        print("\n   ❌ FAILURE: All tracks were REPLACED (bug not fixed)")
    else:
        print(f"\n   ⚠️  UNEXPECTED: Went from {len(before)} to {len(after)} tracks")
