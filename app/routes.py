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

# --- Global Debug Flag ---
DEBUG_OLLAMA_RESPONSE = False

main_bp = Blueprint('main', __name__)

CONFIG_FILE = 'config.ini'
HISTORY_FILE = 'playlist_history.json'

# --- Helper Functions (adapted from your original script) ---

def get_config_value(config, section, key, default=None):
    env_var = f"{section.upper()}_{key.upper()}"
    return os.environ.get(env_var, config.get(section, key, fallback=default))

def load_config():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    else:
        # Create a default config if it doesn't exist
        config['OLLAMA'] = {
            'URL': current_app.config.get('OLLAMA_URL', 'http://localhost:11434'),
            'Model': current_app.config.get('OLLAMA_MODEL', 'llama3'),
            'ContextWindow': '2048',
            'MaxAttempts': '3'
        }
        config['NAVIDROME'] = {
            'URL': '',
            'Username': '',
            'Password': ''
        }
        config['PLEX'] = {
            'ServerURL': '',
            'Token': '',
            'MachineID': '',
            'PlaylistType': 'audio',
            'MusicSectionID': ''
        }
        config['APP'] = {
            'Likes': 'genres: electronic, ambient, idm. artists: aphex twin, boards of canada',
            'Dislikes': 'genres: country, pop. artists: taylor swift',
            'FavoriteArtists': '',
            'EnableNavidrome': 'no',
            'EnablePlex': 'no'
        }
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
    return config

def save_config(data):
    config = load_config()
    config['OLLAMA']['URL'] = data.get('ollama_url', config['OLLAMA']['URL'])
    config['OLLAMA']['Model'] = data.get('ollama_model', config['OLLAMA']['Model'])
    config['OLLAMA']['ContextWindow'] = data.get('context_window', config['OLLAMA']['ContextWindow'])
    config['OLLAMA']['MaxAttempts'] = data.get('max_attempts', config['OLLAMA']['MaxAttempts'])
    
    config['NAVIDROME']['URL'] = data.get('navidrome_url', config['NAVIDROME']['URL'])
    config['NAVIDROME']['Username'] = data.get('navidrome_username', config['NAVIDROME']['Username'])
    config['NAVIDROME']['Password'] = data.get('navidrome_password', config['NAVIDROME']['Password'])
    
    config['PLEX']['ServerURL'] = data.get('plex_server_url', config['PLEX']['ServerURL'])
    config['PLEX']['Token'] = data.get('plex_token', config['PLEX']['Token'])
    config['PLEX']['MachineID'] = data.get('plex_machine_id', config['PLEX']['MachineID'])
    config['PLEX']['PlaylistType'] = data.get('plex_playlist_type', config['PLEX']['PlaylistType'])
    config['PLEX']['MusicSectionID'] = data.get('plex_music_section_id', config['PLEX']['MusicSectionID'])

    config['APP']['Likes'] = data.get('likes', config['APP']['Likes'])
    config['APP']['Dislikes'] = data.get('dislikes', config['APP']['Dislikes'])
    config['APP']['FavoriteArtists'] = data.get('favorite_artists', config['APP']['FavoriteArtists'])
    config['APP']['EnableNavidrome'] = data.get('enable_navidrome', config['APP']['EnableNavidrome'])
    config['APP']['EnablePlex'] = data.get('enable_plex', config['APP']['EnablePlex'])

    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)
    return True

def get_playlist_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_playlist_history(playlist_name, description, tracks, platform, platform_playlist_id=None):
    history = get_playlist_history()
    new_entry = {
        'id': str(time.time()), # Simple unique ID
        'name': playlist_name,
        'description': description,
        'tracks': tracks,
        'platform': platform,
        'platform_playlist_id': platform_playlist_id,
        'created_at': datetime.datetime.now().isoformat(),
        'rating': None
    }
    history.insert(0, new_entry) # Add to the beginning
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def rate_playlist_entry(playlist_id, rating):
    history = get_playlist_history()
    for entry in history:
        if entry['id'] == playlist_id:
            entry['rating'] = int(rating)
            break
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

# --- Core Logic (Ollama, Navidrome, Plex interactions - adapted from your script) ---

class SearchCache:
    def __init__(self, max_age_seconds=3600):
        self.cache = {}
        self.max_age_seconds = max_age_seconds

    def get(self, key):
        if key in self.cache:
            entry_time, value = self.cache[key]
            if time.time() - entry_time < self.max_age_seconds:
                return value
            else:
                del self.cache[key] # Expired entry
        return None

    def set(self, key, value):
        self.cache[key] = (time.time(), value)

plex_cache = SearchCache()

def generate_prompt(likes, dislikes, favorite_artists, existing_tracks=None):
    prompt = f"Create a playlist. I like: {likes}. I dislike: {dislikes}. "
    if favorite_artists:
        prompt += f"My favorite artists are: {favorite_artists}. "
    if existing_tracks:
        prompt += f"The playlist already contains these tracks, please suggest different ones: {json.dumps(existing_tracks)}. "
    prompt += """Suggest around 10-15 tracks. For each track, provide the artist and title. Format the output as a JSON list of objects, where each object has 'artist' and 'title' keys. Example: [{"artist": "Artist Name", "title": "Track Title"}]. Do not include any other text or explanation outside of the JSON list."""
    return prompt

def query_ollama(prompt, ollama_url, ollama_model, context_window):
    payload = {
        "model": ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_ctx": int(context_window)}
    }
    if DEBUG_OLLAMA_RESPONSE:
        print(f"--- Ollama Prompt ---\n{prompt}\n---------------------")
    try:
        response = requests.post(f"{ollama_url}/api/generate", json=payload, timeout=120)
        response.raise_for_status()
        response_data = response.json()
        if DEBUG_OLLAMA_RESPONSE:
            print(f"--- Ollama Raw Response ---\n{response_data['response']}\n--------------------------")
        # Extract JSON part from the response
        json_match = re.search(r'\[\s*\{.*?\}\s*\]', response_data['response'], re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        else:
            # Try to find individual JSON objects if the full list regex fails
            # This is a fallback and might not be perfect
            track_objects = []
            for match in re.finditer(r'\{\s*"artist"\s*:\s*".*?"\s*,\s*"title"\s*:\s*".*?"\s*\}', response_data['response'], re.DOTALL):
                try:
                    track_objects.append(json.loads(match.group(0)))
                except json.JSONDecodeError:
                    continue # Skip malformed JSON objects
            if track_objects:
                return track_objects
            print("Error: Ollama response did not contain a valid JSON list of tracks.")
            print(f"Raw response was: {response_data['response']}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error querying Ollama: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding Ollama JSON response: {e}")
        print(f"Raw response was: {response_data['response']}")
        return None

def search_track_in_navidrome(artist, title, navidrome_url, username, password):
    # Simplified search, you might need to adjust based on Navidrome's API capabilities
    query = f"{artist} {title}"
    url = f"{navidrome_url}/rest/search3.view?u={username}&p={password}&v=1.16.1&c=flask-ollama-playlist&f=json&query={query}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data.get('subsonic-response', {}).get('searchResult3', {}).get('song'):
            songs = data['subsonic-response']['searchResult3']['song']
            # Basic matching, can be improved
            for song in songs:
                if artist.lower() in song['artist'].lower() and title.lower() in song['title'].lower():
                    return song['id']
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error searching Navidrome: {e}")
        return None
    except json.JSONDecodeError:
        print("Error decoding Navidrome JSON response.")
        return None

def create_playlist_in_navidrome(playlist_name, track_ids, navidrome_url, username, password):
    url = f"{navidrome_url}/rest/createPlaylist.view?u={username}&p={password}&v=1.16.1&c=flask-ollama-playlist&f=json&name={playlist_name}"
    if track_ids:
        url += "&" + "&amp;".join([f"songId={tid}" for tid in track_ids])
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data.get('subsonic-response', {}).get('status') == 'ok':
            playlist_id = data['subsonic-response'].get('playlist', {}).get('id')
            return playlist_id
        else:
            print(f"Error creating Navidrome playlist: {data.get('subsonic-response', {}).get('error', {}).get('message')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error creating Navidrome playlist: {e}")
        return None

def search_track_in_plex(artist, title, plex_url, plex_token, music_section_id):
    cache_key = f"{artist}_{title}_{music_section_id}"
    cached_result = plex_cache.get(cache_key)
    if cached_result:
        return cached_result

    search_url = f"{plex_url}/library/sections/{music_section_id}/search?type=10&query={artist} {title}&X-Plex-Token={plex_token}"
    headers = {'Accept': 'application/json'}
    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data.get('MediaContainer', {}).get('Metadata'):
            tracks = data['MediaContainer']['Metadata']
            for track in tracks:
                # Filter out live tracks if desired, or other criteria
                if 'live' in track.get('title', '').lower():
                    continue
                if artist.lower() in track.get('originalTitle', track.get('grandparentTitle', '')).lower() and title.lower() in track.get('title', '').lower():
                    plex_cache.set(cache_key, track.get('ratingKey'))
                    return track.get('ratingKey')
        plex_cache.set(cache_key, None) # Cache miss
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error searching Plex: {e}")
        return None
    except json.JSONDecodeError:
        print("Error decoding Plex JSON response.")
        return None

def create_playlist_in_plex(playlist_name, track_keys, plex_url, plex_token, machine_id, playlist_type, music_section_id):
    # Plex API requires track URIs for playlist creation
    track_uris = []
    for key in track_keys:
        track_uris.append(f"server://{machine_id}/com.plexapp.plugins.library/library/metadata/{key}")
    
    if not track_uris:
        print("No track URIs to add to Plex playlist.")
        return None

    # Create a comma-separated string of URIs
    uri_string = ",".join(track_uris)

    create_url = (
        f"{plex_url}/playlists?uri={uri_string}"
        f"&title={requests.utils.quote(playlist_name)}&smart=0&type={playlist_type}"
        f"&X-Plex-Token={plex_token}"
    )
    headers = {'Accept': 'application/json'}
    try:
        response = requests.post(create_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data.get('MediaContainer', {}).get('Metadata'):
            return data['MediaContainer']['Metadata'][0].get('ratingKey')
        else:
            print(f"Error creating Plex playlist. Response: {data}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error creating Plex playlist: {e}")
        return None
    except json.JSONDecodeError:
        print("Error decoding Plex JSON response for playlist creation.")
        return None

def generate_playlist_core(config, likes, dislikes, favorite_artists, playlist_name, playlist_description):
    ollama_url = get_config_value(config, 'OLLAMA', 'URL')
    ollama_model = get_config_value(config, 'OLLAMA', 'Model')
    context_window = get_config_value(config, 'OLLAMA', 'ContextWindow', '2048')
    max_attempts = int(get_config_value(config, 'OLLAMA', 'MaxAttempts', '3'))

    enable_navidrome = get_config_value(config, 'APP', 'EnableNavidrome', 'no').lower() == 'yes'
    navidrome_url = get_config_value(config, 'NAVIDROME', 'URL')
    navidrome_user = get_config_value(config, 'NAVIDROME', 'Username')
    navidrome_pass = get_config_value(config, 'NAVIDROME', 'Password')

    enable_plex = get_config_value(config, 'APP', 'EnablePlex', 'no').lower() == 'yes'
    plex_url = get_config_value(config, 'PLEX', 'ServerURL')
    plex_token = get_config_value(config, 'PLEX', 'Token')
    plex_machine_id = get_config_value(config, 'PLEX', 'MachineID')
    plex_playlist_type = get_config_value(config, 'PLEX', 'PlaylistType', 'audio')
    plex_music_section_id = get_config_value(config, 'PLEX', 'MusicSectionID')

    yield "Starting playlist generation...\n"

    if ollama_model.lower() == 'auto' or not ollama_model:
        yield "Attempting to auto-detect Ollama model...\n"
        try:
            models_response = requests.get(f"{ollama_url}/api/tags")
            models_response.raise_for_status()
            models_data = models_response.json()
            if models_data.get('models'):
                # Prefer Llama 3 or a common model, can be more sophisticated
                preferred_models = [m['name'] for m in models_data['models'] if 'llama3' in m['name'].lower() or 'mistral' in m['name'].lower()]
                if preferred_models:
                    ollama_model = preferred_models[0]
                else:
                    ollama_model = models_data['models'][0]['name'] # Fallback to first model
                yield f"Auto-detected Ollama model: {ollama_model}\n"
            else:
                yield "Could not auto-detect Ollama model, please specify one in settings.\n"
                ollama_model = 'llama3' # Default fallback
        except Exception as e:
            yield f"Error auto-detecting Ollama model: {e}. Using default 'llama3'.\n"
            ollama_model = 'llama3'

    generated_tracks = []
    for attempt in range(max_attempts):
        yield f"Attempt {attempt + 1} of {max_attempts} to generate tracks with Ollama...\n"
        prompt = generate_prompt(likes, dislikes, favorite_artists, generated_tracks)
        ollama_tracks = query_ollama(prompt, ollama_url, ollama_model, context_window)
        
        if ollama_tracks:
            newly_found_tracks = 0
            for track in ollama_tracks:
                if not any(t['artist'] == track['artist'] and t['title'] == track['title'] for t in generated_tracks):
                    generated_tracks.append(track)
                    newly_found_tracks +=1
            yield f"Ollama suggested {len(ollama_tracks)} tracks. {newly_found_tracks} new unique tracks added.\n"
            if len(generated_tracks) >= 10: # Stop if we have enough tracks
                break
        else:
            yield "Ollama did not return valid tracks this attempt.\n"
        if attempt < max_attempts - 1:
            yield "Waiting a moment before retrying...\n"
            time.sleep(random.randint(2,5)) # Brief pause before retrying

    if not generated_tracks:
        yield "Failed to generate tracks after multiple attempts.\n"
        return

    yield f"Generated {len(generated_tracks)} unique tracks from Ollama.\n"
    yield "Verifying and adding tracks to platforms...\n"

    navidrome_track_ids = []
    plex_track_keys = []
    final_playlist_tracks = []

    for track in generated_tracks:
        artist, title = track['artist'], track['title']
        yield f"  Processing: {artist} - {title}\n"
        found_on_platform = False

        if enable_navidrome and navidrome_url and navidrome_user and navidrome_pass:
            yield f"    Searching on Navidrome... "
            nav_track_id = search_track_in_navidrome(artist, title, navidrome_url, navidrome_user, navidrome_pass)
            if nav_track_id:
                navidrome_track_ids.append(nav_track_id)
                final_playlist_tracks.append({'artist': artist, 'title': title, 'found_on': 'Navidrome'})
                yield "Found.\n"
                found_on_platform = True
            else:
                yield "Not found.\n"
        
        if enable_plex and plex_url and plex_token and plex_music_section_id and not found_on_platform: # Only search Plex if not found on Navidrome or Navidrome disabled
            yield f"    Searching on Plex... "
            plex_track_key = search_track_in_plex(artist, title, plex_url, plex_token, plex_music_section_id)
            if plex_track_key:
                plex_track_keys.append(plex_track_key)
                final_playlist_tracks.append({'artist': artist, 'title': title, 'found_on': 'Plex'})
                yield "Found.\n"
                found_on_platform = True # Mark as found even if it was on Navidrome before
            else:
                yield "Not found.\n"
        
        if not found_on_platform:
            final_playlist_tracks.append({'artist': artist, 'title': title, 'found_on': 'None'})
            yield "    Not found on any enabled platform.\n"

    if not final_playlist_tracks:
        yield "No tracks found on any enabled platform.\n"
        return

    # Create playlists
    navidrome_playlist_id = None
    if enable_navidrome and navidrome_track_ids:
        yield f"Creating playlist '{playlist_name}' on Navidrome with {len(navidrome_track_ids)} tracks...\n"
        navidrome_playlist_id = create_playlist_in_navidrome(playlist_name, navidrome_track_ids, navidrome_url, navidrome_user, navidrome_pass)
        if navidrome_playlist_id:
            yield f"Navidrome playlist created successfully (ID: {navidrome_playlist_id}).\n"
            save_playlist_history(playlist_name, playlist_description, 
                                  [t for t in final_playlist_tracks if t['found_on'] == 'Navidrome'], 
                                  'Navidrome', navidrome_playlist_id)
        else:
            yield "Failed to create Navidrome playlist.\n"

    plex_playlist_id = None
    if enable_plex and plex_track_keys:
        yield f"Creating playlist '{playlist_name}' on Plex with {len(plex_track_keys)} tracks...\n"
        plex_playlist_id = create_playlist_in_plex(playlist_name, plex_track_keys, plex_url, plex_token, plex_machine_id, plex_playlist_type, plex_music_section_id)
        if plex_playlist_id:
            yield f"Plex playlist created successfully (ID: {plex_playlist_id}).\n"
            save_playlist_history(playlist_name, playlist_description, 
                                  [t for t in final_playlist_tracks if t['found_on'] == 'Plex'], 
                                  'Plex', plex_playlist_id)
        else:
            yield "Failed to create Plex playlist.\n"
    
    if not navidrome_playlist_id and not plex_playlist_id and (enable_navidrome or enable_plex):
         yield "Could not create playlist on any enabled and configured platform.\n"
    elif not enable_navidrome and not enable_plex:
        yield "No platforms enabled. Playlist generated but not saved to any service.\n"
        # Save a local-only history entry
        save_playlist_history(playlist_name, playlist_description, final_playlist_tracks, 'Local')

    yield "Playlist generation process complete.\n"
    yield f"Final playlist tracks: {json.dumps(final_playlist_tracks, indent=2)}\n"

# --- Routes ---
@main_bp.route('/')
def home():
    config = load_config()
    context = {
        'ollama_url': get_config_value(config, 'OLLAMA', 'URL'),
        'ollama_model': get_config_value(config, 'OLLAMA', 'Model'),
        'navidrome_url': get_config_value(config, 'NAVIDROME', 'URL'),
        'navidrome_username': get_config_value(config, 'NAVIDROME', 'Username'),
        'navidrome_password': get_config_value(config, 'NAVIDROME', 'Password'),
        'context_window': get_config_value(config, 'OLLAMA', 'ContextWindow', '2048'),
        'max_attempts': get_config_value(config, 'OLLAMA', 'MaxAttempts', '3'),
        'likes': get_config_value(config, 'APP', 'Likes'),
        'dislikes': get_config_value(config, 'APP', 'Dislikes'),
        'favorite_artists': get_config_value(config, 'APP', 'FavoriteArtists'),
        'enable_navidrome': get_config_value(config, 'APP', 'EnableNavidrome', 'no'),
        'enable_plex': get_config_value(config, 'APP', 'EnablePlex', 'no'),
        'plex_server_url': get_config_value(config, 'PLEX', 'ServerURL'),
        'plex_token': get_config_value(config, 'PLEX', 'Token'),
        'plex_machine_id': get_config_value(config, 'PLEX', 'MachineID'),
        'plex_playlist_type': get_config_value(config, 'PLEX', 'PlaylistType', 'audio'),
        'plex_music_section_id': get_config_value(config, 'PLEX', 'MusicSectionID')
    }
    return render_template('index.html', **context)

@main_bp.route('/generate', methods=['POST'])
def generate():
    data = request.form
    action = data.get('action')
    config = load_config()

    if action == 'save':
        if save_config(data):
            return jsonify({'success': True, 'message': 'Settings saved successfully.'})
        else:
            return jsonify({'success': False, 'message': 'Failed to save settings.'}), 500
    
    elif action == 'generate':
        likes = data.get('likes')
        dislikes = data.get('dislikes')
        favorite_artists = data.get('favorite_artists')
        playlist_name = data.get('playlist_name', 'Ollama Generated Playlist')
        playlist_description = data.get('playlist_description', '')

        if not playlist_name:
            playlist_name = f"Ollama Mix - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"

        return Response(generate_playlist_core(config, likes, dislikes, favorite_artists, playlist_name, playlist_description), mimetype='text/plain')
    
    return jsonify({'success': False, 'message': 'Invalid action.'}), 400

@main_bp.route('/history')
def history_page():
    history = get_playlist_history()
    return render_template('history.html', history=history)

@main_bp.route('/history/rate/<playlist_id>', methods=['POST'])
def rate_history_entry(playlist_id):
    rating = request.form.get('rating')
    if rating is None:
        return jsonify({'success': False, 'message': 'Rating not provided.'}), 400
    try:
        rate_playlist_entry(playlist_id, rating)
        return jsonify({'success': True, 'message': 'Rating updated.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@main_bp.route('/shared-playlist/<playlist_id>')
def shared_playlist(playlist_id):
    history = get_playlist_history()
    playlist = None
    
    for entry in history:
        if entry['id'] == playlist_id:
            playlist = entry
            break
    
    if not playlist:
        return render_template('shared_not_found.html')
    
    return render_template('shared_playlist.html', playlist=playlist)

@main_bp.route('/settings', methods=['GET', 'POST'])
def settings_page():
    config = load_config()
    if request.method == 'POST':
        if save_config(request.form):
            # Could add a success message via flash or similar
            pass 
    context = {
        'ollama_url': get_config_value(config, 'OLLAMA', 'URL'),
        'ollama_model': get_config_value(config, 'OLLAMA', 'Model'),
        'navidrome_url': get_config_value(config, 'NAVIDROME', 'URL'),
        'navidrome_username': get_config_value(config, 'NAVIDROME', 'Username'),
        'navidrome_password': get_config_value(config, 'NAVIDROME', 'Password'),
        'context_window': get_config_value(config, 'OLLAMA', 'ContextWindow', '2048'),
        'max_attempts': get_config_value(config, 'OLLAMA', 'MaxAttempts', '3'),
        'likes': get_config_value(config, 'APP', 'Likes'),
        'dislikes': get_config_value(config, 'APP', 'Dislikes'),
        'favorite_artists': get_config_value(config, 'APP', 'FavoriteArtists'),
        'enable_navidrome': get_config_value(config, 'APP', 'EnableNavidrome', 'no'),
        'enable_plex': get_config_value(config, 'APP', 'EnablePlex', 'no'),
        'plex_server_url': get_config_value(config, 'PLEX', 'ServerURL'),
        'plex_token': get_config_value(config, 'PLEX', 'Token'),
        'plex_machine_id': get_config_value(config, 'PLEX', 'MachineID'),
        'plex_playlist_type': get_config_value(config, 'PLEX', 'PlaylistType', 'audio'),
        'plex_music_section_id': get_config_value(config, 'PLEX', 'MusicSectionID')
    }
    return render_template('settings.html', **context)
