#!/usr/bin/env python3
"""
Test script to verify playlist creation in Plex and Navidrome via MCP service.
"""
import sys
import os
sys.path.insert(0, '/opt/tuneforge')

import requests
import configparser
from mcp_server import add_to_playlist, search_tracks, create_playlist

def get_config():
    """Load config.ini"""
    config = configparser.ConfigParser()
    config.optionxform = lambda optionstr: optionstr
    config_path = '/opt/tuneforge/config.ini'
    if os.path.exists(config_path):
        config.read(config_path)
    return config

def test_plex_playlist():
    """Test Plex playlist creation"""
    print("\n=== Testing Plex Playlist Creation ===")
    
    # First, search for a track
    print("1. Searching for a track in Plex...")
    search_result = search_tracks("test", platform="plex", limit=5)
    print(f"Search result: {search_result[:200]}...")
    
    # Parse the JSON to get a track ID
    import json
    try:
        tracks = json.loads(search_result)
        if not tracks:
            print("ERROR: No tracks found in Plex. Cannot test playlist creation.")
            return
        track_id = tracks[0]['id']
        print(f"2. Using track ID: {track_id}")
        
        # Create playlist with this track
        print("3. Creating playlist via add_to_playlist...")
        result = add_to_playlist(
            playlist_id="NEW",
            track_ids=[track_id],
            platform="plex",
            playlist_name="MCP Test Playlist Plex"
        )
        print(f"Result: {result}")
        
        # Verify playlist exists by checking Plex API
        config = get_config()
        url = config.get('PLEX', 'ServerURL', '')
        token = config.get('PLEX', 'Token', '')
        
        if url and token:
            headers = {'X-Plex-Token': token, 'Accept': 'application/json'}
            playlists_url = f"{url.rstrip('/')}/playlists"
            resp = requests.get(playlists_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                playlists = data.get('MediaContainer', {}).get('Metadata', [])
                test_playlists = [p for p in playlists if 'MCP Test' in p.get('title', '')]
                print(f"4. Found {len(test_playlists)} test playlists in Plex:")
                for p in test_playlists:
                    print(f"   - {p.get('title')} (ID: {p.get('ratingKey')}, Tracks: {p.get('leafCount', 0)})")
            else:
                print(f"4. ERROR: Could not fetch playlists: {resp.status_code}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

def test_navidrome_playlist():
    """Test Navidrome playlist creation"""
    print("\n=== Testing Navidrome Playlist Creation ===")
    
    # First, search for a track
    print("1. Searching for a track in Navidrome...")
    search_result = search_tracks("test", platform="navidrome", limit=5)
    print(f"Search result: {search_result[:200]}...")
    
    # Parse the JSON to get a track ID
    import json
    try:
        tracks = json.loads(search_result)
        if not tracks:
            print("ERROR: No tracks found in Navidrome. Cannot test playlist creation.")
            return
        track_id = tracks[0]['id']
        print(f"2. Using track ID: {track_id}")
        
        # Create playlist with this track
        print("3. Creating playlist via add_to_playlist...")
        result = add_to_playlist(
            playlist_id="NEW",
            track_ids=[track_id],
            platform="navidrome",
            playlist_name="MCP Test Playlist Navidrome"
        )
        print(f"Result: {result}")
        
        # Verify playlist exists by checking Navidrome API
        config = get_config()
        url = config.get('NAVIDROME', 'URL', '')
        user = config.get('NAVIDROME', 'Username', '')
        password = config.get('NAVIDROME', 'Password', '')
        
        if url and user and password:
            base_url = url.rstrip('/')
            if '/rest' not in base_url:
                base_url = f"{base_url}/rest"
            
            params = {
                'u': user, 'p': password, 'v': '1.16.1', 'c': 'TuneForge', 'f': 'json'
            }
            resp = requests.get(f"{base_url}/getPlaylists.view", params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                playlists = data.get('subsonic-response', {}).get('playlists', {}).get('playlist', [])
                if not isinstance(playlists, list):
                    playlists = [playlists] if playlists else []
                test_playlists = [p for p in playlists if 'MCP Test' in p.get('name', '')]
                print(f"4. Found {len(test_playlists)} test playlists in Navidrome:")
                for p in test_playlists:
                    print(f"   - {p.get('name')} (ID: {p.get('id')}, Tracks: {p.get('songCount', 0)})")
            else:
                print(f"4. ERROR: Could not fetch playlists: {resp.status_code} - {resp.text[:200]}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Testing MCP Playlist Creation")
    print("=" * 50)
    
    test_plex_playlist()
    test_navidrome_playlist()
    
    print("\n" + "=" * 50)
    print("Test complete. Check the results above.")

