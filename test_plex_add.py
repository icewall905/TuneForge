import requests

# Plex config
url = "http://10.0.10.14:32400"
token = "TQnt4Qsj3sNhcjJoSuvu"
machine_id = "d4e3b2b01d4ad0e86caa1dbcd438751ed360d0e7"

# Test: Get a playlist to see its current state
playlist_id = input("Enter Plex Playlist ID to test: ")
headers = {'X-Plex-Token': token, 'Accept': 'application/json'}

print(f"\n1. Getting current playlist {playlist_id}...")
resp = requests.get(f"{url}/playlists/{playlist_id}/items", headers=headers)
data = resp.json()
current_tracks = data.get('MediaContainer', {}).get('Metadata', [])
print(f"   Current tracks in playlist: {len(current_tracks)}")
for i, t in enumerate(current_tracks[:5]):
    print(f"   - {t.get('title')} by {t.get('grandparentTitle')}")

# Test track to add
track_id = input("\nEnter a Track ID (ratingKey) to add: ")

print(f"\n2. Testing PUT method (current implementation)...")
uri = f"server://{machine_id}/com.plexapp.plugins.library/library/metadata/{track_id}"
put_params = {'uri': uri, 'X-Plex-Token': token}
resp = requests.put(f"{url}/playlists/{playlist_id}/items", headers=headers, params=put_params)
print(f"   Response: {resp.status_code}")

print(f"\n3. Checking playlist after PUT...")
resp = requests.get(f"{url}/playlists/{playlist_id}/items", headers=headers)
data = resp.json()
after_tracks = data.get('MediaContainer', {}).get('Metadata', [])
print(f"   Tracks in playlist now: {len(after_tracks)}")
print(f"   ⚠️  PROBLEM: PUT replaced all tracks! Went from {len(current_tracks)} to {len(after_tracks)}")

