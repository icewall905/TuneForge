from flask import Blueprint, render_template, request, jsonify, Response, current_app
import requests
import json
import configparser
import os
import datetime
import time
import re
import random
import xml.etree.ElementTree as ET

# --- Global Debug Flags ---
DEBUG_ENABLED = True  # Master debug switch
DEBUG_OLLAMA_RESPONSE = False  # Specific for Ollama response logging

main_bp = Blueprint('main', __name__)

CONFIG_FILE = 'config.ini'
HISTORY_FILE = 'playlist_history.json' # Added HISTORY_FILE

def load_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return config

def get_config_value(section, key, default=None):
    """Get a value from the config, case-insensitive for keys"""
    config = load_config()
    if section in config:
        # Find the key case-insensitively
        for config_key in config[section]:
            if config_key.lower() == key.lower():
                return config[section][config_key]
    return default

def load_playlist_history():
    """Load playlist history from the JSON file."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r') as f:
            history_data = json.load(f)
            # Ensure history_data is a list, even if the file contained a single dict or was empty
            if isinstance(history_data, dict): # Handles case where a single playlist might have been saved directly
                return [history_data]
            elif not isinstance(history_data, list): # Handles empty or malformed file
                 return []
            return history_data
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {HISTORY_FILE}")
        return []
    except Exception as e:
        print(f"An error occurred while loading playlist history: {e}")
        return []

def debug_log(message, level="INFO", force=False):
    """Unified debug logging function that respects config settings"""
    global DEBUG_ENABLED
    
    # Check if debug is enabled in config (overrides global setting)
    debug_from_config = get_config_value('APP', 'Debug', 'no').lower() in ('yes', 'true', '1')
    
    if debug_from_config or DEBUG_ENABLED or force:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/history')
def history():
    playlist_history = load_playlist_history()
    return render_template('history.html', history=playlist_history)

@main_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        config = load_config()
        # OLLAMA section
        config.set('OLLAMA', 'URL', request.form.get('ollama_url', get_config_value('OLLAMA', 'URL', '')))
        config.set('OLLAMA', 'Model', request.form.get('ollama_model', get_config_value('OLLAMA', 'Model', '')))
        config.set('OLLAMA', 'ContextWindow', request.form.get('context_window', get_config_value('OLLAMA', 'ContextWindow', '2048')))
        config.set('OLLAMA', 'MaxAttempts', request.form.get('max_attempts', get_config_value('OLLAMA', 'MaxAttempts', '3')))

        # APP section (Music Preferences & Platform Selection)
        if not config.has_section('APP'): config.add_section('APP')
        config.set('APP', 'Likes', request.form.get('likes', get_config_value('APP', 'Likes', '')))
        config.set('APP', 'Dislikes', request.form.get('dislikes', get_config_value('APP', 'Dislikes', '')))
        config.set('APP', 'FavoriteArtists', request.form.get('favorite_artists', get_config_value('APP', 'FavoriteArtists', '')))
        config.set('APP', 'EnableNavidrome', request.form.get('enable_navidrome', get_config_value('APP', 'EnableNavidrome', 'no')))
        config.set('APP', 'EnablePlex', request.form.get('enable_plex', get_config_value('APP', 'EnablePlex', 'no')))

        # NAVIDROME section
        if not config.has_section('NAVIDROME'): config.add_section('NAVIDROME')
        config.set('NAVIDROME', 'URL', request.form.get('navidrome_url', get_config_value('NAVIDROME', 'URL', '')))
        config.set('NAVIDROME', 'Username', request.form.get('navidrome_username', get_config_value('NAVIDROME', 'Username', '')))
        config.set('NAVIDROME', 'Password', request.form.get('navidrome_password', get_config_value('NAVIDROME', 'Password', '')))
        
        # PLEX section
        if not config.has_section('PLEX'): config.add_section('PLEX')
        config.set('PLEX', 'ServerURL', request.form.get('plex_server_url', get_config_value('PLEX', 'ServerURL', '')))
        config.set('PLEX', 'Token', request.form.get('plex_token', get_config_value('PLEX', 'Token', '')))
        config.set('PLEX', 'MachineID', request.form.get('plex_machine_id', get_config_value('PLEX', 'MachineID', '')))
        config.set('PLEX', 'PlaylistType', request.form.get('plex_playlist_type', get_config_value('PLEX', 'PlaylistType', 'audio')))
        config.set('PLEX', 'MusicSectionID', request.form.get('plex_music_section_id', get_config_value('PLEX', 'MusicSectionID', '')))

        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
        # The JavaScript on settings.html expects a JSON response for fetch
        return jsonify({'status': 'success', 'message': 'Settings saved successfully!'})

    # GET request: Load settings and display them
    context = {
        'ollama_url': get_config_value('OLLAMA', 'URL', 'http://localhost:11434'),
        'ollama_model': get_config_value('OLLAMA', 'Model', 'llama3'),
        'context_window': get_config_value('OLLAMA', 'ContextWindow', '2048'),
        'max_attempts': get_config_value('OLLAMA', 'MaxAttempts', '3'),
        'likes': get_config_value('APP', 'Likes', ''),
        'dislikes': get_config_value('APP', 'Dislikes', ''),
        'favorite_artists': get_config_value('APP', 'FavoriteArtists', ''),
        'enable_navidrome': get_config_value('APP', 'EnableNavidrome', 'no'),
        'enable_plex': get_config_value('APP', 'EnablePlex', 'no'),
        'navidrome_url': get_config_value('NAVIDROME', 'URL', ''),
        'navidrome_username': get_config_value('NAVIDROME', 'Username', ''),
        'navidrome_password': get_config_value('NAVIDROME', 'Password', ''),
        'plex_server_url': get_config_value('PLEX', 'ServerURL', ''),
        'plex_token': get_config_value('PLEX', 'Token', ''),
        'plex_machine_id': get_config_value('PLEX', 'MachineID', ''),
        'plex_playlist_type': get_config_value('PLEX', 'PlaylistType', 'audio'),
        'plex_music_section_id': get_config_value('PLEX', 'MusicSectionID', '')
    }
    return render_template('settings.html', **context)

@main_bp.route('/test-navidrome')
def test_navidrome_page():
    return render_template('test_navidrome.html')

@main_bp.route('/api/test-navidrome-connection', methods=['POST'])
def api_test_navidrome_connection():
    data = request.json
    navidrome_url = data.get('navidrome_url')
    username = data.get('username')
    password = data.get('password')
    
    result = test_navidrome_connection(navidrome_url, username, password)
    return jsonify(result)

def test_navidrome_connection(navidrome_url, username, password):
    """Test connection to Navidrome and return diagnostic information"""
    result = {
        'success': False,
        'error': None,
        'details': {},
        'server_info': None
    }
    
    # Check for missing parameters
    if not navidrome_url:
        result['error'] = "Navidrome URL is missing"
        return result
    
    if not username:
        result['error'] = "Username is missing"
        return result
    
    if not password:
        result['error'] = "Password is missing"
        return result
    
    # Process the URL to ensure it's correctly formatted
    base_url = navidrome_url.rstrip('/')
    
    # Check if URL already has /rest path
    result['details']['original_url'] = navidrome_url
    result['details']['processed_url'] = base_url
    
    if '/rest' not in base_url:
        base_url = f"{base_url}/rest"
        result['details']['rest_path_added'] = True
    else:
        result['details']['rest_path_added'] = False
    
    result['details']['final_url'] = base_url
    
    # Try to ping the server
    ping_url = f"{base_url}/ping.view"
    params = {
        'u': username,
        'p': password,
        'v': '1.16.1',
        'c': 'flask-ollama-playlist',
        'f': 'json'
    }
    
    try:
        # Test ping endpoint
        result['details']['ping_url'] = ping_url
        ping_response = requests.get(ping_url, params=params, timeout=10)
        result['details']['ping_status_code'] = ping_response.status_code
        
        if ping_response.status_code == 200:
            try:
                ping_data = ping_response.json()
                result['details']['ping_response'] = ping_data
                
                if ping_data.get('subsonic-response', {}).get('status') == 'ok':
                    result['success'] = True
                else:
                    error = ping_data.get('subsonic-response', {}).get('error', {})
                    result['error'] = f"API Error: {error.get('message')} (code {error.get('code')})"
            except json.JSONDecodeError:
                result['error'] = "Could not parse JSON response from server"
                result['details']['ping_response_text'] = ping_response.text[:500]  # First 500 chars
        else:
            result['error'] = f"Server returned status code {ping_response.status_code}"
            result['details']['ping_response_text'] = ping_response.text[:500]  # First 500 chars
            
        # Try to get server version info if ping was successful
        if result['success']:
            system_url = f"{base_url}/getSystemInfo.view"
            system_response = requests.get(system_url, params=params, timeout=10)
            
            if system_response.status_code == 200:
                try:
                    system_data = system_response.json()
                    if system_data.get('subsonic-response', {}).get('status') == 'ok':
                        result['server_info'] = system_data.get('subsonic-response', {}).get('systemInfo', {})
                except:
                    pass  # Silently fail on system info
            
    except requests.exceptions.ConnectionError:
        result['error'] = "Connection error - could not connect to server"
    except requests.exceptions.Timeout:
        result['error'] = "Connection timed out"
    except requests.exceptions.RequestException as e:
        result['error'] = f"Request error: {str(e)}"
    
    return result

def search_track_in_navidrome(query, navidrome_url, username, password):
    """Search for tracks in Navidrome using the search3 endpoint"""
    if not navidrome_url:
        debug_log("Navidrome URL is not configured", "ERROR")
        return []
        
    # Remove trailing slash if present
    base_url = navidrome_url.rstrip('/')
    
    # Check if URL already has /rest path - don't add it if it's already there
    if '/rest' not in base_url:
        base_url = f"{base_url}/rest"
        debug_log(f"Added /rest to Navidrome URL: {base_url}", "DEBUG")
    
    # Setup the search endpoint URL with proper parameter encoding
    url = f"{base_url}/search3.view"
    params = {
        'u': username,
        'p': password,
        'v': '1.16.1',
        'c': 'flask-ollama-playlist',
        'f': 'json',
        'query': query,
        'songCount': 40,  # Limit to 40 songs max
        'artistCount': 0,  # No artists
        'albumCount': 0    # No albums
    }
    
    debug_log(f"Searching Navidrome for query: '{query}'", "INFO")
    
    try:
        # Make the request using the params parameter which properly handles URL encoding
        debug_log(f"Making request to Navidrome: {url}", "DEBUG")
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        # Print the actual URL that was requested (for debugging)
        debug_log(f"Full search URL: {response.url}", "DEBUG")
        
        data = response.json()
        
        # Debug: print the raw API response
        debug_log(f"Navidrome search response status code: {response.status_code}", "DEBUG")
        debug_log(f"Navidrome search response first 200 chars: {json.dumps(data)[:200]}...", "DEBUG")
        
        if data.get('subsonic-response', {}).get('status') == 'ok':
            search_result = data.get('subsonic-response', {}).get('searchResult3', {})
            songs = search_result.get('song', [])
            debug_log(f"Found {len(songs)} songs in Navidrome", "INFO")
            
            # Format the results similar to how the Ollama response is processed
            tracks = []
            for song in songs:
                track_id = song.get('id')
                title = song.get('title', 'Unknown Title')
                artist = song.get('artist', 'Unknown Artist')
                album = song.get('album', 'Unknown Album')
                
                tracks.append({
                    'id': track_id,
                    'title': title,
                    'artist': artist,
                    'album': album,
                    'source': 'navidrome'
                })
                
                debug_log(f"Found track: {title} by {artist} on {album} (ID: {track_id})", "DEBUG")
                
            return tracks
        else:
            error_message = data.get('subsonic-response', {}).get('error', {}).get('message')
            debug_log(f"Error searching Navidrome: {error_message}", "ERROR", True)
            return []
    except requests.exceptions.RequestException as e:
        debug_log(f"Error searching Navidrome: {e}", "ERROR", True)
        return []
    except json.JSONDecodeError as e:
        debug_log(f"Error decoding Navidrome search JSON response: {e}", "ERROR", True)
        return []
        return []

def create_playlist_in_navidrome(playlist_name, track_ids, navidrome_url, username, password):
    # Process the URL to ensure it's correctly formatted
    if not navidrome_url:
        debug_log("Navidrome URL is not configured", "ERROR")
        return None
        
    # Remove trailing slash if present
    base_url = navidrome_url.rstrip('/')
    
    # Check if URL already has /rest path - don't add it if it's already there
    if '/rest' not in base_url:
        base_url = f"{base_url}/rest"
        debug_log(f"Added /rest to Navidrome URL: {base_url}", "DEBUG")
    
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
        
    debug_log(f"Creating Navidrome playlist '{playlist_name}' with {len(track_ids) if track_ids else 0} tracks", "INFO", True)
    
    try:
        # Use params argument instead of building URL manually
        debug_log(f"Making request to Navidrome: {url}", "DEBUG")
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        debug_log(f"Full playlist creation URL: {response.url}", "DEBUG")
        
        data = response.json()
        debug_log(f"Navidrome create playlist response: {json.dumps(data)[:200]}...", "DEBUG")
        
        if data.get('subsonic-response', {}).get('status') == 'ok':
            playlist_id = data['subsonic-response'].get('playlist', {}).get('id')
            debug_log(f"Successfully created Navidrome playlist with ID: {playlist_id}", "INFO", True)
            return playlist_id
        else:
            error_message = data.get('subsonic-response', {}).get('error', {}).get('message')
            debug_log(f"Error creating Navidrome playlist: {error_message}", "ERROR", True)
            return None
    except requests.exceptions.RequestException as e:
        debug_log(f"Error creating Navidrome playlist: {e}", "ERROR", True)
        return None
    except json.JSONDecodeError as e:
        debug_log(f"Error decoding Navidrome playlist JSON response: {e}", "ERROR", True)
        return None

@main_bp.route('/api/generate-playlist', methods=['POST'])
def api_generate_playlist():
    # Ensure we have JSON data
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 415
    
    # Extract request data
    data = request.json
    prompt = data.get('prompt', '')
    num_songs = data.get('num_songs', 10)
    playlist_name = data.get('playlist_name', 'TuneForge Playlist')
    
    # Debug output
    debug_log(f"Received playlist generation request: {prompt[:100]}...", "INFO", True)
    
    # Load configuration
    ollama_url = get_config_value('OLLAMA', 'URL', 'http://localhost:11434')
    ollama_model = get_config_value('OLLAMA', 'Model', 'llama3')
    enable_navidrome = get_config_value('APP', 'EnableNavidrome', 'no').lower() == 'yes'
    enable_plex = get_config_value('APP', 'EnablePlex', 'no').lower() == 'yes'
    
    debug_log(f"Configuration loaded: Ollama URL={ollama_url}, Model={ollama_model}", "INFO")
    debug_log(f"Services enabled: Navidrome={enable_navidrome}, Plex={enable_plex}", "INFO")
    
    # Prepare the playlist
    tracks = []
    
    # Try to generate tracks with Ollama
    try:
        # Format the prompt for Ollama
        formatted_prompt = f"""Create a playlist with these preferences:
{prompt}

For each song, provide the following in JSON format:
1. Title
2. Artist 
3. Album

Generate exactly {num_songs} songs. Output ONLY valid JSON in this format:
[
  {{"title": "Song Title 1", "artist": "Artist Name 1", "album": "Album Name 1"}},
  {{"title": "Song Title 2", "artist": "Artist Name 2", "album": "Album Name 2"}},
  ...
]
"""
        
        # Create the API request to Ollama
        ollama_api_url = f"{ollama_url.rstrip('/')}/api/generate"
        ollama_payload = {
            "model": ollama_model,
            "prompt": formatted_prompt,
            "stream": False
        }
        
        # Make the request to Ollama
        debug_log(f"Sending request to Ollama at {ollama_api_url}", "INFO", True)
        debug_log(f"Prompt: {formatted_prompt[:200]}...", "DEBUG")
        
        response = requests.post(ollama_api_url, json=ollama_payload, timeout=60)
        
        if response.status_code == 200:
            response_data = response.json()
            response_text = response_data.get('response', '')
            
            # Debug the response if enabled
            debug_log(f"Ollama responded with status 200", "INFO")
            debug_log(f"Response text (first 200 chars): {response_text[:200]}...", "DEBUG")
            
            # Extract the JSON part from the response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
                try:
                    # Parse the JSON
                    generated_tracks = json.loads(json_text)
                    tracks = generated_tracks
                    debug_log(f"Successfully parsed {len(tracks)} tracks from Ollama response", "INFO", True)
                    debug_log(f"Track sample: {json.dumps(tracks[:2], indent=2)}", "DEBUG")
                except json.JSONDecodeError as e:
                    debug_log(f"Error parsing JSON from Ollama: {e}", "ERROR", True)
                    debug_log(f"JSON text that failed to parse: {json_text[:200]}...", "DEBUG")
                    # Fall back to mock data if Ollama parsing fails
                    tracks = [
                        {"title": f"Track {i+1}", "artist": f"Artist {chr(65+i)}", "album": f"Album {chr(88+i%3)}"}
                        for i in range(5)
                    ]
                    debug_log("Falling back to mock data due to JSON parse error", "WARN")
            else:
                debug_log("Could not find JSON in Ollama response, using mock data", "WARN", True)
                debug_log(f"Response that didn't contain valid JSON: {response_text[:200]}...", "DEBUG")
                # Fall back to mock data if no JSON was found
                tracks = [
                    {"title": f"Track {i+1}", "artist": f"Artist {chr(65+i)}", "album": f"Album {chr(88+i%3)}"}
                    for i in range(5)
                ]
        else:
            debug_log(f"Error from Ollama API: {response.status_code} {response.text[:100]}...", "ERROR", True)
            # Fall back to mock data on API error
            tracks = [
                {"title": f"Track {i+1}", "artist": f"Artist {chr(65+i)}", "album": f"Album {chr(88+i%3)}"}
                for i in range(5)
            ]
    except Exception as e:
        debug_log(f"Error calling Ollama API: {e}", "ERROR", True)
        # Fall back to mock data on any error
        tracks = [
            {"title": f"Track {i+1}", "artist": f"Artist {chr(65+i)}", "album": f"Album {chr(88+i%3)}"}
            for i in range(5)
        ]
    
    # Create the playlist data structure
    playlist = {
        "name": playlist_name,
        "description": prompt,
        "created_at": datetime.datetime.now().isoformat(),
        "tracks": tracks
    }
    
    # Now check if we should search for these tracks in Navidrome
    navidrome_tracks = []
    plex_tracks = []
    
    if enable_navidrome:
        debug_log("Navidrome integration is enabled, searching for tracks...", "INFO")
        navidrome_url = get_config_value('NAVIDROME', 'URL', '')
        navidrome_username = get_config_value('NAVIDROME', 'Username', '')
        navidrome_password = get_config_value('NAVIDROME', 'Password', '')
        
        debug_log(f"Navidrome config: URL={navidrome_url}, Username={navidrome_username}", "DEBUG")
        
        if navidrome_url and navidrome_username and navidrome_password:
            debug_log("Navidrome credentials found, proceeding with track search", "INFO")
            
            # Search for each track in Navidrome
            for track in tracks:
                title = track.get('title', '')
                artist = track.get('artist', '')
                
                search_query = f"{artist} {title}"
                debug_log(f"Searching Navidrome for: {search_query}", "INFO")
                
                found_tracks = search_track_in_navidrome(search_query, navidrome_url, navidrome_username, navidrome_password)
                
                if found_tracks:
                    debug_log(f"Found {len(found_tracks)} matching tracks in Navidrome", "INFO")
                    navidrome_tracks.extend(found_tracks)
                else:
                    debug_log(f"No matches found in Navidrome for: {search_query}", "WARN")
            
            # If we found tracks in Navidrome, create a playlist
            if navidrome_tracks:
                debug_log(f"Found a total of {len(navidrome_tracks)} tracks in Navidrome", "INFO")
                track_ids = [track.get('id') for track in navidrome_tracks if track.get('id')]
                
                if track_ids:
                    debug_log(f"Creating Navidrome playlist with {len(track_ids)} tracks", "INFO")
                    playlist_id = create_playlist_in_navidrome(playlist_name, track_ids, navidrome_url, navidrome_username, navidrome_password)
                    
                    if playlist_id:
                        debug_log(f"Successfully created Navidrome playlist with ID: {playlist_id}", "INFO", True)
                    else:
                        debug_log("Failed to create Navidrome playlist", "ERROR", True)
                else:
                    debug_log("No valid track IDs found for Navidrome playlist", "WARN")
            else:
                debug_log("No matching tracks found in Navidrome, skipping playlist creation", "WARN")
        else:
            debug_log("Navidrome is enabled but credentials are incomplete, skipping", "WARN", True)
    else:
        debug_log("Navidrome integration is disabled, skipping", "INFO")
    
    # Check if we should search for these tracks in Plex
    if enable_plex:
        debug_log("Plex integration is enabled, searching for tracks...", "INFO")
        plex_server_url = get_config_value('PLEX', 'ServerURL', '')
        plex_token = get_config_value('PLEX', 'Token', '')
        plex_machine_id = get_config_value('PLEX', 'MachineID', '')
        plex_music_section_id = get_config_value('PLEX', 'MusicSectionID', '')
        plex_playlist_type = get_config_value('PLEX', 'PlaylistType', 'audio')
        
        debug_log(f"Plex config: URL={plex_server_url}, Token=******, Section={plex_music_section_id}", "DEBUG")
        
        if plex_server_url and plex_token and plex_music_section_id:
            debug_log("Plex credentials found, proceeding with track search", "INFO")
            
            # Search for each track in Plex
            for track in tracks:
                title = track.get('title', '')
                artist = track.get('artist', '')
                
                search_query = f"{artist} {title}"
                debug_log(f"Searching Plex for: {search_query}", "INFO")
                
                found_tracks = search_track_in_plex(search_query, plex_server_url, plex_token, plex_music_section_id)
                
                if found_tracks:
                    debug_log(f"Found {len(found_tracks)} matching tracks in Plex", "INFO")
                    plex_tracks.extend(found_tracks)
                else:
                    debug_log(f"No matches found in Plex for: {search_query}", "WARN")
            
            # If we found tracks in Plex, create a playlist
            if plex_tracks:
                debug_log(f"Found a total of {len(plex_tracks)} tracks in Plex", "INFO")
                track_ids = [track.get('id') for track in plex_tracks if track.get('id')]
                
                if track_ids:
                    debug_log(f"Creating Plex playlist with {len(track_ids)} tracks", "INFO")
                    playlist_id = create_playlist_in_plex(playlist_name, track_ids, plex_server_url, plex_token, plex_machine_id, plex_playlist_type)
                    
                    if playlist_id:
                        debug_log(f"Successfully created Plex playlist with ID: {playlist_id}", "INFO", True)
                    else:
                        debug_log("Failed to create Plex playlist", "ERROR", True)
                else:
                    debug_log("No valid track IDs found for Plex playlist", "WARN")
            else:
                debug_log("No matching tracks found in Plex, skipping playlist creation", "WARN")
        else:
            debug_log("Plex is enabled but credentials are incomplete, skipping", "WARN", True)
    else:
        debug_log("Plex integration is disabled, skipping", "INFO")
    
    # Save the playlist to history
    try:
        # Load existing history
        history = load_playlist_history()
        
        # Add new playlist to history
        history.append(playlist)
        
        # Save back to file
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
            
        debug_log(f"Saved playlist '{playlist_name}' to history", "INFO")
    except Exception as e:
        debug_log(f"Error saving playlist to history: {e}", "ERROR", True)
    
    # Return response
    response = {
        "status": "success",
        "message": "Playlist generated successfully",
        "data": {
            "playlist": playlist,
            "services": {
                "navidrome": enable_navidrome,
                "plex": enable_plex
            }
        }
    }
    
    return jsonify(response)

def search_track_in_plex(query, plex_server_url, plex_token, section_id):
    """Search for tracks in Plex using the search endpoint"""
    if not plex_server_url:
        debug_log("Plex Server URL is not configured", "ERROR")
        return []
        
    # Remove trailing slash if present
    base_url = plex_server_url.rstrip('/')
    
    # Setup the search endpoint URL
    url = f"{base_url}/search"
    
    headers = {
        'X-Plex-Token': plex_token,
        'Accept': 'application/json'
    }
    
    params = {
        'query': query,
        'section': section_id,
        'type': '10'  # 10 is the type for tracks
    }
    
    debug_log(f"Searching Plex for query: '{query}'", "INFO")
    
    try:
        # Make the request
        debug_log(f"Making request to Plex: {url}", "DEBUG")
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        # Print the actual URL that was requested (for debugging)
        debug_log(f"Full search URL: {response.url}", "DEBUG")
        
        data = response.json()
        
        # Debug: print the raw API response
        debug_log(f"Plex search response status code: {response.status_code}", "DEBUG")
        debug_log(f"Plex search response first 200 chars: {json.dumps(data)[:200]}...", "DEBUG")
        
        tracks = []
        if 'MediaContainer' in data and 'Metadata' in data['MediaContainer']:
            results = data['MediaContainer']['Metadata']
            debug_log(f"Found {len(results)} items in Plex search results", "INFO")
            
            for item in results:
                if item.get('type') == 'track':
                    track = {
                        'id': item.get('ratingKey'),
                        'title': item.get('title', 'Unknown Title'),
                        'artist': item.get('grandparentTitle', 'Unknown Artist'),
                        'album': item.get('parentTitle', 'Unknown Album'),
                        'source': 'plex'
                    }
                    tracks.append(track)
                    debug_log(f"Found track: {track['title']} by {track['artist']} on {track['album']} (ID: {track['id']})", "DEBUG")
        
        debug_log(f"Found {len(tracks)} tracks in Plex", "INFO")
        return tracks
    except requests.exceptions.RequestException as e:
        debug_log(f"Error searching Plex: {e}", "ERROR", True)
        return []
    except json.JSONDecodeError as e:
        debug_log(f"Error decoding Plex search JSON response: {e}", "ERROR", True)
        return []
    except Exception as e:
        debug_log(f"Unexpected error searching Plex: {e}", "ERROR", True)
        return []

def create_playlist_in_plex(playlist_name, track_ids, plex_server_url, plex_token, plex_machine_id, playlist_type='audio'):
    """Create a playlist in Plex with the given tracks"""
    if not plex_server_url:
        debug_log("Plex Server URL is not configured", "ERROR")
        return None
        
    # Remove trailing slash if present
    base_url = plex_server_url.rstrip('/')
    
    # Setup the create playlist endpoint
    url = f"{base_url}/playlists"
    
    headers = {
        'X-Plex-Token': plex_token,
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    # Convert track IDs to proper format for Plex
    track_uri_strings = []
    for track_id in track_ids:
        track_uri_strings.append(f"/library/metadata/{track_id}")
    
    params = {
        'uri': f"server://{plex_machine_id}/com.plexapp.plugins.library",
        'title': playlist_name,
        'type': playlist_type,
        'smart': '0'
    }
    
    if track_uri_strings:
        params['uri'] += f"?metadata%5D={','.join(track_uri_strings)}"
    
    debug_log(f"Creating Plex playlist '{playlist_name}' with {len(track_ids)} tracks", "INFO", True)
    
    try:
        # Make the request
        debug_log(f"Making request to Plex: {url}", "DEBUG")
        response = requests.post(url, params=params, headers=headers)
        response.raise_for_status()
        
        debug_log(f"Plex create playlist response status code: {response.status_code}", "DEBUG")
        
        if response.status_code == 201 or response.status_code == 200:
            try:
                data = response.json()
                if 'MediaContainer' in data and 'Metadata' in data['MediaContainer'] and len(data['MediaContainer']['Metadata']) > 0:
                    playlist_id = data['MediaContainer']['Metadata'][0].get('ratingKey')
                    debug_log(f"Successfully created Plex playlist with ID: {playlist_id}", "INFO", True)
                    return playlist_id
            except json.JSONDecodeError:
                debug_log("Could not parse JSON response from Plex", "ERROR")
                return None
        
        debug_log(f"Error creating Plex playlist: {response.text}", "ERROR", True)
        return None
    except requests.exceptions.RequestException as e:
        debug_log(f"Error creating Plex playlist: {e}", "ERROR", True)
        return None
    except Exception as e:
        debug_log(f"Unexpected error creating Plex playlist: {e}", "ERROR", True)
        return None

@main_bp.route('/test-plex')
def test_plex_page():
    return render_template('test_plex.html')

@main_bp.route('/api/test-plex-connection', methods=['POST'])
def api_test_plex_connection():
    data = request.json
    plex_server_url = data.get('plex_server_url')
    plex_token = data.get('plex_token')
    plex_music_section_id = data.get('plex_music_section_id')
    
    result = test_plex_connection(plex_server_url, plex_token, plex_music_section_id)
    return jsonify(result)

def test_plex_connection(plex_server_url, plex_token, section_id):
    """Test connection to Plex and return diagnostic information"""
    result = {
        'success': False,
        'error': None,
        'details': {},
        'server_info': None
    }
    
    # Check for missing parameters
    if not plex_server_url:
        result['error'] = "Plex Server URL is missing"
        return result
    
    if not plex_token:
        result['error'] = "Plex Token is missing"
        return result
    
    # Process the URL to ensure it's correctly formatted
    base_url = plex_server_url.rstrip('/')
    result['details']['original_url'] = plex_server_url
    result['details']['processed_url'] = base_url
    
    # Try to ping the server
    ping_url = f"{base_url}/library/sections"
    headers = {
        'X-Plex-Token': plex_token,
        'Accept': 'application/json'
    }
    
    try:
        # Test library sections endpoint
        result['details']['ping_url'] = ping_url
        ping_response = requests.get(ping_url, headers=headers, timeout=10)
        result['details']['ping_status_code'] = ping_response.status_code
        
        if ping_response.status_code == 200:
            try:
                ping_data = ping_response.json()
                result['details']['ping_response'] = ping_data
                
                # Check if we can access the library
                if 'MediaContainer' in ping_data and 'Directory' in ping_data['MediaContainer']:
                    result['success'] = True
                    
                    # If section_id is provided, check if it exists
                    if section_id:
                        section_found = False
                        for section in ping_data['MediaContainer']['Directory']:
                            if section.get('key') == section_id or section.get('id') == section_id:
                                section_found = True
                                result['details']['section_info'] = section
                                break
                        
                        if not section_found:
                            result['error'] = f"Section ID {section_id} not found in Plex library"
                            result['success'] = False
                else:
                    result['error'] = "Could not access Plex library sections"
            except json.JSONDecodeError:
                result['error'] = "Could not parse JSON response from server"
                result['details']['ping_response_text'] = ping_response.text[:500]  # First 500 chars
        else:
            result['error'] = f"Server returned status code {ping_response.status_code}"
            result['details']['ping_response_text'] = ping_response.text[:500]  # First 500 chars
            
        # Try to get server version info if ping was successful
        if result['success']:
            system_url = f"{base_url}/identity"
            system_response = requests.get(system_url, headers=headers, timeout=10)
            
            if system_response.status_code == 200:
                try:
                    system_data = system_response.json()
                    if 'MediaContainer' in system_data:
                        result['server_info'] = system_data['MediaContainer']
                except:
                    pass  # Silently fail on system info
    
    except requests.exceptions.ConnectionError:
        result['error'] = "Connection error - could not connect to server"
    except requests.exceptions.Timeout:
        result['error'] = "Connection timed out"
    except requests.exceptions.RequestException as e:
        result['error'] = f"Request error: {str(e)}"
    
    return result
