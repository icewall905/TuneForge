#!/usr/bin/env python3
import requests
import json

PLEX_URL = "http://10.0.10.14:32400"
PLEX_TOKEN = "TQnt4Qsj3sNhcjJoSuvu"
SECTION_ID = "1"
HEADERS = {'X-Plex-Token': PLEX_TOKEN, 'Accept': 'application/json'}

def search(query):
    print(f"\nSearching for: '{query}'")
    params = {'type': '10', 'query': query, 'X-Plex-Token': PLEX_TOKEN}
    url = f"{PLEX_URL}/library/sections/{SECTION_ID}/search"
    
    try:
        resp = requests.get(url, headers=HEADERS, params=params)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            metadata = data.get('MediaContainer', {}).get('Metadata', [])
            print(f"Found {len(metadata)} results.")
            for item in metadata[:3]:
                print(f" - {item.get('title')} by {item.get('grandparentTitle')} (ID: {item.get('ratingKey')})")
        else:
            print(f"Error: {resp.text}")
    except Exception as e:
        print(f"Exception: {e}")

def search_global(query):
    print(f"\nGlobal Searching for: '{query}'")
    params = {'query': query, 'X-Plex-Token': PLEX_TOKEN}
    url = f"{PLEX_URL}/search"
    
    try:
        resp = requests.get(url, headers=HEADERS, params=params)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            # Global search returns Hubs
            hubs = data.get('MediaContainer', {}).get('Hub', [])
            found = 0
            for hub in hubs:
                if hub.get('type') == 'track':
                    metadata = hub.get('Metadata', [])
                    found += len(metadata)
                    for item in metadata[:3]:
                        print(f" - {item.get('title')} by {item.get('grandparentTitle')} (ID: {item.get('ratingKey')})")
            print(f"Found {found} track results in hubs.")
        else:
            print(f"Error: {resp.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    # Test with the query that failed
    search("Scar Tissue Red Hot Chili Peppers")
    search_global("Scar Tissue Red Hot Chili Peppers")
    
    # Test with simpler queries
    search("Scar Tissue")

