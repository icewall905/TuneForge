#!/usr/bin/env python3
"""Test different methods for adding tracks to Plex playlist."""
import requests

PLEX_URL = "http://10.0.10.14:32400"
PLEX_TOKEN = "TQnt4Qsj3sNhcjJoSuvu"
MACHINE_ID = "d4e3b2b01d4ad0e86caa1dbcd438751ed360d0e7"

headers = {'X-Plex-Token': PLEX_TOKEN, 'Accept': 'application/json'}

playlist_id = input("Enter Playlist ID: ").strip()
track_id = input("Enter Track ID to add: ").strip()

uri = f"server://{MACHINE_ID}/com.plexapp.plugins.library/library/metadata/{track_id}"

print("\n=== Testing POST method ===")
try:
    params = {'uri': uri, 'X-Plex-Token': PLEX_TOKEN}
    resp = requests.post(f"{PLEX_URL}/playlists/{playlist_id}/items", headers=headers, params=params)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

print("\n=== Testing PUT method ===")
try:
    params = {'uri': uri, 'X-Plex-Token': PLEX_TOKEN}
    resp = requests.put(f"{PLEX_URL}/playlists/{playlist_id}/items", headers=headers, params=params)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

print("\n=== Testing POST with uri in data instead of params ===")
try:
    data = {'uri': uri}
    params = {'X-Plex-Token': PLEX_TOKEN}
    resp = requests.post(f"{PLEX_URL}/playlists/{playlist_id}/items", headers=headers, params=params, data=data)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
