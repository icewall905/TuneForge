#!/usr/bin/env python3
"""
Test script to verify Plex search for "Oasis" returns tracks by the band Oasis.
"""
import sys
import os
import json

# Add the parent directory to the Python path to import mcp_server
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mcp_server import search_tracks

print("=" * 60)
print("Testing Plex search for 'Oasis'")
print("=" * 60)
print()

# Test search for "Oasis"
print("Searching for 'Oasis' in Plex...")
result = search_tracks(query="Oasis", platform="plex", limit=20)

try:
    tracks = json.loads(result)
    if isinstance(tracks, list):
        print(f"✓ Found {len(tracks)} tracks")
        print()
        
        # Check if we found tracks by the band Oasis
        oasis_band_tracks = [t for t in tracks if t.get('artist', '').lower() == 'oasis']
        other_tracks = [t for t in tracks if t.get('artist', '').lower() != 'oasis']
        
        if oasis_band_tracks:
            print(f"✓ Found {len(oasis_band_tracks)} tracks by the band Oasis:")
            for track in oasis_band_tracks[:10]:  # Show first 10
                print(f"  - {track.get('title')} by {track.get('artist')} (ID: {track.get('id')})")
            if len(oasis_band_tracks) > 10:
                print(f"  ... and {len(oasis_band_tracks) - 10} more")
        else:
            print("✗ No tracks found by the band Oasis")
        
        if other_tracks:
            print()
            print(f"⚠ Also found {len(other_tracks)} tracks by other artists:")
            for track in other_tracks[:5]:  # Show first 5
                print(f"  - {track.get('title')} by {track.get('artist')} (ID: {track.get('id')})")
            if len(other_tracks) > 5:
                print(f"  ... and {len(other_tracks) - 5} more")
        
        print()
        if oasis_band_tracks:
            print("=" * 60)
            print("✓ Test PASSED: Found tracks by the band Oasis")
            print("=" * 60)
        else:
            print("=" * 60)
            print("✗ Test FAILED: No tracks by the band Oasis found")
            print("=" * 60)
            sys.exit(1)
    else:
        print(f"✗ Unexpected result format: {result}")
        sys.exit(1)
except json.JSONDecodeError:
    print(f"✗ Error parsing result: {result}")
    sys.exit(1)

