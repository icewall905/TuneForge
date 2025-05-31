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
        # Log more of the response for detailed inspection
        debug_log(f"Navidrome search raw response: {json.dumps(data)}", "DEBUG") 
        
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
    debug_log(f"Requested {num_songs} songs", "INFO")
    
    # Load configuration
    ollama_url = get_config_value('OLLAMA', 'URL', 'http://localhost:11434')
    ollama_model = get_config_value('OLLAMA', 'Model', 'llama3')
    enable_navidrome = get_config_value('APP', 'EnableNavidrome', 'no').lower() == 'yes'
    enable_plex = get_config_value('APP', 'EnablePlex', 'no').lower() == 'yes'
    
    debug_log(f"Configuration loaded: Ollama URL={ollama_url}, Model={ollama_model}", "INFO")
    debug_log(f"Services enabled: Navidrome={enable_navidrome}, Plex={enable_plex}", "INFO")
    
    # Prepare the playlist
    all_tracks = []
    matched_tracks = []
    remaining_tracks_needed = num_songs
    retry_attempts = 0
    max_retry_attempts = int(get_config_value('OLLAMA', 'MaxAttempts', '3'))
    
    # Define minimum threshold for matches before retrying
    min_match_threshold = max(int(num_songs * 0.2), 2)  # At least 20% or 2 tracks, whichever is higher
    
    debug_log(f"Minimum match threshold: {min_match_threshold} tracks", "DEBUG")
    
    # Continue generating tracks until we have enough matches or hit retry limit
    while remaining_tracks_needed > 0 and retry_attempts < max_retry_attempts:
        tracks = generate_tracks_with_ollama(ollama_url, ollama_model, prompt, remaining_tracks_needed, retry_attempts)
        
        # Add the new tracks to our master list
        if tracks and len(tracks) > 0:
            all_tracks.extend(tracks)
            
            # Track the retry attempt
            retry_attempts += 1
            
            # Search for these tracks in services
            newly_matched_navidrome_tracks = []
            newly_matched_plex_tracks = []
            
            # Search in Navidrome if enabled
            if enable_navidrome:
                newly_matched_navidrome_tracks = search_tracks_in_service(tracks, 'navidrome')
                matched_tracks.extend(newly_matched_navidrome_tracks)
                
            # Search in Plex if enabled
            if enable_plex:
                newly_matched_plex_tracks = search_tracks_in_service(tracks, 'plex')
                matched_tracks.extend(newly_matched_plex_tracks)
            
            # Count unique matched tracks (avoid duplicates)
            unique_matched_tracks = {}
            for track in matched_tracks:
                track_id = track.get('id')
                if track_id:
                    # Store the track by ID, overwriting any previous instance
                    unique_matched_tracks[track_id] = track
            
            # Update remaining tracks needed
            remaining_tracks_needed = num_songs - len(unique_matched_tracks)
            
            debug_log(f"Found {len(newly_matched_navidrome_tracks)} new Navidrome matches, {len(newly_matched_plex_tracks)} new Plex matches", "INFO")
            debug_log(f"Total unique matched tracks: {len(unique_matched_tracks)}/{num_songs}", "INFO")
            
            # If we have enough tracks, break
            if remaining_tracks_needed <= 0:
                debug_log(f"Found enough tracks, stopping retries", "INFO")
                break
                
            # Check if we got at least some matches in this batch
            total_new_matches = len(newly_matched_navidrome_tracks) + len(newly_matched_plex_tracks)
            if total_new_matches < min_match_threshold and retry_attempts < max_retry_attempts:
                debug_log(f"Only found {total_new_matches} matches in this batch, which is below threshold of {min_match_threshold}", "INFO")
                debug_log(f"Will try again for {remaining_tracks_needed} more tracks (attempt {retry_attempts}/{max_retry_attempts})", "INFO")
            else:
                # We got a decent number of matches, so break
                debug_log(f"Found {total_new_matches} matches in this batch, which is satisfactory", "INFO")
                break
        else:
            # If we got no tracks from Ollama, increment retry but give up if we hit max
            retry_attempts += 1
            if retry_attempts >= max_retry_attempts:
                debug_log(f"Failed to get tracks from Ollama after {retry_attempts} attempts, giving up", "ERROR")
                break
    
    # Create the playlist data structure with all generated tracks
    playlist = {
        "name": playlist_name,
        "description": prompt,
        "created_at": datetime.datetime.now().isoformat(),
        "tracks": all_tracks
    }
    
    # Now create playlists in the music services if we have matches
    if enable_navidrome:
        create_playlist_in_service(playlist_name, matched_tracks, 'navidrome')
    
    if enable_plex:
        create_playlist_in_service(playlist_name, matched_tracks, 'plex')
    
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
            },
            "stats": {
                "total_tracks_generated": len(all_tracks),
                "matched_tracks": len(matched_tracks),
                "retry_attempts": retry_attempts
            }
        }
    }
    
    return jsonify(response)

def generate_tracks_with_ollama(ollama_url, ollama_model, prompt, num_songs, attempt=0):
    """Generate tracks using Ollama API with retry logic"""
    try:
        # Adjust prompt for retry attempts
        retry_prompt = ""
        if attempt > 0:
            retry_prompt = f"\nThe previous suggestions didn't match my music library well. Please suggest {num_songs} DIFFERENT songs that are more likely to be in a typical music collection. Focus on well-known artists and popular songs."
        
        # Format the prompt for Ollama
        formatted_prompt = f"""Create a playlist with these preferences:
{prompt}{retry_prompt}

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
        debug_log(f"Sending request to Ollama at {ollama_api_url} (attempt {attempt+1})", "INFO", True)
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
                    debug_log(f"Successfully parsed {len(generated_tracks)} tracks from Ollama response", "INFO", True)
                    debug_log(f"Track sample: {json.dumps(generated_tracks[:2], indent=2)}", "DEBUG")
                    return generated_tracks
                except json.JSONDecodeError as e:
                    debug_log(f"Error parsing JSON from Ollama: {e}", "ERROR", True)
                    debug_log(f"JSON text that failed to parse: {json_text[:200]}...", "DEBUG")
                    # Fall back to mock data if Ollama parsing fails
                    tracks = [
                        {"title": f"Track {i+1}", "artist": f"Artist {chr(65+i)}", "album": f"Album {chr(88+i%3)}"}
                        for i in range(5)
                    ]
                    debug_log("Falling back to mock data due to JSON parse error", "WARN")
                    return tracks
            else:
                debug_log("Could not find JSON in Ollama response, using mock data", "WARN", True)
                debug_log(f"Response that didn't contain valid JSON: {response_text[:200]}...", "DEBUG")
                # Fall back to mock data if no JSON was found
                tracks = [
                    {"title": f"Track {i+1}", "artist": f"Artist {chr(65+i)}", "album": f"Album {chr(88+i%3)}"}
                    for i in range(5)
                ]
                return tracks
        else:
            debug_log(f"Error from Ollama API: {response.status_code} {response.text[:100]}...", "ERROR", True)
            # Fall back to mock data on API error
            tracks = [
                {"title": f"Track {i+1}", "artist": f"Artist {chr(65+i)}", "album": f"Album {chr(88+i%3)}"}
                for i in range(5)
            ]
            return tracks
    except Exception as e:
        debug_log(f"Error calling Ollama API: {e}", "ERROR", True)
        # Fall back to mock data on any error
        tracks = [
            {"title": f"Track {i+1}", "artist": f"Artist {chr(65+i)}", "album": f"Album {chr(88+i%3)}"}
            for i in range(5)
        ]
        return tracks

def search_tracks_in_service(tracks, service):
    """Search for tracks in a specific service (Navidrome or Plex)"""
    if service == 'navidrome':
        navidrome_url = get_config_value('NAVIDROME', 'URL', '')
        navidrome_username = get_config_value('NAVIDROME', 'Username', '')
        navidrome_password = get_config_value('NAVIDROME', 'Password', '')
        
        debug_log(f"Searching for {len(tracks)} tracks in Navidrome", "INFO")
        
        if not navidrome_url or not navidrome_username or not navidrome_password:
            debug_log("Navidrome credentials incomplete, skipping search", "WARN")
            return []
            
        matched_tracks = []
        for track in tracks:
            title = track.get('title', '')
            artist = track.get('artist', '')
            
            search_query = f"{artist} {title}"
            debug_log(f"Searching Navidrome for: {search_query}", "INFO")
            
            found_tracks = search_track_in_navidrome(search_query, navidrome_url, navidrome_username, navidrome_password)
            
            if found_tracks:
                debug_log(f"Found {len(found_tracks)} matching tracks in Navidrome", "INFO")
                matched_tracks.extend(found_tracks)
            else:
                debug_log(f"No matches found in Navidrome for: {search_query}", "WARN")
                
        debug_log(f"Found a total of {len(matched_tracks)} tracks in Navidrome", "INFO")
        return matched_tracks
    
    elif service == 'plex':
        plex_server_url = get_config_value('PLEX', 'ServerURL', '')
        plex_token = get_config_value('PLEX', 'Token', '')
        plex_music_section_id = get_config_value('PLEX', 'MusicSectionID', '')
        
        debug_log(f"Searching for {len(tracks)} tracks in Plex", "INFO")
        
        if not plex_server_url or not plex_token or not plex_music_section_id:
            debug_log("Plex credentials incomplete, skipping search", "WARN")
            return []
            
        matched_tracks = []
        for track in tracks:
            title = track.get('title', '')
            artist = track.get('artist', '')
            
            search_query = f"{artist} {title}"
            debug_log(f"Searching Plex for: {search_query}", "INFO")
            
            found_tracks = search_track_in_plex(search_query, plex_server_url, plex_token, plex_music_section_id)
            
            if found_tracks:
                debug_log(f"Found {len(found_tracks)} matching tracks in Plex", "INFO")
                matched_tracks.extend(found_tracks)
            else:
                debug_log(f"No matches found in Plex for: {search_query}", "WARN")
                
        debug_log(f"Found a total of {len(matched_tracks)} tracks in Plex", "INFO")
        return matched_tracks
    
    return []

def create_playlist_in_service(playlist_name, tracks, service):
    """Create a playlist in a specific service (Navidrome or Plex)"""
    if not tracks or len(tracks) == 0:
        debug_log(f"No tracks to create playlist in {service}", "WARN")
        return None
        
    # Filter tracks by service and get unique IDs
    service_tracks = [track for track in tracks if track.get('source') == service]
    track_ids = []
    
    # Use a set to deduplicate tracks
    seen_ids = set()
    for track in service_tracks:
        track_id = track.get('id')
        if track_id and track_id not in seen_ids:
            track_ids.append(track_id)
            seen_ids.add(track_id)
    
    if not track_ids or len(track_ids) == 0:
        debug_log(f"No valid track IDs for {service} playlist", "WARN")
        return None
        
    debug_log(f"Creating {service} playlist with {len(track_ids)} unique tracks", "INFO")
    
    if service == 'navidrome':
        navidrome_url = get_config_value('NAVIDROME', 'URL', '')
        navidrome_username = get_config_value('NAVIDROME', 'Username', '')
        navidrome_password = get_config_value('NAVIDROME', 'Password', '')
        
        return create_playlist_in_navidrome(playlist_name, track_ids, navidrome_url, navidrome_username, navidrome_password)
    
    elif service == 'plex':
        plex_server_url = get_config_value('PLEX', 'ServerURL', '')
        plex_token = get_config_value('PLEX', 'Token', '')
        plex_machine_id = get_config_value('PLEX', 'MachineID', '')
        plex_playlist_type = get_config_value('PLEX', 'PlaylistType', 'audio')
        
        return create_playlist_in_plex(playlist_name, track_ids, plex_server_url, plex_token, plex_machine_id, plex_playlist_type)
    
    return None
    
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
    
    # Split query into artist and title components for better search
    parts = query.split(" ", 1)
    artist = parts[0] if len(parts) > 0 else ""
    title = parts[1] if len(parts) > 1 else query
    
    debug_log(f"Parsed query into artist='{artist}' and title='{title}'", "DEBUG")
    
    # Setup the search endpoint URL
    # Use the library endpoint instead of search for better results
    url = f"{base_url}/library/sections/{section_id}/all"
    
    headers = {
        'X-Plex-Token': plex_token,
        'Accept': 'application/json'
    }
    
    # First try: search using a more flexible approach
    params = {
        'title': title,
        'type': '10',  # 10 is the type for tracks
        'limit': 50    # Increase limit to get more potential matches
    }
    
    # Only add artist filter if it's not empty and reasonably long
    if artist and len(artist) > 2:
        params['artist.title'] = artist
    
    debug_log(f"Searching Plex for query: '{query}'", "INFO")
    debug_log(f"Using artist filter: '{artist}' and title filter: '{title}'", "DEBUG")
    
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
        
        # Analyze the MediaContainer structure
        if 'MediaContainer' in data:
            container = data['MediaContainer']
            debug_log(f"MediaContainer keys: {list(container.keys())}", "DEBUG")
            debug_log(f"MediaContainer size: {container.get('size', 0)}", "DEBUG")
            if 'Metadata' not in container and container.get('size', 0) == 0:
                debug_log("No Metadata found in MediaContainer with size 0", "DEBUG")
            elif 'Metadata' not in container:
                debug_log(f"No Metadata found but container has size {container.get('size', 0)}", "DEBUG")
        
        tracks = []
        if 'MediaContainer' in data and 'Metadata' in data['MediaContainer']:
            results = data['MediaContainer'].get('Metadata', [])
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
        
        # If we got no results with the first approach, try a more general search
        if not tracks:
            debug_log("No tracks found with specific search, trying more general search", "INFO")
            
            # Use the search endpoint as a fallback with a more general query
            search_url = f"{base_url}/search"
            
            # Use just the title part for a more general search
            search_query = title
            
            # If title is too short or generic, fall back to the original query
            if len(title.strip()) < 3:
                search_query = query
                
            search_params = {
                'query': search_query,
                'sectionId': section_id,
                'type': '10',  # 10 is the type for tracks
                'limit': 50
            }
            
            search_response = requests.get(search_url, params=search_params, headers=headers)
            search_response.raise_for_status()
            
            debug_log(f"Full fallback search URL: {search_response.url}", "DEBUG")
            
            search_data = search_response.json()
            
            if 'MediaContainer' in search_data and 'Metadata' in search_data['MediaContainer']:
                search_results = search_data['MediaContainer'].get('Metadata', [])
                debug_log(f"Found {len(search_results)} items in Plex fallback search results", "INFO")
                
                for item in search_results:
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
        
        # Try a third approach if still no results - use artist search
        if not tracks:
            debug_log("No tracks found with general search, trying artist-only search", "INFO")
            
            # Try searching just by artist if we have one
            if artist and len(artist.strip()) > 2:
                artist_search_url = f"{base_url}/library/sections/{section_id}/all"
                artist_search_params = {
                    'artist.title': artist,
                    'type': '10',  # 10 is the type for tracks
                    'limit': 100   # Increase limit for broader results
                }
                
                artist_response = requests.get(artist_search_url, params=artist_search_params, headers=headers)
                artist_response.raise_for_status()
                
                debug_log(f"Full artist search URL: {artist_response.url}", "DEBUG")
                
                artist_data = artist_response.json()
                
                if 'MediaContainer' in artist_data and 'Metadata' in artist_data['MediaContainer']:
                    artist_results = artist_data['MediaContainer'].get('Metadata', [])
                    debug_log(f"Found {len(artist_results)} items in Plex artist search results", "INFO")
                    
                    for item in artist_results:
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
        debug_log(f"Raw response: {response.text[:500]}", "DEBUG")
        return []
    except Exception as e:
        debug_log(f"Unexpected error searching Plex: {e}", "ERROR", True)
        return []

def create_playlist_in_plex(playlist_name, track_ids, plex_server_url, plex_token, plex_machine_id, playlist_type='audio'):
    """Create a playlist in Plex with the given tracks using a two-step process."""
    if not plex_server_url:
        debug_log("Plex Server URL is not configured", "ERROR")
        return None
        
    if not plex_machine_id:
        debug_log("Plex Machine ID is not configured", "ERROR")
        return None

    if not track_ids or len(track_ids) == 0:
        debug_log("No track IDs provided for Plex playlist", "ERROR")
        return None
        
    base_url = plex_server_url.rstrip('/')
    headers = {
        'X-Plex-Token': plex_token,
        'Accept': 'application/json'
    }

    # Step 1: Create an empty playlist
    create_playlist_url = f"{base_url}/playlists"
    create_params = {
        'title': playlist_name,
        'type': playlist_type,
        'smart': '0',
        'uri': f"server://{plex_machine_id}/com.plexapp.plugins.library" # URI for the library
    }
    
    debug_log(f"Creating Plex playlist \'{playlist_name}\' (Step 1: Create empty playlist)", "INFO", True)
    debug_log(f"Request URL: {create_playlist_url}", "DEBUG")
    debug_log(f"Request params: {create_params}", "DEBUG")

    try:
        response = requests.post(create_playlist_url, params=create_params, headers=headers)
        debug_log(f"Step 1 Response status code: {response.status_code}", "DEBUG")
        debug_log(f"Step 1 Response text: {response.text[:500]}", "DEBUG")
        response.raise_for_status() # Raise an exception for HTTP errors

        data = response.json()
        debug_log(f"Step 1 Response JSON: {json.dumps(data)[:500]}...", "DEBUG")

        if 'MediaContainer' in data and 'Metadata' in data['MediaContainer'] and len(data['MediaContainer']['Metadata']) > 0:
            playlist_metadata = data['MediaContainer']['Metadata'][0]
            playlist_id = playlist_metadata.get('ratingKey')
            playlist_title = playlist_metadata.get('title')
            debug_log(f"Successfully created empty Plex playlist \'{playlist_title}\' with ID: {playlist_id}", "INFO", True)
        else:
            debug_log(f"Could not retrieve playlist ID from Plex response. Response: {json.dumps(data)[:500]}", "ERROR")
            return None

    except requests.exceptions.RequestException as e:
        debug_log(f"Error creating Plex playlist (Step 1): {e}", "ERROR", True)
        if hasattr(e, 'response') and e.response is not None:
            debug_log(f"Error response content: {e.response.text[:500]}", "DEBUG")
        return None
    except json.JSONDecodeError:
        debug_log(f"Error decoding JSON response from Plex (Step 1). Response: {response.text[:500]}", "ERROR")
        return None

    # Step 2: Add tracks to the created playlist
    if not playlist_id: # Should not happen if previous block succeeded, but as a safeguard
        debug_log("Playlist ID not found, cannot add tracks.", "ERROR")
        return None

    add_items_url = f"{base_url}/playlists/{playlist_id}/items"
    
    # Construct full track URIs: server://{machine_id}/com.plexapp.plugins.library/library/metadata/{track_id}
    full_track_uris = [f"server://{plex_machine_id}/com.plexapp.plugins.library/library/metadata/{track_id}" for track_id in track_ids]
    items_uri_param = ','.join(full_track_uris)
    
    add_params = {'uri': items_uri_param}

    debug_log(f"Adding {len(track_ids)} tracks to Plex playlist ID {playlist_id} (Step 2: Add items)", "INFO", True)
    debug_log(f"Request URL: {add_items_url}", "DEBUG")
    debug_log(f"Request params: {add_params}", "DEBUG") # Careful with logging tokens if they were in params

    try:
        add_response = requests.put(add_items_url, params=add_params, headers=headers) # Token is in headers
        debug_log(f"Step 2 Response status code: {add_response.status_code}", "DEBUG")
        debug_log(f"Step 2 Response text: {add_response.text[:500]}", "DEBUG")
        add_response.raise_for_status() # Raise an exception for HTTP errors
        
        # Verify items were added (optional, based on Plex API response for PUT /items)
        # Plex PUT to add items usually returns the updated playlist metadata.
        # We can check leafCount here if the response provides it.
        try:
            updated_playlist_data = add_response.json()
            debug_log(f"Step 2 Response JSON: {json.dumps(updated_playlist_data)[:500]}...", "DEBUG")
            if 'MediaContainer' in updated_playlist_data and 'Metadata' in updated_playlist_data['MediaContainer']:
                updated_metadata = updated_playlist_data['MediaContainer']['Metadata'][0]
                final_leaf_count = updated_metadata.get('leafCount', 'N/A')
                debug_log(f"Tracks added. Playlist \'{updated_metadata.get('title')}\' now has {final_leaf_count} items.", "INFO", True)
                if final_leaf_count == len(track_ids):
                     debug_log(f"Successfully added all {len(track_ids)} tracks to playlist ID {playlist_id}.", "INFO", True)
                elif final_leaf_count == 0 : # Check if it's still 0
                    debug_log(f"Warning: Tracks may not have been added. leafCount is {final_leaf_count} after adding items.", "WARN", True)
                else:
                    debug_log(f"Partially added tracks? Expected {len(track_ids)}, got {final_leaf_count}.", "WARN", True)

        except json.JSONDecodeError:
            debug_log("Could not decode JSON from add items response, but PUT was successful.", "WARN")
        
        return playlist_id # Return playlist_id if add operation was successful (status 2xx)

    except requests.exceptions.RequestException as e:
        debug_log(f"Error adding tracks to Plex playlist ID {playlist_id} (Step 2): {e}", "ERROR", True)
        if hasattr(e, 'response') and e.response is not None:
            debug_log(f"Error response content: {e.response.text[:500]}", "DEBUG")
        # Playlist was created but adding items failed.
        # Depending on desired behavior, could return playlist_id or None.
        # Returning None as the overall operation to create a populated playlist failed.
        return None
    except Exception as e:
        debug_log(f"An unexpected error occurred while adding items to Plex playlist: {e}", "ERROR", True)
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
