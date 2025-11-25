#!/usr/bin/env python3
import requests
import sys
import time

PLEX_URL = "http://10.0.10.14:32400"
PLEX_TOKEN = "TQnt4Qsj3sNhcjJoSuvu"
MACHINE_ID = "d4e3b2b01d4ad0e86caa1dbcd438751ed360d0e7"
HEADERS = {'X-Plex-Token': PLEX_TOKEN, 'Accept': 'application/json'}

def get_first_track():
    """Get a valid track ID to use for testing."""
    url = f"{PLEX_URL}/library/sections/1/all?type=10&X-Plex-Token={PLEX_TOKEN}&X-Plex-Container-Start=0&X-Plex-Container-Size=5"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        print(f"Failed to get tracks: {resp.status_code}")
        return None
    data = resp.json()
    tracks = data.get('MediaContainer', {}).get('Metadata', [])
    if not tracks:
        print("No tracks found.")
        return None
    return tracks

def create_playlist(name, track_id):
    """Create a new playlist with one track."""
    print(f"Creating playlist '{name}'...")
    uri = f"server://{MACHINE_ID}/com.plexapp.plugins.library/library/metadata/{track_id}"
    params = {'type': 'audio', 'title': name, 'smart': '0', 'uri': uri, 'X-Plex-Token': PLEX_TOKEN}
    resp = requests.post(f"{PLEX_URL}/playlists", headers=HEADERS, params=params)
    if resp.status_code != 200:
        print(f"Failed to create playlist: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    playlist = data.get('MediaContainer', {}).get('Metadata', [])[0]
    print(f"Created playlist ID: {playlist['ratingKey']}")
    return playlist['ratingKey']

def check_playlist(playlist_id):
    """Return number of items in playlist."""
    resp = requests.get(f"{PLEX_URL}/playlists/{playlist_id}/items", headers=HEADERS)
    data = resp.json()
    count = data.get('MediaContainer', {}).get('leafCount', 0)
    print(f"Playlist {playlist_id} has {count} items.")
    return count

def test_add_methods():
    tracks = get_first_track()
    if not tracks or len(tracks) < 2:
        print("Need at least 2 tracks to test.")
        return

    t1 = tracks[0]['ratingKey']
    t2 = tracks[1]['ratingKey']
    print(f"Track 1: {t1}, Track 2: {t2}")

    # Test 1: PUT
    pid_put = create_playlist("TuneForge_Test_PUT", t1)
    if pid_put:
        print("\n--- Testing PUT ---")
        check_playlist(pid_put)
        uri = f"server://{MACHINE_ID}/com.plexapp.plugins.library/library/metadata/{t2}"
        print(f"Adding track {t2} using PUT...")
        params = {'uri': uri, 'X-Plex-Token': PLEX_TOKEN}
        resp = requests.put(f"{PLEX_URL}/playlists/{pid_put}/items", headers=HEADERS, params=params)
        print(f"PUT Status: {resp.status_code}")
        count = check_playlist(pid_put)
        if count == 1:
            print("RESULT: PUT replaced the playlist (FAIL)")
        elif count == 2:
            print("RESULT: PUT appended to playlist (SUCCESS)")
        else:
            print(f"RESULT: Unexpected count {count}")

    # Test 2: POST
    pid_post = create_playlist("TuneForge_Test_POST", t1)
    if pid_post:
        print("\n--- Testing POST ---")
        check_playlist(pid_post)
        uri = f"server://{MACHINE_ID}/com.plexapp.plugins.library/library/metadata/{t2}"
        print(f"Adding track {t2} using POST...")
        params = {'uri': uri, 'X-Plex-Token': PLEX_TOKEN}
        resp = requests.post(f"{PLEX_URL}/playlists/{pid_post}/items", headers=HEADERS, params=params)
        print(f"POST Status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"POST Error: {resp.text}")
        count = check_playlist(pid_post)
        if count == 2:
            print("RESULT: POST appended to playlist (SUCCESS)")
        else:
            print(f"RESULT: POST failed (count {count})")

if __name__ == "__main__":
    test_add_methods()
