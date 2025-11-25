#!/usr/bin/env python3
"""
Script to find and delete all test playlists created during MCP testing.
"""
import sys
import os
sys.path.insert(0, '/opt/tuneforge')

import json
import requests
import configparser
from mcp_server import delete_playlist

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_section(title):
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{title:^70}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

def print_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}✗ {msg}{RESET}")

def print_info(msg):
    print(f"  {msg}")

def get_config():
    """Load config.ini"""
    config = configparser.ConfigParser()
    config.optionxform = lambda optionstr: optionstr
    config_path = '/opt/tuneforge/config.ini'
    if os.path.exists(config_path):
        config.read(config_path)
    return config

def get_navidrome_playlists():
    """Get all playlists from Navidrome"""
    config = get_config()
    url = config.get('NAVIDROME', 'URL') if config.has_section('NAVIDROME') and config.has_option('NAVIDROME', 'URL') else ''
    user = config.get('NAVIDROME', 'Username') if config.has_section('NAVIDROME') and config.has_option('NAVIDROME', 'Username') else ''
    password = config.get('NAVIDROME', 'Password') if config.has_section('NAVIDROME') and config.has_option('NAVIDROME', 'Password') else ''
    
    if not all([url, user, password]):
        return []
    
    try:
        base_url = url.rstrip('/')
        if '/rest' not in base_url:
            base_url = f"{base_url}/rest"
        
        params = {
            'u': user, 'p': password, 'v': '1.16.1', 'c': 'TuneForge', 'f': 'json'
        }
        resp = requests.get(f"{base_url}/getPlaylists.view", params=params, timeout=10)
        
        if resp.status_code != 200:
            return []
        
        data = resp.json()
        playlists = data.get('subsonic-response', {}).get('playlists', {}).get('playlist', [])
        if not isinstance(playlists, list):
            playlists = [playlists] if playlists else []
        
        return playlists
    except Exception as e:
        print_error(f"Error fetching Navidrome playlists: {e}")
        return []

def get_plex_playlists():
    """Get all playlists from Plex"""
    config = get_config()
    url = config.get('PLEX', 'ServerURL') if config.has_section('PLEX') and config.has_option('PLEX', 'ServerURL') else ''
    token = config.get('PLEX', 'Token') if config.has_section('PLEX') and config.has_option('PLEX', 'Token') else ''
    
    if not all([url, token]):
        return []
    
    try:
        headers = {'X-Plex-Token': token, 'Accept': 'application/json'}
        resp = requests.get(f"{url.rstrip('/')}/playlists", headers=headers, timeout=10)
        
        if resp.status_code != 200:
            return []
        
        data = resp.json()
        playlists = data.get('MediaContainer', {}).get('Metadata', [])
        return playlists
    except Exception as e:
        print_error(f"Error fetching Plex playlists: {e}")
        return []

def cleanup_navidrome_test_playlists():
    """Find and delete test playlists in Navidrome"""
    print_section("Cleaning Up Navidrome Test Playlists")
    
    playlists = get_navidrome_playlists()
    test_playlists = [p for p in playlists if 'MCP Test' in p.get('name', '')]
    
    if not test_playlists:
        print_info("No test playlists found in Navidrome")
        return 0
    
    print_info(f"Found {len(test_playlists)} test playlist(s) in Navidrome:")
    for p in test_playlists:
        print_info(f"  - {p.get('name')} (ID: {p.get('id')}, Tracks: {p.get('songCount', 0)})")
    
    deleted = 0
    for p in test_playlists:
        playlist_id = p.get('id')
        playlist_name = p.get('name', 'Unknown')
        
        print_info(f"Deleting: {playlist_name}...")
        result = delete_playlist(playlist_id, platform="navidrome")
        
        if result.startswith("Successfully"):
            print_success(f"Deleted: {playlist_name}")
            deleted += 1
        else:
            print_error(f"Failed to delete {playlist_name}: {result}")
    
    return deleted

def cleanup_plex_test_playlists():
    """Find and delete test playlists in Plex"""
    print_section("Cleaning Up Plex Test Playlists")
    
    playlists = get_plex_playlists()
    test_playlists = [p for p in playlists if 'MCP Test' in p.get('title', '')]
    
    if not test_playlists:
        print_info("No test playlists found in Plex")
        return 0
    
    print_info(f"Found {len(test_playlists)} test playlist(s) in Plex:")
    for p in test_playlists:
        print_info(f"  - {p.get('title')} (ID: {p.get('ratingKey')}, Tracks: {p.get('leafCount', 0)})")
    
    deleted = 0
    for p in test_playlists:
        playlist_id = p.get('ratingKey')
        playlist_name = p.get('title', 'Unknown')
        
        print_info(f"Deleting: {playlist_name}...")
        result = delete_playlist(playlist_id, platform="plex")
        
        if result.startswith("Successfully"):
            print_success(f"Deleted: {playlist_name}")
            deleted += 1
        else:
            print_error(f"Failed to delete {playlist_name}: {result}")
    
    return deleted

def main():
    print_section("Test Playlist Cleanup")
    
    navidrome_deleted = cleanup_navidrome_test_playlists()
    plex_deleted = cleanup_plex_test_playlists()
    
    print_section("Cleanup Summary")
    print_info(f"Navidrome: {navidrome_deleted} playlist(s) deleted")
    print_info(f"Plex: {plex_deleted} playlist(s) deleted")
    print_info(f"Total: {navidrome_deleted + plex_deleted} playlist(s) deleted")
    
    if navidrome_deleted + plex_deleted > 0:
        print_success("Cleanup completed!")
    else:
        print_info("No test playlists found to delete.")

if __name__ == "__main__":
    main()

