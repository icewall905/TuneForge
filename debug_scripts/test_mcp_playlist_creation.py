#!/usr/bin/env python3
"""
Comprehensive test script for MCP playlist creation in Plex and Navidrome.
Tests both add_to_playlist and create_playlist functions.
"""
import sys
import os
sys.path.insert(0, '/opt/tuneforge')

import json
import requests
import configparser
from datetime import datetime
from mcp_server import add_to_playlist, create_playlist, search_tracks

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{title:^70}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

def print_success(msg):
    """Print success message"""
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg):
    """Print error message"""
    print(f"{RED}✗ {msg}{RESET}")

def print_warning(msg):
    """Print warning message"""
    print(f"{YELLOW}⚠ {msg}{RESET}")

def print_info(msg):
    """Print info message"""
    print(f"  {msg}")

def get_config():
    """Load config.ini"""
    config = configparser.ConfigParser()
    config.optionxform = lambda optionstr: optionstr
    config_path = '/opt/tuneforge/config.ini'
    if os.path.exists(config_path):
        config.read(config_path)
    return config

def test_navidrome_search():
    """Test Navidrome track search"""
    print_section("Testing Navidrome Track Search")
    
    try:
        print_info("Searching for tracks in Navidrome...")
        result = search_tracks("test", platform="navidrome", limit=5)
        
        if result.startswith("Error:"):
            print_error(f"Search failed: {result}")
            return None
        
        tracks = json.loads(result)
        if not tracks:
            print_warning("No tracks found in Navidrome. Cannot test playlist creation.")
            return None
        
        print_success(f"Found {len(tracks)} tracks")
        for i, track in enumerate(tracks[:3], 1):
            print_info(f"  {i}. {track.get('title', 'Unknown')} by {track.get('artist', 'Unknown')} (ID: {track.get('id')})")
        
        return tracks[0]['id'] if tracks else None
        
    except Exception as e:
        print_error(f"Exception during search: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_plex_search():
    """Test Plex track search"""
    print_section("Testing Plex Track Search")
    
    try:
        print_info("Searching for tracks in Plex...")
        result = search_tracks("test", platform="plex", limit=5)
        
        if result.startswith("Error:"):
            print_error(f"Search failed: {result}")
            return None
        
        tracks = json.loads(result)
        if not tracks:
            print_warning("No tracks found in Plex. Cannot test playlist creation.")
            return None
        
        print_success(f"Found {len(tracks)} tracks")
        for i, track in enumerate(tracks[:3], 1):
            print_info(f"  {i}. {track.get('title', 'Unknown')} by {track.get('artist', 'Unknown')} (ID: {track.get('id')})")
        
        return tracks[0]['id'] if tracks else None
        
    except Exception as e:
        print_error(f"Exception during search: {e}")
        import traceback
        traceback.print_exc()
        return None

def verify_navidrome_playlist(playlist_name):
    """Verify playlist exists in Navidrome"""
    config = get_config()
    url = config.get('NAVIDROME', 'URL') if config.has_section('NAVIDROME') and config.has_option('NAVIDROME', 'URL') else ''
    user = config.get('NAVIDROME', 'Username') if config.has_section('NAVIDROME') and config.has_option('NAVIDROME', 'Username') else ''
    password = config.get('NAVIDROME', 'Password') if config.has_section('NAVIDROME') and config.has_option('NAVIDROME', 'Password') else ''
    
    if not all([url, user, password]):
        print_warning("Cannot verify: Navidrome not configured")
        return False
    
    try:
        base_url = url.rstrip('/')
        if '/rest' not in base_url:
            base_url = f"{base_url}/rest"
        
        params = {
            'u': user, 'p': password, 'v': '1.16.1', 'c': 'TuneForge', 'f': 'json'
        }
        resp = requests.get(f"{base_url}/getPlaylists.view", params=params, timeout=10)
        
        if resp.status_code != 200:
            print_error(f"Failed to fetch playlists: {resp.status_code}")
            return False
        
        data = resp.json()
        playlists = data.get('subsonic-response', {}).get('playlists', {}).get('playlist', [])
        if not isinstance(playlists, list):
            playlists = [playlists] if playlists else []
        
        matching = [p for p in playlists if playlist_name in p.get('name', '')]
        if matching:
            p = matching[0]
            print_success(f"Playlist found: '{p.get('name')}' (ID: {p.get('id')}, Tracks: {p.get('songCount', 0)})")
            return True
        else:
            print_error(f"Playlist '{playlist_name}' not found in Navidrome")
            return False
            
    except Exception as e:
        print_error(f"Exception verifying playlist: {e}")
        return False

def verify_plex_playlist(playlist_name):
    """Verify playlist exists in Plex"""
    config = get_config()
    url = config.get('PLEX', 'ServerURL') if config.has_section('PLEX') and config.has_option('PLEX', 'ServerURL') else ''
    token = config.get('PLEX', 'Token') if config.has_section('PLEX') and config.has_option('PLEX', 'Token') else ''
    
    if not all([url, token]):
        print_warning("Cannot verify: Plex not configured")
        return False
    
    try:
        headers = {'X-Plex-Token': token, 'Accept': 'application/json'}
        resp = requests.get(f"{url.rstrip('/')}/playlists", headers=headers, timeout=10)
        
        if resp.status_code != 200:
            print_error(f"Failed to fetch playlists: {resp.status_code}")
            return False
        
        data = resp.json()
        playlists = data.get('MediaContainer', {}).get('Metadata', [])
        
        matching = [p for p in playlists if playlist_name in p.get('title', '')]
        if matching:
            p = matching[0]
            print_success(f"Playlist found: '{p.get('title')}' (ID: {p.get('ratingKey')}, Tracks: {p.get('leafCount', 0)})")
            return True
        else:
            print_error(f"Playlist '{playlist_name}' not found in Plex")
            return False
            
    except Exception as e:
        print_error(f"Exception verifying playlist: {e}")
        return False

def test_navidrome_create_playlist():
    """Test Navidrome empty playlist creation"""
    print_section("Testing Navidrome create_playlist (Empty Playlist)")
    
    playlist_name = f"MCP Test Empty Navidrome {datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        print_info(f"Creating empty playlist: '{playlist_name}'")
        result = create_playlist(playlist_name, platform="navidrome")
        
        if result.startswith("Error:") or result.startswith("Navidrome Error:"):
            print_error(f"Failed: {result}")
            return False
        
        print_success(f"Creation reported success: {result}")
        
        # Verify playlist exists
        print_info("Verifying playlist exists...")
        if verify_navidrome_playlist(playlist_name):
            return True
        else:
            return False
            
    except Exception as e:
        print_error(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_navidrome_add_to_playlist_new():
    """Test Navidrome playlist creation via add_to_playlist"""
    print_section("Testing Navidrome add_to_playlist (Create New)")
    
    # Get a track ID first
    track_id = test_navidrome_search()
    if not track_id:
        print_error("Cannot test: No track ID available")
        return False
    
    playlist_name = f"MCP Test Navidrome {datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        print_info(f"Creating playlist '{playlist_name}' with track ID: {track_id}")
        result = add_to_playlist(
            playlist_id="NEW",
            track_ids=[track_id],
            platform="navidrome",
            playlist_name=playlist_name
        )
        
        if result.startswith("Error:") or result.startswith("Navidrome Error:"):
            print_error(f"Failed: {result}")
            return False
        
        print_success(f"Creation reported success: {result}")
        
        # Verify playlist exists
        print_info("Verifying playlist exists...")
        if verify_navidrome_playlist(playlist_name):
            return True
        else:
            return False
            
    except Exception as e:
        print_error(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_plex_add_to_playlist_new():
    """Test Plex playlist creation via add_to_playlist"""
    print_section("Testing Plex add_to_playlist (Create New)")
    
    # Get a track ID first
    track_id = test_plex_search()
    if not track_id:
        print_error("Cannot test: No track ID available")
        return False
    
    playlist_name = f"MCP Test Plex {datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        print_info(f"Creating playlist '{playlist_name}' with track ID: {track_id}")
        result = add_to_playlist(
            playlist_id="NEW",
            track_ids=[track_id],
            platform="plex",
            playlist_name=playlist_name
        )
        
        if result.startswith("Error:") or result.startswith("Plex Error:"):
            print_error(f"Failed: {result}")
            return False
        
        print_success(f"Creation reported success: {result}")
        
        # Verify playlist exists
        print_info("Verifying playlist exists...")
        if verify_plex_playlist(playlist_name):
            return True
        else:
            print_warning("Playlist created but not found in API. This might be a visibility/permissions issue.")
            return False
            
    except Exception as e:
        print_error(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print_section("MCP Playlist Creation Test Suite")
    print_info(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        'navidrome_search': False,
        'plex_search': False,
        'navidrome_create_empty': False,
        'navidrome_add_new': False,
        'plex_add_new': False
    }
    
    # Test searches first
    navidrome_track = test_navidrome_search()
    results['navidrome_search'] = navidrome_track is not None
    
    plex_track = test_plex_search()
    results['plex_search'] = plex_track is not None
    
    # Test Navidrome playlist creation
    if results['navidrome_search']:
        results['navidrome_create_empty'] = test_navidrome_create_playlist()
        results['navidrome_add_new'] = test_navidrome_add_to_playlist_new()
    
    # Test Plex playlist creation
    if results['plex_search']:
        results['plex_add_new'] = test_plex_add_to_playlist_new()
    
    # Print summary
    print_section("Test Summary")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, result in results.items():
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  {test_name:30} {status}")
    
    print(f"\n{BLUE}Results: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print_success("All tests passed!")
        return 0
    else:
        print_error("Some tests failed. Review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

