#!/usr/bin/env python3
"""
Test script to directly query Plex API and see what's happening with the search.
"""
import sys
import os
import json
import requests
import configparser

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def get_config_value(section, key, default=None):
    """Helper to read config.ini"""
    config = configparser.ConfigParser()
    config.optionxform = lambda optionstr: optionstr
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, '..', 'config.ini')
    
    if not os.path.exists(config_path):
        return default
        
    config.read(config_path)
    if config.has_section(section) and key in config[section]:
        return config[section][key]
    return default

url = get_config_value('PLEX', 'ServerURL')
token = get_config_value('PLEX', 'Token')
section_id = get_config_value('PLEX', 'MusicSectionID')

if not all([url, token, section_id]):
    print("Error: Plex not configured")
    sys.exit(1)

headers = {'X-Plex-Token': token, 'Accept': 'application/json'}

print("=" * 60)
print("Testing Plex API directly")
print("=" * 60)
print()

# Test 1: Search by artist (grandparentTitle)
print("Test 1: Search by artist (grandparentTitle='Oasis')")
print("-" * 60)
all_url = f"{url.rstrip('/')}/library/sections/{section_id}/all"
params = {'type': '10', 'grandparentTitle': 'Oasis', 'X-Plex-Token': token}
try:
    response = requests.get(all_url, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    metadata = data.get('MediaContainer', {}).get('Metadata', [])
    print(f"Found {len(metadata)} tracks")
    if metadata:
        for track in metadata[:5]:
            print(f"  - {track.get('title')} by {track.get('grandparentTitle')} (ID: {track.get('ratingKey')})")
    else:
        print("  No tracks found")
except Exception as e:
    print(f"  Error: {e}")

print()

# Test 2: General search
print("Test 2: General text search (query='Oasis')")
print("-" * 60)
search_url = f"{url.rstrip('/')}/library/sections/{section_id}/search"
params = {'type': '10', 'query': 'Oasis', 'X-Plex-Token': token}
try:
    response = requests.get(search_url, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    metadata = data.get('MediaContainer', {}).get('Metadata', [])
    print(f"Found {len(metadata)} tracks")
    if metadata:
        # Group by artist
        by_artist = {}
        for track in metadata:
            artist = track.get('grandparentTitle', 'Unknown')
            if artist not in by_artist:
                by_artist[artist] = []
            by_artist[artist].append(track)
        
        for artist, tracks in sorted(by_artist.items()):
            print(f"  {artist}: {len(tracks)} tracks")
            for track in tracks[:3]:
                print(f"    - {track.get('title')} (ID: {track.get('ratingKey')})")
            if len(tracks) > 3:
                print(f"    ... and {len(tracks) - 3} more")
except Exception as e:
    print(f"  Error: {e}")

print()

# Test 3: Try searching for a known Oasis track
print("Test 3: Search for known Oasis track 'Wonderwall'")
print("-" * 60)
params = {'type': '10', 'title': 'Wonderwall', 'X-Plex-Token': token}
try:
    response = requests.get(all_url, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    metadata = data.get('MediaContainer', {}).get('Metadata', [])
    print(f"Found {len(metadata)} tracks")
    if metadata:
        for track in metadata:
            print(f"  - {track.get('title')} by {track.get('grandparentTitle')} (ID: {track.get('ratingKey')})")
            print(f"    Artist in Plex: '{track.get('grandparentTitle')}'")
    else:
        print("  No tracks found")
except Exception as e:
    print(f"  Error: {e}")

print()

# Test 4: List all artists to see how Oasis is stored
print("Test 4: Check artists in library (first 50)")
print("-" * 60)
params = {'type': '8', 'X-Plex-Token': token}  # type 8 is artist
try:
    response = requests.get(all_url, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    metadata = data.get('MediaContainer', {}).get('Metadata', [])
    print(f"Found {len(metadata)} artists")
    # Look for Oasis
    oasis_artists = [a for a in metadata if 'oasis' in a.get('title', '').lower()]
    if oasis_artists:
        print("Artists matching 'oasis':")
        for artist in oasis_artists:
            print(f"  - '{artist.get('title')}' (ID: {artist.get('ratingKey')})")
    else:
        print("  No artists found matching 'oasis'")
        # Show first 20 artists
        print("\nFirst 20 artists in library:")
        for artist in metadata[:20]:
            print(f"  - {artist.get('title')}")
except Exception as e:
    print(f"  Error: {e}")

