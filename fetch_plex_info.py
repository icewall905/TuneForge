import requests
import xml.etree.ElementTree as ET
import sys
import getpass

def get_plex_info():
    print("\n=== Plex Configuration Helper ===\n")
    
    # 1. Get Plex URL
    plex_url = input("Enter your Plex Server URL [http://10.0.10.14:32400]: ").strip()
    if not plex_url:
        plex_url = "http://10.0.10.14:32400"
    
    # 2. Get Plex Token
    print("\nTo get your Plex Token:")
    print("1. Sign in to https://app.plex.tv")
    print("2. Find any media item in your library")
    print("3. Click the 3 dots (...) -> Get Info -> View XML")
    print("4. Look for 'X-Plex-Token' in the URL bar")
    print("   OR refer to: https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/")
    
    plex_token = getpass.getpass("\nEnter your Plex Token (input hidden): ").strip()
    
    if not plex_token:
        print("Error: Plex Token is required.")
        return

    headers = {
        'X-Plex-Token': plex_token,
        'Accept': 'application/json'
    }

    try:
        # 3. Get Machine ID (Identity)
        print(f"\nConnecting to {plex_url}...")
        identity_url = f"{plex_url}/identity"
        response = requests.get(identity_url, headers=headers, timeout=5)
        
        if response.status_code != 200:
            print(f"Error connecting to server: {response.status_code} {response.reason}")
            return

        identity_data = response.json()
        machine_id = identity_data.get('MediaContainer', {}).get('machineIdentifier')
        
        print("\n------------------------------------------------")
        print(f"✅ Plex Machine ID: {machine_id}")
        print("------------------------------------------------")

        # 4. Get Libraries (Sections)
        print("\nFetching Libraries...")
        sections_url = f"{plex_url}/library/sections"
        response = requests.get(sections_url, headers=headers, timeout=5)
        
        if response.status_code != 200:
            print(f"Error fetching libraries: {response.status_code} {response.reason}")
            return

        sections_data = response.json()
        directories = sections_data.get('MediaContainer', {}).get('Directory', [])
        
        print("\nAvailable Libraries:")
        print(f"{'ID':<5} | {'Type':<10} | {'Name'}")
        print("-" * 30)
        
        music_found = False
        for section in directories:
            sec_id = section.get('key')
            sec_type = section.get('type')
            sec_title = section.get('title')
            print(f"{sec_id:<5} | {sec_type:<10} | {sec_title}")
            
            if sec_type == 'artist': # Plex uses 'artist' type for music libraries
                music_found = True
                print(f"      ^ This looks like a Music library! Use ID: {sec_id}")

        print("------------------------------------------------")
        
        if not music_found:
            print("⚠️  No Music library found. Look for type 'artist'.")

        print("\nSummary for TuneForge Configuration:")
        print(f"Plex Server URL: {plex_url}")
        print(f"Plex Token:      {plex_token}")
        print(f"Plex Machine ID: {machine_id}")
        print(f"Plex Playlist Type: audio")
        print(f"Plex Music Library Section ID: [Enter the ID from the list above]")

    except Exception as e:
        print(f"\nError: {e}")
        print("Please verify your URL and Token.")

if __name__ == "__main__":
    get_plex_info()
