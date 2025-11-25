import requests
import configparser
import os

# Read config
config = configparser.ConfigParser()
config.read('/opt/tuneforge/config.ini')

url = config['PLEX']['ServerURL']
token = config['PLEX']['Token']
machine_id = config['PLEX']['MachineID']

print(f"URL: {url}")
print(f"MachineID: {machine_id}")

# Mock track IDs (need valid ones from Plex)
# First, search for a track to get a valid ID
headers = {'X-Plex-Token': token, 'Accept': 'application/json'}
search_url = f"{url.rstrip('/')}/search"
params = {'query': 'Red Hot Chili Peppers', 'type': '10'} # type 10 is track
resp = requests.get(search_url, headers=headers, params=params)
data = resp.json()

if not data.get('MediaContainer', {}).get('Metadata'):
    print("No tracks found to test with.")
    exit(1)

track_id = data['MediaContainer']['Metadata'][0]['ratingKey']
print(f"Found track ID: {track_id}")

# Test Create Playlist Logic
playlist_name = "Test Playlist MCP Debug"
first_track = track_id

uri = f"server://{machine_id}/com.plexapp.plugins.library/library/metadata/{first_track}"
params = {'type': 'audio', 'title': playlist_name, 'smart': '0', 'uri': uri, 'X-Plex-Token': token}

print(f"Attempting to create playlist with params: {params}")

try:
    resp = requests.post(f"{url.rstrip('/')}/playlists", headers=headers, params=params)
    print(f"Response Status: {resp.status_code}")
    print(f"Response Body: {resp.text}")
    resp.raise_for_status()
    print("Playlist created successfully!")
except Exception as e:
    print(f"Error creating playlist: {e}")
