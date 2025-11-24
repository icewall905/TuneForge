def update_create_playlist_function():
    """Create a modified version of the create_playlist_in_navidrome function"""
    
    code = """def create_playlist_in_navidrome(playlist_name, track_ids, navidrome_url, username, password):
    # Process the URL to ensure it's correctly formatted
    if not navidrome_url:
        print("Navidrome URL is not configured")
        return None
        
    # Remove trailing slash if present
    base_url = navidrome_url.rstrip('/')
    
    # Check if URL already has /rest path - don't add it if it's already there
    if '/rest' not in base_url:
        base_url = f"{base_url}/rest"
    
    # URL encode parameters
    encoded_username = requests.utils.quote(username)
    encoded_password = requests.utils.quote(password)
    encoded_playlist_name = requests.utils.quote(playlist_name)
    
    # Start with the base URL and standard parameters
    url = f"{base_url}/createPlaylist.view"
    params = {
        'u': username,
        'p': password,
        'v': '1.16.1',
        'c': 'flask-ollama-playlist',
        'f': 'json',
        'name': playlist_name
    }
    
    # Add songId parameters for each track
    if track_ids:
        # Use a list for multiple values with the same key
        # requests will handle this correctly in the URL
        if not isinstance(track_ids, list):
            track_ids = [track_ids]
            
        params['songId'] = track_ids
        
    print(f"DEBUG: Creating Navidrome playlist '{playlist_name}' with {len(track_ids) if track_ids else 0} tracks")
    
    try:
        # Use params argument instead of building URL manually
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        print(f"DEBUG: Full playlist creation URL: {response.url}")
        
        data = response.json()
        print(f"DEBUG: Navidrome create playlist response: {json.dumps(data, indent=2)}")
        
        if data.get('subsonic-response', {}).get('status') == 'ok':
            playlist_id = data['subsonic-response'].get('playlist', {}).get('id')
            print(f"DEBUG: Successfully created Navidrome playlist with ID: {playlist_id}")
            return playlist_id
        else:
            error_message = data.get('subsonic-response', {}).get('error', {}).get('message')
            print(f"Error creating Navidrome playlist: {error_message}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error creating Navidrome playlist: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding Navidrome playlist JSON response: {e}")
        return None"""
    
    return code
