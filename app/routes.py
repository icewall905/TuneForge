from flask import Blueprint, render_template, request, jsonify, Response, current_app, send_file
import requests
import json
import configparser
import os
import datetime
import time
import re
import random
import xml.etree.ElementTree as ET
from urllib.parse import quote
import logging
from logging.handlers import RotatingFileHandler
import sqlite3
from pathlib import Path
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from collections import OrderedDict
import hashlib
import threading
import queue
import uuid
from datetime import datetime
import string

# --- Logger Setup ---
LOG_DIR = 'logs'  # This will be relative to the project root (TuneForge/)
DB_DIR = 'db'    # Database directory
# Ensure the log directory exists
os.makedirs(LOG_DIR, exist_ok=True)
# Ensure the database directory exists
os.makedirs(DB_DIR, exist_ok=True)

app_file_logger = logging.getLogger('TuneForgeApp')
app_file_logger.setLevel(logging.DEBUG)  # Process all levels from debug_log

# Check if a similar handler already exists to prevent duplicates during reloads
handler_exists = any(
    isinstance(h, RotatingFileHandler) and \
    getattr(h, 'baseFilename', '') == os.path.abspath(os.path.join(LOG_DIR, 'tuneforge_app.log'))
    for h in app_file_logger.handlers
)

if not handler_exists:
    log_file_path = os.path.join(LOG_DIR, 'tuneforge_app.log')
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=5*1024*1024,  # 5 MB
        backupCount=5,
        encoding='utf-8'
    )
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    app_file_logger.addHandler(file_handler)
    # If you also want these logs in the console (in addition to the file), uncomment below
    # console_handler = logging.StreamHandler()
    # console_handler.setFormatter(formatter)
    # app_file_logger.addHandler(console_handler)

# --- Global Debug Flags ---
DEBUG_ENABLED = True  # Master debug switch
DEBUG_OLLAMA_RESPONSE = False  # Specific for Ollama response logging, can also be set in config.ini

# --- Navidrome search caching and HTTP session ---
NAVIDROME_SEARCH_CACHE = OrderedDict()
NAVIDROME_CACHE_MAX_SIZE = 300
try:
    NAVIDROME_SESSION = requests.Session()
except Exception:
    NAVIDROME_SESSION = requests

main_bp = Blueprint('main', __name__)

# Jinja2 custom filters
def filesizeformat(bytes):
    """Convert bytes to human readable format"""
    if bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while bytes >= 1024 and i < len(size_names) - 1:
        bytes /= 1024.0
        i += 1
    return f"{bytes:.1f} {size_names[i]}"

# Register the filter with the blueprint
main_bp.add_app_template_filter(filesizeformat, 'filesizeformat')

CONFIG_FILE = 'config.ini'
HISTORY_FILE = 'playlist_history.json'

# --- Config Functions ---
def load_config():
    config = configparser.ConfigParser()
    # Preserve case for keys
    config.optionxform = lambda optionstr: optionstr  # Preserve case
    if not os.path.exists(CONFIG_FILE):
        # Fallback to example if main config doesn't exist, or create empty
        example_config_file = CONFIG_FILE + '.example'
        if os.path.exists(example_config_file):
            debug_log(f"{CONFIG_FILE} not found, loading {example_config_file}", "WARN")
            config.read(example_config_file)
            # Optionally save it as config.ini now
            # with open(CONFIG_FILE, 'w') as f:
            #     config.write(f)
        else:
            debug_log(f"{CONFIG_FILE} and {example_config_file} not found. Using empty config.", "WARN")
            # Setup default sections if needed, or let it be empty
            config.add_section('OLLAMA')
            config.add_section('APP')
            config.add_section('NAVIDROME')
            config.add_section('PLEX')
    else:
        config.read(CONFIG_FILE)
    return config

def get_config_value(section, key, default=None):
    config = load_config()
    if config.has_section(section):
        # Try exact key match first (case-sensitive)
        if key in config[section]:
            return config[section][key]
        # Fall back to case-insensitive lookup for legacy configs
        lower_key = key.lower()
        for existing_key in config[section].keys():
            if existing_key.lower() == lower_key:
                return config[section][existing_key]
    return default

def save_config(data_dict):
    config = configparser.ConfigParser()
    config.optionxform = lambda optionstr: optionstr # Preserve case for keys when writing
    for section, options in data_dict.items():
        if not config.has_section(section):
            config.add_section(section)
        for key, value in options.items():
            config.set(section, key, str(value))
    try:
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
        debug_log(f"Configuration saved to {CONFIG_FILE}", "INFO")
    except Exception as e:
        debug_log(f"Error writing configuration to {CONFIG_FILE}: {e}", "ERROR", True)
        raise # Re-raise to inform the caller

# --- Playlist History Functions ---
def load_playlist_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r') as f:
            # Handle empty file
            content = f.read()
            if not content:
                return []
            history_data = json.loads(content)
            if isinstance(history_data, dict): # Handles case where a single playlist might have been saved directly
                return [history_data]
            elif not isinstance(history_data, list): # Handles malformed file (should be list)
                 debug_log(f"Playlist history file {HISTORY_FILE} does not contain a list. Resetting.", "WARN", True)
                 return []
            return history_data
    except json.JSONDecodeError:
        debug_log(f"Error decoding JSON from {HISTORY_FILE}. File might be corrupted or empty.", "ERROR", True)
        return [] # Return empty list on error
    except Exception as e:
        debug_log(f"An error occurred while loading playlist history: {e}", "ERROR", True)
        return []

def save_playlist_history(history_data):
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history_data, f, indent=4)
        debug_log(f"Playlist history saved to {HISTORY_FILE}", "INFO")
    except Exception as e:
        debug_log(f"Error saving playlist history to {HISTORY_FILE}: {e}", "ERROR", True)

# --- Debug Logging ---
_debug_flags_printed = False # Module-level flag to print debug status only once

def debug_log(message, level="INFO", force=False):
    global DEBUG_ENABLED, _debug_flags_printed
    # Check if debug is enabled in config - avoid circular dependency
    try:
        # Try to get config value directly without going through the full config loading cycle
        if os.path.exists(CONFIG_FILE):
            temp_config = configparser.ConfigParser()
            temp_config.optionxform = lambda optionstr: optionstr
            temp_config.read(CONFIG_FILE)
            if temp_config.has_section('APP') and 'Debug' in temp_config['APP']:
                debug_from_config_str = temp_config['APP']['Debug']
            else:
                debug_from_config_str = 'yes'  # Default fallback
        else:
            debug_from_config_str = 'yes'  # Default fallback
    except Exception:
        debug_from_config_str = 'yes'  # Default fallback on any error
    
    debug_from_config = debug_from_config_str.lower() in ('yes', 'true', '1') if isinstance(debug_from_config_str, str) else False

    # Print status once
    if not _debug_flags_printed:
        print(f"[TuneForge Logger Init] DEBUG_ENABLED: {DEBUG_ENABLED}, Config 'APP','Debug': '{debug_from_config_str}', Parsed debug_from_config: {debug_from_config}")
        # Add an immediate test DEBUG message to verify logging works at that level
        app_file_logger.debug("This is a test DEBUG message during logger initialization")
        app_file_logger.info("This is a test INFO message during logger initialization")
        _debug_flags_printed = True
    
    if force or (DEBUG_ENABLED and debug_from_config):
        level_upper = level.upper()
        if level_upper == "DEBUG":
            app_file_logger.debug(message)
        elif level_upper == "INFO":
            app_file_logger.info(message)
        elif level_upper == "WARNING" or level_upper == "WARN":
            app_file_logger.warning(message)
        elif level_upper == "ERROR":
            app_file_logger.error(message)
        elif level_upper == "CRITICAL":
            app_file_logger.critical(message)
        else:
            # For unknown levels, log as INFO with the original level string in the message
            app_file_logger.info(f"[{level}] {message}")

# --- Ollama Interaction ---
def generate_tracks_with_ollama(ollama_url, ollama_model, prompt, num_songs, attempt_num=0, previously_suggested_tracks=None):
    global DEBUG_OLLAMA_RESPONSE # Global flag for verbose Ollama response logging
    # Configurable flag for verbose Ollama response logging
    config_debug_ollama = get_config_value('OLLAMA', 'DebugOllamaResponse', 'no').lower() in ('yes', 'true', '1')


    debug_log(f"Ollama: Attempting to generate {num_songs} tracks. Attempt: {attempt_num + 1}", "INFO")

    likes = get_config_value('APP', 'Likes', '')
    dislikes = get_config_value('APP', 'Dislikes', '')
    favorite_artists = get_config_value('APP', 'FavoriteArtists', '')
    # context_window = int(get_config_value('OLLAMA', 'ContextWindow', '2048')) # Not directly used here

    context_str = ""
    recent_suggestions_for_prompt = []
    if previously_suggested_tracks and attempt_num > 0:
        seen_in_context = set()
        # Look at last N suggestions (e.g., 50) to avoid overly long context
        for track in reversed(previously_suggested_tracks[-50:]): 
            track_key = (track.get("title", "").lower(), track.get("artist", "").lower())
            if track.get("title") and track.get("artist") and track_key not in seen_in_context:
                recent_suggestions_for_prompt.append(f"- '{track['title']}' by '{track['artist']}'")
                seen_in_context.add(track_key)
            if len(recent_suggestions_for_prompt) >= 25: # Limit context to ~25 distinct tracks
                break
    if recent_suggestions_for_prompt:
        context_str = "\\n\\nCRITICAL: To avoid repetition, DO NOT suggest any of the following tracks again. These have already been suggested and should be completely avoided:\\n" + "\\n".join(reversed(recent_suggestions_for_prompt))

    retry_guidance = ""
    if attempt_num > 0:
        retry_guidance = (
            "\\n\\nCRITICAL: Your previous suggestions included repeats, undesirable versions, or didn't match well. "
            "You MUST provide COMPLETELY DIFFERENT suggestions this time. "
            "Focus on well-known, studio-recorded songs. STRICTLY AVOID live versions, instrumentals, karaoke, covers, remixes, demos, and edits unless the prompt specifically asks for them. "
            "Ensure maximum variety and avoid any tracks that might be similar to previous suggestions. "
            "Think of different artists, different time periods, and different sub-genres within the requested style."
        )

    full_prompt = (
        f"You are a helpful music expert. Generate a list of exactly {num_songs} unique songs based on the following prompt: '{prompt}'.\\n"
        f"User Likes: {likes}\\nUser Dislikes: {dislikes}\\nUser Favorite Artists: {favorite_artists}\\n"
        f"Format each song strictly as 'Title - Artist - Album'. If an album is not applicable or known, use 'Unknown Album'.\\n"
        f"Each song must be on a new line. Do not include numbering, introductory/closing remarks, or any other text, just the songs in the specified format."
        f"{context_str}"
        f"{retry_guidance}"
    )

    # debug_log(f"Ollama full prompt:\\n{full_prompt}", "DEBUG") # Can be very verbose

    payload = {
        "model": ollama_model,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": float(get_config_value('OLLAMA', 'Temperature', '0.7')),
            "top_p": float(get_config_value('OLLAMA', 'TopP', '0.9')),
            "num_ctx": int(get_config_value('OLLAMA', 'ContextWindow', '2048')), # Max context window
            # "seed": random.randint(0, 2**32 -1) # For more deterministic results if needed for testing
        }
    }
    
    try:
        response = requests.post(f"{ollama_url.rstrip('/')}/api/generate", json=payload, timeout=120) # Increased timeout
        response.raise_for_status()
        response_data = response.json()

        if DEBUG_OLLAMA_RESPONSE or config_debug_ollama:
            debug_log(f"Ollama raw response JSON: {json.dumps(response_data)}", "DEBUG", True)

        content = response_data.get("response", "").strip()
        if not content:
            debug_log("Ollama response content is empty.", "WARN", True)
            return []

        debug_log(f"Ollama raw response content: {repr(content[:200])}...", "DEBUG")
        
        tracks = []
        lines = content.split('\n')
        debug_log(f"Ollama: Split response into {len(lines)} lines", "DEBUG")
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line: 
                debug_log(f"Ollama: Skipping empty line {i+1}", "DEBUG")
                continue
            parts = line.split(' - ')
            debug_log(f"Ollama: Line {i+1}: '{line}' -> {len(parts)} parts: {parts}", "DEBUG")
            
            if len(parts) >= 2:
                title = parts[0].strip().strip('\"\'')
                artist = parts[1].strip().strip('\"\'')
                album = parts[2].strip().strip('\"\'') if len(parts) >= 3 else "Unknown Album"
                if title and artist:
                    tracks.append({"title": title, "artist": artist, "album": album})
                    debug_log(f"Ollama: Parsed track {len(tracks)}: '{title}' by '{artist}'", "DEBUG")
                else:
                    debug_log(f"Ollama: Skipping line {i+1} - missing title or artist: title='{title}', artist='{artist}'", "DEBUG")
            else:
                debug_log(f"Ollama: Could not parse line {i+1}: '{line}' (expected format: Title - Artist - Album)", "WARN")
        
        debug_log(f"Ollama generated {len(tracks)} tracks from response.", "INFO")
        return tracks

    except requests.exceptions.Timeout:
        debug_log(f"Error calling Ollama: Timeout after 120 seconds.", "ERROR", True)
        return []
    except requests.exceptions.RequestException as e:
        debug_log(f"Error calling Ollama: {e}", "ERROR", True)
        return []
    except json.JSONDecodeError as e:
        debug_log(f"Error decoding Ollama JSON response: {e}. Response text: {response.text[:200] if 'response' in locals() else 'N/A'}", "ERROR", True)
        return []
    except Exception as e:
        debug_log(f"Unexpected error in generate_tracks_with_ollama: {e}", "ERROR", True)
        return []

# --- Navidrome Functions ---
def test_navidrome_connection(navidrome_url, username, password):
    result = {'success': False, 'error': None, 'details': {}, 'server_info': None}
    if not all([navidrome_url, username, password]):
        result['error'] = "Navidrome URL, Username, or Password missing."
        return result
    
    base_url = navidrome_url.rstrip('/')
    if '/rest' not in base_url: base_url = f"{base_url}/rest"
    result['details']['final_url'] = base_url
    
    ping_url = f"{base_url}/ping.view"
    params = {'u': username, 'p': password, 'v': '1.16.1', 'c': 'TuneForge', 'f': 'json'}
    
    try:
        ping_response = requests.get(ping_url, params=params, timeout=10)
        result['details']['ping_status_code'] = ping_response.status_code
        ping_response.raise_for_status() # Check for HTTP errors first
        
        ping_data = ping_response.json()
        result['details']['ping_response'] = ping_data
        
        if ping_data.get('subsonic-response', {}).get('status') == 'ok':
            result['success'] = True
            # Try to get server version info
            system_url = f"{base_url}/getSystemInfo.view"
            system_response = requests.get(system_url, params=params, timeout=10)
            if system_response.status_code == 200:
                system_data = system_response.json()
                if system_data.get('subsonic-response', {}).get('status') == 'ok':
                    result['server_info'] = system_data.get('subsonic-response', {}).get('systemInfo', {})
        else:
            error = ping_data.get('subsonic-response', {}).get('error', {})
            result['error'] = f"API Error: {error.get('message')} (code {error.get('code')})"
            
    except requests.exceptions.HTTPError as e:
        result['error'] = f"HTTP Error: {e.response.status_code} - {e.response.reason}. URL: {ping_url}"
        try: result['details']['ping_response_text'] = e.response.text[:500]
        except: pass
    except requests.exceptions.ConnectionError:
        result['error'] = f"Connection error - could not connect to Navidrome server at {navidrome_url}"
    except requests.exceptions.Timeout:
        result['error'] = "Connection timed out"
    except json.JSONDecodeError:
        result['error'] = "Could not parse JSON response from server"
        result['details']['ping_response_text'] = ping_response.text[:500] if 'ping_response' in locals() else "N/A"
    except requests.exceptions.RequestException as e:
        result['error'] = f"Request error: {str(e)}"
    return result

def search_track_in_navidrome(query, navidrome_url, username, password):
    if not navidrome_url: return []
    base_url = navidrome_url.rstrip('/')
    if '/rest' not in base_url: base_url = f"{base_url}/rest"
    
    url = f"{base_url}/search3.view"
    params = {
        'u': username, 'p': password, 'v': '1.16.1', 'c': 'TuneForge', 'f': 'json',
        'query': query, 'songCount': 100, 'artistCount': 0, 'albumCount': 0
    }
    # Build a cache key
    cache_key = (url, tuple(sorted(params.items())))
    if cache_key in NAVIDROME_SEARCH_CACHE:
        cached = NAVIDROME_SEARCH_CACHE.pop(cache_key)
        NAVIDROME_SEARCH_CACHE[cache_key] = cached  # move to end (LRU)
        return cached
    try:
        # Use shared session and a short timeout to avoid long stalls
        response = NAVIDROME_SESSION.get(url, params=params, timeout=4)
        response.raise_for_status()
        data = response.json()
        
        if data.get('subsonic-response', {}).get('status') == 'ok':
            songs = data.get('subsonic-response', {}).get('searchResult3', {}).get('song', [])
            # debug_log(f"Navidrome: Found {len(songs)} songs for query '{query}'", "DEBUG")
            tracks = []
            for song in songs:
                tracks.append({
                    'id': song.get('id'), 'title': song.get('title', 'Unknown Title'),
                    'artist': song.get('artist', 'Unknown Artist'), 'album': song.get('album', 'Unknown Album'),
                    'source': 'navidrome'
                })
            # Update LRU cache
            NAVIDROME_SEARCH_CACHE[cache_key] = tracks
            if len(NAVIDROME_SEARCH_CACHE) > NAVIDROME_CACHE_MAX_SIZE:
                NAVIDROME_SEARCH_CACHE.popitem(last=False)
            return tracks
        else:
            # error_message = data.get('subsonic-response', {}).get('error', {}).get('message')
            # debug_log(f"Navidrome: Error searching: {error_message}", "WARN")
            return []
    except requests.exceptions.RequestException: # Catches HTTPError, Timeout, ConnectionError
        # debug_log(f"Navidrome: Request error searching: {e}", "WARN")
        return []
    except json.JSONDecodeError:
        # debug_log(f"Navidrome: Error decoding search JSON response: {e}", "WARN")
        return []

def create_playlist_in_navidrome(navidrome_url, username, password, playlist_name, track_ids):
    if not navidrome_url:
        debug_log("Navidrome URL not configured, cannot create playlist.", "ERROR", True)
        return None
    base_url = navidrome_url.rstrip('/')
    if '/rest' not in base_url: base_url = f"{base_url}/rest"
    
    url = f"{base_url}/createPlaylist.view" # This creates or updates if name exists
    params = {
        'u': username, 'p': password, 'v': '1.16.1', 'c': 'TuneForge', 
        'f': 'json', 'name': playlist_name
    }
    if track_ids: params['songId'] = track_ids
        
    debug_log(f"Navidrome: Creating/updating playlist '{playlist_name}' with {len(track_ids) if track_ids else 0} tracks.", "INFO", True)
    try:
        response = requests.get(url, params=params, timeout=30)
        # debug_log(f"Navidrome create playlist full URL: {response.url}", "DEBUG")
        response.raise_for_status()
        data = response.json()
        # debug_log(f"Navidrome create playlist response: {json.dumps(data)[:200]}...", "DEBUG")
        
        if data.get('subsonic-response', {}).get('status') == 'ok':
            playlist_data = data['subsonic-response'].get('playlist', {})
            playlist_id = playlist_data.get('id')
            actual_song_count = playlist_data.get('songCount', 'N/A')
            debug_log(f"Navidrome: Successfully created/updated playlist '{playlist_name}' (ID: {playlist_id}). Reported tracks: {actual_song_count}.", "INFO", True)
            return playlist_id
        else:
            error_message = data.get('subsonic-response', {}).get('error', {}).get('message', 'Unknown error')
            debug_log(f"Navidrome: Error creating playlist '{playlist_name}': {error_message}", "ERROR", True)
            return None
    except requests.exceptions.RequestException as e:
        debug_log(f"Navidrome: Request error creating playlist '{playlist_name}': {e}", "ERROR", True)
        return None
    except json.JSONDecodeError as e:
        debug_log(f"Navidrome: JSON decode error for playlist '{playlist_name}': {e}. Response: {response.text[:200] if 'response' in locals() else 'N/A'}", "ERROR", True)
        return None

def normalize_string(text):
    """Normalize a string for better comparison by removing common suffixes and special characters"""
    if not text:
        return ""
    
    # Convert to lowercase
    normalized = text.lower()
    
    # Remove common suffixes in parentheses
    import re
    normalized = re.sub(r'\s*\([^)]*\)', '', normalized)  # Remove (Live), (Remastered), etc.
    normalized = re.sub(r'\s*\[[^\]]*\]', '', normalized)  # Remove [Remix], [Album Version], etc.
    
    # Remove special characters and extra whitespace
    normalized = re.sub(r'[^\w\s]', ' ', normalized)  # Replace special chars with spaces
    normalized = re.sub(r'\s+', ' ', normalized)       # Multiple spaces to single space
    normalized = normalized.strip()
    
    return normalized

def calculate_similarity(str1, str2):
    """Calculate similarity between two strings using multiple methods"""
    if not str1 or not str2:
        return 0.0
    
    # Normalize both strings
    norm1 = normalize_string(str1)
    norm2 = normalize_string(str2)
    
    # Exact match after normalization
    if norm1 == norm2:
        return 1.0
    
    # Word-based similarity
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    
    if not words1 or not words2:
        return 0.0
    
    # Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    word_similarity = intersection / union if union > 0 else 0.0
    
    # Character-based similarity (for handling typos)
    import difflib
    char_similarity = difflib.SequenceMatcher(None, norm1, norm2).ratio()
    
    # Return the higher of the two similarities
    return max(word_similarity, char_similarity)

def is_unwanted_version(title, album=None):
    """Return True if the track looks like a live/remaster/demo/acoustic/etc. version we should avoid."""
    def has_any_keyword(text):
        if not text:
            return False
        t = text.lower()
        keywords = [
            ' live ', ' live-', ' live_', '(live', '[live',
            ' remaster', '(remaster', '[remaster', ' remastered',
            ' acoustic', '(acoustic', '[acoustic',
            ' demo', '(demo', '[demo',
            ' edit', '(edit', '[edit',
            ' karaoke', ' instrumental'
        ]
        # Add boundary spaces to catch plain suffix/prefix
        t_spaced = f" {t} "
        return any(k in t_spaced for k in keywords)

    return has_any_keyword(title) or has_any_keyword(album)

def search_tracks_in_navidrome(navidrome_url, username, password, ollama_suggested_tracks, final_unique_matched_tracks_map):
    """Search for tracks in Navidrome and add them to the final matched tracks map"""
    if not all([navidrome_url, username, password]):
        debug_log("Navidrome credentials/URL missing, skipping Navidrome search batch.", "WARN")
        return []
    
    newly_matched_for_batch = []

    # Build pending list skipping already matched
    pending = []
    for suggested_track in ollama_suggested_tracks:
        title, artist = suggested_track.get("title"), suggested_track.get("artist")
        if not title or not artist:
            continue
        track_key = (title.lower(), artist.lower())
        if track_key in final_unique_matched_tracks_map:
            continue
        pending.append((track_key, suggested_track, title, artist))

    if not pending:
        return newly_matched_for_batch

    # Concurrency control from config
    try:
        max_workers = int(get_config_value('APP', 'NavidromeMaxConcurrency', '10'))
    except Exception:
        max_workers = 10

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def build_query(t, a):
        st = t.replace('"', '\\"')
        sa = a.replace('"', '\\"')
        return f'"{st}" "{sa}"'
    
    def build_search_strategies(title, artist):
        """Build multiple search strategies for better matching"""
        strategies = []
        
        # Strategy 1: Artist + Title (often works best)
        if title and artist:
            strategies.append(('artist_title', f'"{artist}" "{title}"'))
        
        # Strategy 2: Title only (can find tracks when artist info is complex)
        if title:
            strategies.append(('title_only', f'"{title}"'))
        
        # Strategy 3: Artist only (fallback for artist-based search)
        if artist:
            strategies.append(('artist_only', f'"{artist}"'))
        
        # Strategy 4: Title + Artist (original strategy)
        if title and artist:
            strategies.append(('title_artist', f'"{title}" "{artist}"'))
        
        return strategies

    def evaluate_results(title, artist, results):
        best = None
        best_score = 0.0
        for nt in results[:20]:
            if is_unwanted_version(nt.get('title'), nt.get('album')):
                continue
            ts = calculate_similarity(title, nt['title'])
            ars = calculate_similarity(artist, nt['artist'])
            combined = (ts * 0.7) + (ars * 0.3)
            if combined > best_score and combined >= 0.82 and ts >= 0.88 and ars >= 0.70:
                best = nt
                best_score = combined
                if combined >= 0.92 and ts >= 0.92:
                    break
        return best

    # Submit primary searches concurrently
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {}
        for track_key, suggested_track, title, artist in pending:
            # Try multiple search strategies for better matching
            search_strategies = build_search_strategies(title, artist)
            navidrome_tracks = []
            used_strategy = None
            
            # Try each strategy until we find a match
            for strategy_type, query in search_strategies:
                try:
                    navidrome_tracks = search_track_in_navidrome(query, navidrome_url, username, password)
                    if navidrome_tracks:
                        used_strategy = f"{strategy_type}: {query}"
                        debug_log(f"Navidrome: Found match using strategy: {used_strategy}", 'DEBUG')
                        break
                except Exception as e:
                    debug_log(f"Search strategy '{strategy_type}: {query}' failed: {e}", 'WARN')
                    continue
            
            if navidrome_tracks:
                future = executor.submit(lambda: navidrome_tracks, None)  # Return the found tracks directly
                future_to_item[future] = (track_key, suggested_track, title, artist, used_strategy)
            else:
                debug_log(f"Navidrome: No matches found for '{title}' by '{artist}' with any strategy", 'DEBUG')

        # Process as results arrive
        # Optional: determine target to allow early stop
        target_songs = None
        if hasattr(api_generate_playlist, 'playlist_progress'):
            for _pid, _p in api_generate_playlist.playlist_progress.items():
                if _p.get('status') in ['starting', 'progress']:
                    target_songs = _p.get('target_songs')
                    break

        for future in as_completed(future_to_item):
            future_data = future_to_item[future]
            if len(future_data) == 5:  # New format with strategy
                track_key, suggested_track, title, artist, used_strategy = future_data
                found_navidrome_tracks = future.result() or []
            else:  # Fallback for old format
                track_key, suggested_track, title, artist = future_data
                used_strategy = "legacy"
                try:
                    found_navidrome_tracks = future.result() or []
                except Exception:
                    found_navidrome_tracks = []

            if found_navidrome_tracks:
                best_match = evaluate_results(title, artist, found_navidrome_tracks)
            else:
                best_match = None

            if best_match:
                match_details = {
                    'id': best_match['id'], 'title': best_match['title'], 'artist': best_match['artist'],
                    'album': best_match['album'], 'source': 'navidrome',
                    'original_suggestion': {'title': title, 'artist': artist, 'album': suggested_track.get('album')},
                    'search_strategy': used_strategy
                }
                final_unique_matched_tracks_map[track_key] = match_details
                newly_matched_for_batch.append(match_details)

                # Update progress for individual track match
                if hasattr(api_generate_playlist, 'playlist_progress'):
                    for playlist_id, progress in api_generate_playlist.playlist_progress.items():
                        if progress['status'] in ['starting', 'progress']:
                            progress.update({
                                'current_status': f'Matched: {best_match["artist"]} - {best_match["title"]}. Currently at tracks {len(final_unique_matched_tracks_map)}/{progress.get("target_songs", "?")}.',
                                'current_track': f'{best_match["artist"]} - {best_match["title"]}',
                                'tracks_found': len(final_unique_matched_tracks_map)
                            })
                            break

                # Early stop if we reached target
                if target_songs and len(final_unique_matched_tracks_map) >= int(target_songs):
                    try:
                        executor.shutdown(wait=False, cancel_futures=True)
                    except Exception:
                        pass
                    break
            else:
                debug_log(f"Navidrome: ❌ No suitable match found for '{title}' by '{artist}'", "DEBUG")

    return newly_matched_for_batch

# --- Plex Functions ---
def search_track_in_plex(plex_url, plex_token, title, artist, album, library_section_id):
    if not all([plex_url, plex_token, library_section_id]):
        debug_log("Plex URL, Token, or Library Section ID not configured. Skipping Plex search.", "WARN")
        return None

    headers = {'X-Plex-Token': plex_token, 'Accept': 'application/json'}
    search_path = f"/library/sections/{library_section_id}/all"
    params = {'type': '10', 'title': title, 'grandparentTitle': artist, 'X-Plex-Token': plex_token}
    if album and album.lower() != "unknown album": params['parentTitle'] = album

    full_url = f"{plex_url.rstrip('/')}{search_path}"
    debug_log(f"Plex: Searching URL='{full_url}', Params='{ {k:v for k,v in params.items() if k != 'X-Plex-Token'} }'", "DEBUG")

    try:
        response = requests.get(full_url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        if data.get('MediaContainer') and data['MediaContainer'].get('Metadata'):
            debug_log(f"Plex: Found {len(data['MediaContainer']['Metadata'])} potential matches for '{title}' by '{artist}'", "DEBUG")
            
            for track_info in data['MediaContainer']['Metadata']: # Iterate through results
                track_id = track_info.get('ratingKey')
                found_title = track_info.get('title')
                found_artist = track_info.get('grandparentTitle') # Artist
                found_album = track_info.get('parentTitle')    # Album
                track_section_id = track_info.get('librarySectionID')
                
                # Debug log each potential match's details
                debug_log(f"Plex: Checking match: Title='{found_title}', Artist='{found_artist}', Album='{found_album}', Track Section ID={track_section_id}, Expected Section ID={library_section_id}", "DEBUG")
                
                if track_id and found_title and found_artist:
                    # Check for section ID mismatch
                    if track_section_id and str(track_section_id) != str(library_section_id):
                        debug_log(f"Plex: Mismatched section ID for track '{found_title}' by '{found_artist}'. Track section: {track_section_id}, Expected: {library_section_id}", "DEBUG")
                        continue  # Skip this track due to section mismatch
                    
                    # Check for title/artist match
                    if found_title.lower() == title.lower() and found_artist.lower() == artist.lower():
                        debug_log(f"Plex: Found exact match: '{found_title}' by '{found_artist}' (ID: {track_id})", "DEBUG")
                        return {'id': track_id, 'title': found_title, 'artist': found_artist, 'album': found_album, 'source': 'plex'}
            
            debug_log(f"Plex: No exact match found for '{title}' by '{artist}' in results.", "DEBUG")
        else:
            debug_log(f"Plex: Track '{title}' by '{artist}' not found or no metadata in section {library_section_id}.", "DEBUG")
        return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code != 404: # Don't log 404 as error here
             debug_log(f"Plex: HTTP error searching: {e}. Response: {e.response.text[:200]}", "WARN")
    except requests.exceptions.RequestException as e:
        debug_log(f"Plex: Request error searching: {e}", "WARN")
    except json.JSONDecodeError as e:
        debug_log(f"Plex: JSON decode error searching. Response: {response.text[:200] if 'response' in locals() else 'N/A'}", "WARN")
    return None

def create_playlist_in_plex(playlist_name, track_ids, plex_server_url, plex_token, plex_machine_id):
    if not all([plex_server_url, plex_token, plex_machine_id]):
        debug_log("Plex server URL, token, or machine ID missing. Cannot create playlist.", "ERROR", True)
        return None, 0
    if not track_ids:
        debug_log("No track IDs provided for Plex playlist creation.", "WARN", True)
        return None, 0

    headers = {'X-Plex-Token': plex_token, 'Accept': 'application/json'}
    first_track_id = track_ids[0]
    
    create_playlist_url = f"{plex_server_url.rstrip('/')}/playlists"
    # URI for the item to create the playlist from (first track)
    # Format: server://{machine_id}/com.plexapp.plugins.library/library/metadata/{item_rating_key}
    source_item_uri = f"server://{plex_machine_id}/com.plexapp.plugins.library/library/metadata/{first_track_id}"
    
    create_params = {
        'X-Plex-Token': plex_token, 'title': playlist_name, 'smart': '0', 'type': 'audio',
        'uri': source_item_uri
    }
    
    playlist_rating_key = None
    created_tracks_count = 0

    debug_log(f"Plex: Attempting to create playlist '{playlist_name}' with first track ID: {first_track_id} (URI: {source_item_uri})", "INFO", True)
    # debug_log(f"Plex Create URL: {create_playlist_url}, Params: { {k:v for k,v in create_params.items() if k != 'X-Plex-Token'} }", "DEBUG")

    try:
        response = requests.post(create_playlist_url, headers=headers, params=create_params, timeout=30)
        # debug_log(f"Plex Create POST Status: {response.status_code}, Headers: {response.headers}", "DEBUG", True)
        # response_text_snippet = response.text[:1000] if response.text else "Empty"
        # debug_log(f"Plex Create POST Response Text (first 1000 chars): {response_text_snippet}", "DEBUG", True)
        response.raise_for_status() 
        
        created_playlist_data = response.json()
        if created_playlist_data.get('MediaContainer', {}).get('Metadata'):
            playlist_metadata = created_playlist_data['MediaContainer']['Metadata'][0]
            playlist_rating_key = playlist_metadata.get('ratingKey')
            created_tracks_count = int(playlist_metadata.get('leafCount', 0))
            debug_log(f"Plex: Playlist '{playlist_metadata.get('title')}' created. ID: {playlist_rating_key}, Initial items: {created_tracks_count}", "INFO", True)
        else:
            debug_log(f"Plex: Playlist created but response format unexpected: {json.dumps(created_playlist_data)[:500]}", "WARN", True)
            # Try to find ratingKey if possible, otherwise this will fail.
            # This path implies success (2xx) but unexpected JSON.

        if not playlist_rating_key:
            debug_log(f"Plex: Could not determine playlist ID from POST response.", "ERROR", True)
            return None, 0
        
        # At this point, the playlist is created with the first track.
        # created_tracks_count was set from the POST response (ideally 1).

        additional_track_ids = track_ids[1:]
        if additional_track_ids:
            add_items_url = f"{plex_server_url.rstrip('/')}/playlists/{playlist_rating_key}/items"
            items_uri_list = [f"server://{plex_machine_id}/com.plexapp.plugins.library/library/metadata/{tid}" for tid in additional_track_ids]
            items_uri_param = ",".join(items_uri_list)
            put_params = {'X-Plex-Token': plex_token, 'uri': items_uri_param}
            
            debug_log(f"Plex: Adding {len(additional_track_ids)} additional tracks to playlist ID {playlist_rating_key}.", "INFO", True)

            put_response = requests.put(add_items_url, headers=headers, params=put_params, timeout=60)
            debug_log(f"Plex Add Items PUT Status: {put_response.status_code}", "DEBUG", True)
            put_response.raise_for_status()

            updated_playlist_data = put_response.json()
            # Check the response from the PUT request to confirm tracks were added.
            if updated_playlist_data.get('MediaContainer', {}).get('Metadata'):
                playlist_meta_put = updated_playlist_data['MediaContainer']['Metadata'][0]
                # leafCountAdded is the most reliable field if present
                leaf_count_added_str = playlist_meta_put.get('leafCountAdded')
                if leaf_count_added_str is not None:
                    leaf_count_added = int(leaf_count_added_str)
                    # The initial track is already counted in created_tracks_count from POST
                    # So, we add the newly added tracks from PUT.
                    # However, the total count is in 'leafCount' or 'size'.
                    # Let's use the final leafCount from the PUT response directly.
                    final_leaf_count_str = playlist_meta_put.get('leafCount', playlist_meta_put.get('size'))
                    if final_leaf_count_str is not None:
                        final_leaf_count = int(final_leaf_count_str)
                        debug_log(f"Plex: Playlist updated. leafCountAdded: {leaf_count_added}, Final leafCount: {final_leaf_count}", "INFO", True)
                        created_tracks_count = final_leaf_count # This is the total number of tracks in the playlist
                    else:
                        # If leafCount is not available, but leafCountAdded is, it implies an issue or partial success.
                        # We can be conservative or try to infer. For now, let's assume the reported added count is on top of the first one.
                        debug_log(f"Plex: PUT successful, leafCountAdded: {leaf_count_added}, but final leafCount missing. Assuming initial + added.", "WARN")
                        created_tracks_count = created_tracks_count + leaf_count_added # created_tracks_count is 1 from POST
                else:
                    # If 'leafCountAdded' is not present, try to use 'leafCount' or 'size' from PUT response
                    final_leaf_count_str = playlist_meta_put.get('leafCount', playlist_meta_put.get('size'))
                    if final_leaf_count_str is not None:
                        final_leaf_count = int(final_leaf_count_str)
                        debug_log(f"Plex: Playlist updated. Final leafCount (from PUT JSON): {final_leaf_count}. leafCountAdded was missing.", "INFO", True)
                        created_tracks_count = final_leaf_count
                    else:
                        debug_log(f"Plex: Add items PUT successful (status {put_response.status_code}), but response format for counts unexpected. Current count: {created_tracks_count}", "WARN")
                        # created_tracks_count remains as it was from the POST (likely 1), as we can't confirm more were added from PUT response.
            else:
                debug_log(f"Plex: Add items PUT successful (status {put_response.status_code}), but MediaContainer or Metadata missing in response. Count remains {created_tracks_count}.", "WARN")
                # created_tracks_count remains as it was from the POST (likely 1)
        
        if created_tracks_count != len(track_ids):
             debug_log(f"Plex: Playlist item count mismatch. Expected {len(track_ids)}, got {created_tracks_count}. Check Plex server.", "WARN")
        else:
             debug_log(f"Plex: Playlist successfully created/updated with {created_tracks_count} tracks.", "INFO", True)

        return playlist_rating_key, created_tracks_count

    except requests.exceptions.HTTPError as e:
        error_details = e.response.text[:500] if e.response else "No response body"
        debug_log(f"Plex: HTTP error during playlist operation for '{playlist_name}': {e}. Status: {e.response.status_code if e.response else 'N/A'}. Details: {error_details}", "ERROR", True)
        return None, 0
    except requests.exceptions.RequestException as e:
        debug_log(f"Plex: Request error during playlist operation for '{playlist_name}': {e}", "ERROR", True)
        return None, 0
    except json.JSONDecodeError as e:
        resp_text = "N/A"
        if 'response' in locals() and response: resp_text = response.text[:200]
        elif 'put_response' in locals() and put_response: resp_text = put_response.text[:200]
        debug_log(f"Plex: JSON decode error during playlist op for '{playlist_name}': {e}. Response: {resp_text}", "ERROR", True)
        return None, 0
    except Exception as e:
        debug_log(f"Plex: Unexpected error during playlist op for '{playlist_name}': {e}", "ERROR", True)
        return None, 0

def search_tracks_in_plex(plex_url, plex_token, ollama_suggested_tracks, final_unique_matched_tracks_map, library_section_id):
    newly_matched_for_batch = []
    if not all([plex_url, plex_token, library_section_id]):
        debug_log("Plex credentials/URL/SectionID missing, skipping Plex search batch.", "WARN")
        return newly_matched_for_batch

    for suggested_track in ollama_suggested_tracks:
        title, artist, album = suggested_track.get("title"), suggested_track.get("artist"), suggested_track.get("album", "Unknown Album")
        if not title or not artist: continue

        track_key = (title.lower(), artist.lower())
        if track_key in final_unique_matched_tracks_map: continue

        # Try multiple search strategies for better matching
        search_strategies = [
            (title, artist, album),  # Full info (most accurate)
            (title, artist, None),  # No album
            (title, None, None),  # Title only
            (None, artist, None),  # Artist only
        ]
        
        found_plex_track = None
        used_strategy = None
        
        for search_title, search_artist, search_album in search_strategies:
            if not search_title and not search_artist: continue
            try:
                found_plex_track = search_track_in_plex(plex_url, plex_token, search_title or '', search_artist or '', search_album, library_section_id)
                if found_plex_track:
                    used_strategy = f"Title: {search_title or 'N/A'}, Artist: {search_artist or 'N/A'}"
                    debug_log(f"Plex: Found match using strategy: {used_strategy}", 'DEBUG')
                    break
            except Exception as e:
                debug_log(f"Plex search strategy failed: {e}", 'WARN')
                continue
        
        if found_plex_track:
            match_details = {
                'id': found_plex_track['id'], 'title': found_plex_track['title'], 'artist': found_plex_track['artist'],
                'album': found_plex_track['album'], 'source': 'plex',
                'original_suggestion': {'title': title, 'artist': artist, 'album': album},
                'search_strategy': used_strategy
            }
            final_unique_matched_tracks_map[track_key] = match_details
            newly_matched_for_batch.append(match_details)
            debug_log(f"Plex: Matched '{found_plex_track['title']}' by '{found_plex_track['artist']}' for suggestion '{title}' by '{artist}' using strategy: {used_strategy}.", "INFO")
        # else:
            # debug_log(f"Plex: No match for '{title}' by '{artist}' (Album: '{album}') in section {library_section_id}.", "DEBUG")
            
    return newly_matched_for_batch

def test_plex_connection(plex_url, plex_token):
    result = {'success': False, 'error': None, 'message': 'Test not fully executed.', 'details': {}, 'server_info': None}
    if not all([plex_url, plex_token]):
        result['error'] = "Plex Server URL or Token missing."
        result['message'] = "Plex Server URL and Token are required."
        return result

    base_url = plex_url.rstrip('/')
    identity_url = f"{base_url}/identity"
    result['details']['attempted_url'] = identity_url

    headers = {'X-Plex-Token': plex_token, 'Accept': 'application/json'}
    response = None  # Initialize response variable
    
    try:
        response = requests.get(identity_url, headers=headers, timeout=10)
        result['details']['status_code'] = response.status_code
        
        try:
            result['details']['response_snippet'] = response.text[:500]
        except Exception:
            result['details']['response_snippet'] = "Could not retrieve response text."

        if response.status_code == 200:
            data = response.json()
            mc = data.get('MediaContainer', {})
            server_info_data = {
                'friendlyName': mc.get('friendlyName'),
                'machineIdentifier': mc.get('machineIdentifier'),
                'version': mc.get('version'),
                'platform': mc.get('platform'),
                'platformVersion': mc.get('platformVersion'),
            }
            result['server_info'] = server_info_data
            
            if mc.get('machineIdentifier'):
                 result['success'] = True
                 result['message'] = f"Successfully connected to Plex server: {server_info_data.get('friendlyName', 'Unknown Name')} (Version: {server_info_data.get('version', 'Unknown')})"
            else:
                result['error'] = "Connected, but couldn't retrieve essential server identity (e.g., Machine ID)."
                result['message'] = "Connection attempt returned 200 OK, but the response format was unexpected for server identity."

        elif response.status_code == 401:
            result['error'] = "Plex connection failed: Unauthorized (401). Check your Plex Token."
            result['message'] = "Authentication failed. Please verify your Plex token."
        else:
            response.raise_for_status()

    except requests.exceptions.HTTPError as e:
        result['error'] = f"Plex connection failed: HTTP Error {e.response.status_code if e.response else 'Unknown'} when accessing {identity_url}."
        result['message'] = f"Server returned an HTTP error: {e.response.status_code if e.response else 'Unknown'}."
        if e.response and e.response.text:
             result['details']['response_snippet'] = e.response.text[:500]
    except requests.exceptions.ConnectionError:
        result['error'] = f"Plex connection failed: Could not connect to server at {plex_url} (tried {identity_url})."
        result['message'] = "Unable to establish a connection with the Plex server. Check the URL and network."
    except requests.exceptions.Timeout:
        result['error'] = f"Plex connection failed: Connection timed out when accessing {identity_url}."
        result['message'] = "The connection to the Plex server timed out."
    except json.JSONDecodeError:
        result['error'] = f"Plex connection failed: Could not parse JSON response from {identity_url}."
        result['message'] = "Received an invalid JSON response from the server."
        if response and response.text: # response_snippet might already be set
             result['details']['response_snippet'] = response.text[:500]
    except requests.exceptions.RequestException as e:
        result['error'] = f"Plex connection failed: A request error occurred - {str(e)}."
        result['message'] = f"An unexpected error occurred during the request: {str(e)}."
    except Exception as e:
        result['error'] = f"An unexpected error occurred: {str(e)}"
        result['message'] = "An unexpected error occurred during the Plex connection test."
        debug_log(f"Unexpected error in test_plex_connection: {e}", "ERROR", True)

    return result

# --- Flask Routes ---
@main_bp.route('/')
def index():
    debug_log("Index page requested", "INFO")
    return render_template('index.html')

@main_bp.route('/', methods=['POST'])
def index_post():
    """Handle form submissions that somehow bypass JavaScript"""
    debug_log(f"Form submitted to index route via POST: {request.form}", "WARN")
    debug_log(f"Request headers: {dict(request.headers)}", "DEBUG")
    return jsonify({"error": "Form submission should be handled by JavaScript API"}), 400

@main_bp.route('/', methods=['GET'])
def index_get():
    """Handle GET requests to index page"""
    if request.args:
        debug_log(f"GET request to index with query parameters: {dict(request.args)}", "WARN")
        debug_log(f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}", "DEBUG")
        debug_log(f"Referer: {request.headers.get('Referer', 'None')}", "DEBUG")
    return render_template('index.html')

@main_bp.route('/history')
def history():
    playlist_history = load_playlist_history()
    # Sort by timestamp descending so newest appear first (top-left in grid)
    def _parse_ts(item):
        try:
            ts = item.get('timestamp')
            return datetime.fromisoformat(ts) if ts else datetime.min
        except Exception:
            return datetime.min
    playlist_history.sort(key=_parse_ts, reverse=True)
    return render_template('history.html', history=playlist_history)

@main_bp.route('/api/history/delete', methods=['POST'])
def api_delete_playlist():
    """Delete a playlist from history"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'})
        
        playlist_index = data.get('playlist_index')
        playlist_id = data.get('playlist_id')
        
        if playlist_index is None:
            return jsonify({'success': False, 'error': 'Playlist index not provided'})
        
        # Load current history
        history = load_playlist_history()
        
        if playlist_index < 0 or playlist_index >= len(history):
            return jsonify({'success': False, 'error': 'Invalid playlist index'})
        
        # Remove the playlist
        deleted_playlist = history.pop(playlist_index)
        debug_log(f"Deleted playlist: {deleted_playlist.get('name', 'Unknown')} (ID: {playlist_id})", 'INFO')
        
        # Save updated history
        save_playlist_history(history)
        
        return jsonify({
            'success': True, 
            'message': f'Playlist "{deleted_playlist.get("name", "Unknown")}" deleted successfully',
            'deleted_index': playlist_index
        })
        
    except Exception as e:
        debug_log(f"Error deleting playlist: {e}", 'ERROR')
        return jsonify({'success': False, 'error': str(e)})

@main_bp.route('/new-generator', methods=['GET', 'POST'])
def new_generator():
    if request.method == 'GET':
        # Ensure database indexes exist for optimal performance
        try:
            from sonic_similarity import ensure_database_indexes
            db_path = os.path.join(DB_DIR, 'local_music.db')
            ensure_database_indexes(db_path)
        except Exception as e:
            debug_log(f"Failed to ensure database indexes: {e}", 'WARN')
        
        return render_template('sonic_traveller.html')

    data = request.get_json() or {}
    seed_track = (data.get('seed_track') or '').strip()
    seed_track_id = data.get('seed_track_id')
    num_songs = int(data.get('num_songs', 20))
    try:
        threshold = float(data.get('threshold', 0.35))
    except Exception:
        threshold = 0.35
    ollama_model = get_config_value('OLLAMA', 'Model', 'llama3')

    if not (seed_track or seed_track_id):
        return jsonify({'error': 'Seed track or seed_track_id is required'}), 400

    # If an id is provided, try to resolve title/artist from local DB for better prompting
    if seed_track_id and not seed_track:
        resolved = _get_track_by_id(seed_track_id)
        if resolved:
            seed_track = f"{(resolved.get('title') or '').strip()} - {(resolved.get('artist') or '').strip()}".strip(' -')

    ollama_url = get_config_value('OLLAMA', 'URL')
    if not ollama_url:
        return jsonify({'error': 'Ollama URL not configured in settings'}), 400

    # Request candidates from Ollama (2x desired for filtering)
    prompt = f"List {num_songs * 2} songs similar in vibe to: {seed_track}. Return Title and Artist."
    candidates = generate_tracks_with_ollama(ollama_url, ollama_model, prompt, num_songs * 2, 0, []) or []

    # Map candidates to local tracks and keep only those with features (Phase 2)
    mapped_with_features = _map_candidates_to_local_with_features(candidates)

    # Distance scoring (normalized) against seed (if seed features available); otherwise, return mapped as-is
    db_path = os.path.join(DB_DIR, 'local_music.db')
    try:
        from feature_store import fetch_track_features, fetch_batch_features
        from sonic_similarity import get_feature_stats, build_vector, compute_distance
        seed_features = None
        if seed_track_id:
            seed_features = fetch_track_features(db_path, int(seed_track_id))
        # If no seed id, try to find the seed via exact title-artist in DB
        if not seed_features and seed_track:
            # resolve seed to id
            conn = sqlite3.connect(db_path)
            try:
                parts = seed_track.split('-')
                stitle = (parts[0] if parts else '').strip()
                sartist = (parts[1] if len(parts) > 1 else '').strip()
                if stitle and sartist:
                    cur = conn.cursor()
                    cur.execute('SELECT id FROM tracks WHERE lower(title)=? AND lower(artist)=? LIMIT 1', (stitle.lower(), sartist.lower()))
                    r = cur.fetchone()
                    if r:
                        seed_features = fetch_track_features(db_path, int(r[0]))
            finally:
                conn.close()

        if seed_features:
            stats = get_feature_stats(db_path)
            seed_vec = build_vector(seed_features, stats)
            # fetch candidate features in batch
            track_ids = [r['id'] for r in mapped_with_features]
            feat_map = fetch_batch_features(db_path, track_ids)
            # compute distances
            scored = []
            for r in mapped_with_features:
                f = feat_map.get(r['id'])
                if not f:
                    continue
                cand_vec = build_vector(f, stats)
                dist = compute_distance(seed_vec, cand_vec)
                scored.append((dist, r))
            scored.sort(key=lambda x: x[0])
            picked = [dict(id=r['id'], title=r['title'], artist=r['artist'], album=r['album'], distance=round(d, 3)) for d, r in scored[:num_songs]]
        else:
            picked = [dict(id=r['id'], title=r['title'], artist=r['artist'], album=r['album']) for r in mapped_with_features[:num_songs]]

        return jsonify({
            'message': 'Sonic Traveller results',
            'tracks': picked,
            'count': len(picked),
            'total_candidates': len(candidates),
            'used_distance': bool(seed_features)
        }), 200
    except Exception as e:
        debug_log(f"Sonic Traveller distance scoring error: {e}", 'ERROR')
        # Fallback to mapped list
        results = [dict(id=r['id'], title=r['title'], artist=r['artist'], album=r['album']) for r in mapped_with_features[:num_songs]]
        return jsonify({'message': 'Sonic Traveller (fallback)', 'tracks': results, 'count': len(results)}), 200

def _map_candidates_to_local_with_features(candidates):
    """Return a list of local track dicts (id,title,artist,album) that match candidates and have features."""
    db_path = os.path.join(DB_DIR, 'local_music.db')
    if not os.path.exists(db_path):
        return []

    # Build normalized candidate keys
    def _norm(s):
        return (s or '').strip()

    unique_pairs = []
    seen = set()
    for tr in candidates:
        title = _norm(tr.get('title'))
        artist = _norm(tr.get('artist'))
        if not title or not artist:
            continue
        key = (title.lower(), artist.lower())
        if key in seen:
            continue
        seen.add(key)
        unique_pairs.append((title, artist))

    if not unique_pairs:
        return []

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    matched_rows = []  # list of dicts with id,title,artist,album

    try:
        # First pass: exact lower(title,artist)
        for title, artist in unique_pairs:
            cursor.execute(
                "SELECT id, title, artist, album FROM tracks WHERE lower(title)=? AND lower(artist)=? LIMIT 1",
                (title.lower(), artist.lower())
            )
            row = cursor.fetchone()
            if row:
                matched_rows.append({'id': row[0], 'title': row[1] or '', 'artist': row[2] or '', 'album': row[3] or ''})

        # Second pass: LIKE for those not matched
        remaining = [(t, a) for (t, a) in unique_pairs if not any((r['title'].lower(), r['artist'].lower()) == (t.lower(), a.lower()) for r in matched_rows)]
        for title, artist in remaining:
            like_title = f"%{title}%"
            like_artist = f"%{artist}%"
            cursor.execute(
                "SELECT id, title, artist, album FROM tracks WHERE title LIKE ? AND artist LIKE ? LIMIT 10",
                (like_title, like_artist)
            )
            candidate_rows = [{'id': r[0], 'title': r[1] or '', 'artist': r[2] or '', 'album': r[3] or ''} for r in cursor.fetchall() or []]
            # crude best: pick first for now; later we could reuse evaluate logic
            if candidate_rows:
                matched_rows.append(candidate_rows[0])

    finally:
        conn.close()

    # Filter by having features
    try:
        from feature_store import fetch_batch_features
        track_ids = [r['id'] for r in matched_rows]
        features_map = fetch_batch_features(db_path, track_ids)
        filtered = [r for r in matched_rows if r['id'] in features_map]
        return filtered
    except Exception:
        # If feature fetch fails, return matched rows without filtering to avoid hard failure
        return matched_rows

@main_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        # This is form data, not JSON
        current_config = load_config() # Load existing to preserve sections/keys not in form
        
        # OLLAMA section
        if not current_config.has_section('OLLAMA'): current_config.add_section('OLLAMA')
        current_config.set('OLLAMA', 'URL', request.form.get('ollama_url', get_config_value('OLLAMA', 'URL', '')))
        current_config.set('OLLAMA', 'Model', request.form.get('ollama_model', get_config_value('OLLAMA', 'Model', '')))
        current_config.set('OLLAMA', 'ContextWindow', request.form.get('context_window', get_config_value('OLLAMA', 'ContextWindow', '2048')))
        current_config.set('OLLAMA', 'MaxAttempts', request.form.get('max_attempts', get_config_value('OLLAMA', 'MaxAttempts', '10')))
        current_config.set('OLLAMA', 'Temperature', request.form.get('ollama_temperature', get_config_value('OLLAMA', 'Temperature', '0.7')))
        current_config.set('OLLAMA', 'TopP', request.form.get('ollama_top_p', get_config_value('OLLAMA', 'TopP', '0.9')))
        current_config.set('OLLAMA', 'DebugOllamaResponse', request.form.get('debug_ollama_response', get_config_value('OLLAMA', 'DebugOllamaResponse', 'no')))


        # APP section
        if not current_config.has_section('APP'): current_config.add_section('APP')
        current_config.set('APP', 'Likes', request.form.get('likes', get_config_value('APP', 'Likes', '')))
        current_config.set('APP', 'Dislikes', request.form.get('dislikes', get_config_value('APP', 'Dislikes', '')))
        current_config.set('APP', 'FavoriteArtists', request.form.get('favorite_artists', get_config_value('APP', 'FavoriteArtists', '')))
        current_config.set('APP', 'EnableNavidrome', request.form.get('enable_navidrome', get_config_value('APP', 'EnableNavidrome', 'no')))
        current_config.set('APP', 'EnablePlex', request.form.get('enable_plex', get_config_value('APP', 'EnablePlex', 'no')))
        current_config.set('APP', 'Debug', request.form.get('app_debug_mode', get_config_value('APP', 'Debug', 'yes'))) # Ensure this matches the form field name
        current_config.set('APP', 'VerboseLogging', request.form.get('verbose_logging', get_config_value('APP', 'VerboseLogging', 'no')))
        current_config.set('APP', 'UseLocalMatching', 'yes' if request.form.get('use_local_matching') else 'no')
        current_config.set('APP', 'LocalMusicFolder', request.form.get('local_music_folder', get_config_value('APP', 'LocalMusicFolder', '')))


        # NAVIDROME section
        if not current_config.has_section('NAVIDROME'): current_config.add_section('NAVIDROME')
        current_config.set('NAVIDROME', 'URL', request.form.get('navidrome_url', get_config_value('NAVIDROME', 'URL', '')))
        current_config.set('NAVIDROME', 'Username', request.form.get('navidrome_username', get_config_value('NAVIDROME', 'Username', '')))
        current_config.set('NAVIDROME', 'Password', request.form.get('navidrome_password', get_config_value('NAVIDROME', 'Password', '')))
        
        # PLEX section
        if not current_config.has_section('PLEX'): current_config.add_section('PLEX')
        current_config.set('PLEX', 'ServerURL', request.form.get('plex_server_url', get_config_value('PLEX', 'ServerURL', '')))
        current_config.set('PLEX', 'Token', request.form.get('plex_token', get_config_value('PLEX', 'Token', '')))
        current_config.set('PLEX', 'MachineID', request.form.get('plex_machine_id', get_config_value('PLEX', 'MachineID', '')))
        current_config.set('PLEX', 'MusicSectionID', request.form.get('plex_music_section_id', get_config_value('PLEX', 'MusicSectionID', '')))
        current_config.set('PLEX', 'PlaylistType', request.form.get('plex_playlist_type', get_config_value('PLEX', 'PlaylistType', 'audio')))


        with open(CONFIG_FILE, 'w') as configfile:
            current_config.write(configfile)
        # Instead of redirect, return JSON for AJAX handling
        return jsonify({'status': 'success', 'message': 'Settings saved successfully!'})

    # GET request
    context = {
        'ollama_url': get_config_value('OLLAMA', 'URL', 'http://localhost:11434'),
        'ollama_model': get_config_value('OLLAMA', 'Model', 'llama3'),
        'context_window': get_config_value('OLLAMA', 'ContextWindow', '2048'),
        'max_attempts': get_config_value('OLLAMA', 'MaxAttempts', '10'),
        'ollama_temperature': get_config_value('OLLAMA', 'Temperature', '0.7'),
        'ollama_top_p': get_config_value('OLLAMA', 'TopP', '0.9'),
        'debug_ollama_response': get_config_value('OLLAMA', 'DebugOllamaResponse', 'no'),

        'likes': get_config_value('APP', 'Likes', ''),
        'dislikes': get_config_value('APP', 'Dislikes', ''),
        'favorite_artists': get_config_value('APP', 'FavoriteArtists', ''),
        'enable_navidrome': get_config_value('APP', 'EnableNavidrome', 'no'),
        'enable_plex': get_config_value('APP', 'EnablePlex', 'no'),
        'app_debug_mode': get_config_value('APP', 'Debug', 'yes'), # Ensure this matches the form field name and context variable
        'verbose_logging': get_config_value('APP', 'VerboseLogging', 'no'),
        'use_local_matching': get_config_value('APP', 'UseLocalMatching', 'no'),
        'local_music_folder': get_config_value('APP', 'LocalMusicFolder', ''),

        'navidrome_url': get_config_value('NAVIDROME', 'URL', ''),
        'navidrome_username': get_config_value('NAVIDROME', 'Username', ''),
        'navidrome_password': get_config_value('NAVIDROME', 'Password', ''),
        
        'plex_server_url': get_config_value('PLEX', 'ServerURL', ''),
        'plex_token': get_config_value('PLEX', 'Token', ''),
        'plex_machine_id': get_config_value('PLEX', 'MachineID', ''),
        'plex_playlist_type': get_config_value('PLEX', 'PlaylistType', 'audio'), 
        'plex_music_section_id': get_config_value('PLEX', 'MusicSectionID', '')
    }
    
    # Add local music statistics
    try:
        local_stats = get_local_track_stats()
        context['local_stats'] = local_stats
    except Exception as e:
        debug_log(f"Error getting local music stats for settings: {e}", "WARN")
        context['local_stats'] = None
    
    return render_template('settings.html', **context)

@main_bp.route('/test-navidrome') # Renders the test page
def test_navidrome_page():
    return render_template('test_navidrome.html')

@main_bp.route('/api/test-navidrome-connection', methods=['POST']) # API endpoint for testing
def api_test_navidrome_connection():
    data = request.get_json() # Use get_json() for better error handling
    if not data:
        return jsonify({"error": "Invalid or missing JSON payload"}), 400
    navidrome_url = data.get('navidrome_url')
    username = data.get('username')
    password = data.get('password')
    result = test_navidrome_connection(navidrome_url, username, password)
    return jsonify(result)

@main_bp.route('/test-plex') # Renders the Plex test page
def test_plex_page():
    context = {
        'plex_server_url': get_config_value('PLEX', 'ServerURL', ''),
        'plex_token': get_config_value('PLEX', 'Token', ''),
        'plex_music_section_id': get_config_value('PLEX', 'MusicSectionID', '')
    }
    return render_template('test_plex.html', **context)

@main_bp.route('/api/test-plex-connection', methods=['POST']) # API endpoint for testing Plex connection
def api_test_plex_connection():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid or missing JSON payload", "success": False}), 400
    
    plex_server_url = data.get('plex_server_url')
    plex_token = data.get('plex_token')

    if not plex_server_url or not plex_token:
        return jsonify({"error": "Plex Server URL and Token are required in the payload.", "success": False}), 400

    result = test_plex_connection(plex_server_url, plex_token)
    return jsonify(result)

@main_bp.route('/api/generate-playlist', methods=['POST'])
def api_generate_playlist():
    debug_log("Playlist generation API called", "INFO")
    debug_log(f"Request headers: {dict(request.headers)}", "DEBUG")
    
    data = request.get_json() # Use get_json() for better error handling
    if not data:
        debug_log("Invalid or missing JSON payload in playlist generation", "ERROR")
        return jsonify({"error": "Invalid or missing JSON payload"}), 400
        
    prompt = data.get('prompt')
    playlist_name = data.get('playlist_name', 'New TuneForge Playlist')
    num_songs = int(data.get('num_songs', 10))
    services_to_use_req = data.get('services', [])
    services_to_use = [s.lower() for s in services_to_use_req] if services_to_use_req else ['navidrome', 'plex']
    
    max_ollama_attempts = int(get_config_value('OLLAMA', 'MaxAttempts', '3'))
    
    # Generate or accept provided playlist ID for progress tracking
    import uuid
    client_playlist_id = data.get('client_playlist_id')
    playlist_id = client_playlist_id if client_playlist_id else str(uuid.uuid4())
    
    debug_log(f"Generated playlist ID: {playlist_id}", "DEBUG")
    debug_log(f"Playlist generation parameters: prompt='{prompt}', num_songs={num_songs}, playlist_name='{playlist_name}'", "INFO")
    
    # Initialize progress tracking
    if not hasattr(api_generate_playlist, 'playlist_progress'):
        api_generate_playlist.playlist_progress = {}
    
    api_generate_playlist.playlist_progress[playlist_id] = {
        'status': 'starting',
        'current_status': 'Initializing playlist generation...',
        'ollama_calls': 0,
        'tracks_found': 0,
        'target_songs': num_songs,
        'start_time': time.time()
    }

    if not prompt: return jsonify({"error": "Prompt is required"}), 400

    ollama_url = get_config_value('OLLAMA', 'URL')
    ollama_model = get_config_value('OLLAMA', 'Model')
    if not ollama_url or not ollama_model:
        return jsonify({"error": "Ollama URL or Model not configured in settings."}), 400
    
    use_local_matching = get_config_value('APP', 'UseLocalMatching', 'no').lower() in ('yes', 'true', '1')
    enable_navidrome = (not use_local_matching) and ('navidrome' in services_to_use) and get_config_value('APP', 'EnableNavidrome', 'no').lower() in ('yes', 'true', '1')
    enable_plex = (not use_local_matching) and ('plex' in services_to_use) and get_config_value('APP', 'EnablePlex', 'no').lower() in ('yes', 'true', '1')

    navidrome_url, navidrome_user, navidrome_pass = (None,)*3
    if enable_navidrome:
        navidrome_url = get_config_value('NAVIDROME', 'URL')
        navidrome_user = get_config_value('NAVIDROME', 'Username')
        navidrome_pass = get_config_value('NAVIDROME', 'Password')
        if not all([navidrome_url, navidrome_user, navidrome_pass]):
            debug_log("Navidrome enabled but details missing. Disabling for this run.", "WARN", True); enable_navidrome = False

    plex_server_url, plex_token, plex_section_id, plex_machine_id = (None,)*4
    if enable_plex:
        plex_server_url = get_config_value('PLEX', 'ServerURL')
        plex_token = get_config_value('PLEX', 'Token')
        plex_section_id = get_config_value('PLEX', 'MusicSectionID')
        plex_machine_id = get_config_value('PLEX', 'MachineID')
        if not all([plex_server_url, plex_token, plex_section_id, plex_machine_id]):
            debug_log("Plex enabled but critical details missing. Disabling for this run.", "WARN", True); enable_plex = False
    
    if not use_local_matching and not enable_navidrome and not enable_plex:
        return jsonify({"error": "No services (Local/ Navidrome/ Plex) are enabled or properly configured."}), 400

    final_unique_matched_tracks_map = {} # Stores {(title.lower(), artist.lower()): track_details_dict}
    all_ollama_suggestions_raw = [] # Stores all raw track dicts from Ollama for context
    
    ollama_api_calls_made = 0
    
    while len(final_unique_matched_tracks_map) < num_songs and ollama_api_calls_made < max_ollama_attempts:
        tracks_still_needed = num_songs - len(final_unique_matched_tracks_map)
        debug_log(f"Playlist Gen: Attempt {ollama_api_calls_made + 1}/{max_ollama_attempts}. Tracks found: {len(final_unique_matched_tracks_map)}/{num_songs}.", "INFO", True)
        debug_log(f"Playlist Gen: Starting Ollama call {ollama_api_calls_made + 1} to find {tracks_still_needed} more tracks...", "INFO", True)
        
        # Update progress tracking
        api_generate_playlist.playlist_progress[playlist_id].update({
            'ollama_calls': ollama_api_calls_made + 1,
            'tracks_found': len(final_unique_matched_tracks_map),
            'current_status': f'Ollama call {ollama_api_calls_made + 1}: Requesting {tracks_still_needed} more tracks...',
            'current_phase': 'ollama'
        })

        songs_to_request_this_ollama_call = tracks_still_needed * 3 # Request more to account for filtering/matching
        if tracks_still_needed <= 3: songs_to_request_this_ollama_call = tracks_still_needed + 10
        songs_to_request_this_ollama_call = max(10, min(songs_to_request_this_ollama_call, 40)) # Bounds: 10-40

        debug_log(f"Ollama: Requesting {songs_to_request_this_ollama_call} new tracks.", "INFO")
        current_ollama_batch = generate_tracks_with_ollama(
            ollama_url, ollama_model, prompt, songs_to_request_this_ollama_call, 
            ollama_api_calls_made, all_ollama_suggestions_raw
        )
        ollama_api_calls_made += 1

        if not current_ollama_batch:
            debug_log(f"Ollama: Attempt {ollama_api_calls_made} yielded no tracks. {'Retrying...' if ollama_api_calls_made < max_ollama_attempts else 'Max attempts reached.'}", "WARN", True)
            if ollama_api_calls_made < max_ollama_attempts: time.sleep(1); continue
            else: break # Max Ollama attempts reached

        all_ollama_suggestions_raw.extend(current_ollama_batch)
        
        # Pre-filter Ollama suggestions (live, instrumental, already found etc.)
        undesirable_patterns = [ # Regex patterns
            r"\(live\b", r"\[live\b", r"- live\b", r"\blive at\b", r"\blive from\b",
            r"\(instrumental\b", r"\[instrumental\b", r"- instrumental\b",
            r"\(karaoke\b", r"\[karaoke\b", r"- karaoke\b", r"karaoke version\b",
            r"\(cover\b", r"\[cover\b", r"- cover\b", r" tribute\b",
            r"\(remix\b", r"\[remix\b", r"- remix\b",
            r"\(acoustic\b", r"\[acoustic\b", r"- acoustic\b",
            r"\(edit\b", r"\[edit\b", r"- radio edit\b", r"single version\b",
            r"\(demo\b", r"\[demo\b", r"- demo\b", r"\(session\b", r"\[session\b",
        ]
        undesirable_artist_keywords = ["karaoke", "tribute band", "the karaoke crew", "various artists", "soundtrack"]
        
        eligible_tracks_for_search = []
        for track in current_ollama_batch:
            title_l, artist_l, album_l = track.get("title","").lower(), track.get("artist","").lower(), track.get("album","").lower()
            if not title_l or not artist_l: continue
            if (title_l, artist_l) in final_unique_matched_tracks_map: continue # Already found

            is_undesirable = any(re.search(p, title_l) or re.search(p, album_l) for p in undesirable_patterns) or \
                             any(k in artist_l for k in undesirable_artist_keywords)
            if is_undesirable:
                debug_log(f"Filtering out undesirable: '{track.get('title')}' by '{track.get('artist')}' (pattern: {[p for p in undesirable_patterns if re.search(p, title_l or '') or re.search(p, album_l or '')]} artist keywords: {[k for k in undesirable_artist_keywords if k in artist_l]})", "DEBUG")
                continue
            eligible_tracks_for_search.append(track)
        
        debug_log(f"Ollama: {len(eligible_tracks_for_search)} tracks eligible for searching after filtering batch of {len(current_ollama_batch)}.", "INFO")
        debug_log(f"Ollama: Processing {len(eligible_tracks_for_search)} tracks for matching...", "INFO")
        if not eligible_tracks_for_search: continue

        if use_local_matching:
            newly_matched = search_tracks_in_local_library(eligible_tracks_for_search, final_unique_matched_tracks_map)
            api_generate_playlist.playlist_progress[playlist_id].update({
                'tracks_found': len(final_unique_matched_tracks_map),
                'current_status': f'Found {len(newly_matched)} new tracks via Local Library',
                'current_phase': 'local'
            })
            if len(final_unique_matched_tracks_map) >= num_songs: break
        
        if enable_navidrome:
            debug_log(f"Navidrome: Starting search for {len(eligible_tracks_for_search)} eligible tracks", "INFO")
            newly_matched = search_tracks_in_navidrome(navidrome_url, navidrome_user, navidrome_pass, eligible_tracks_for_search, final_unique_matched_tracks_map)
            debug_log(f"Navidrome: Search completed. Found {len(newly_matched)} new matches", "INFO")
            
            # Update progress after Navidrome search
            api_generate_playlist.playlist_progress[playlist_id].update({
                'tracks_found': len(final_unique_matched_tracks_map),
                'current_status': f'Found {len(newly_matched)} new tracks via Navidrome',
                'current_phase': 'navidrome'
            })
            
            if len(final_unique_matched_tracks_map) >= num_songs: break
        
        if enable_plex:
            search_tracks_in_plex(plex_server_url, plex_token, eligible_tracks_for_search, final_unique_matched_tracks_map, plex_section_id)
            
            # Update progress after Plex search
            api_generate_playlist.playlist_progress[playlist_id].update({
                'tracks_found': len(final_unique_matched_tracks_map),
                'current_status': f'Found tracks via Plex'
            })
            
            if len(final_unique_matched_tracks_map) >= num_songs: break
        
        if ollama_api_calls_made < max_ollama_attempts and len(final_unique_matched_tracks_map) < num_songs:
            tracks_still_needed = num_songs - len(final_unique_matched_tracks_map)
            debug_log(f"Playlist Gen: Need more tracks. Current: {len(final_unique_matched_tracks_map)}/{num_songs}. Continuing to next Ollama call...", "INFO", True)
            time.sleep(0.5)

    # --- End of main generation loop ---
    final_tracklist_details = list(final_unique_matched_tracks_map.values())

    # Final progress update
    api_generate_playlist.playlist_progress[playlist_id].update({
        'status': 'completed',
        'tracks_found': len(final_tracklist_details),
        'current_status': f'Generation complete! Found {len(final_tracklist_details)}/{num_songs} tracks'
    })

    if not final_tracklist_details:
        msg = f"Could not find any tracks for prompt '{prompt}' after {ollama_api_calls_made} Ollama attempts."
        debug_log(msg, "ERROR", True)
        return jsonify({"message": msg, "playlist_name": playlist_name, "tracks_found": 0, "playlist_id": playlist_id}), 500

    debug_log(f"Playlist Gen: Total {len(final_tracklist_details)} unique tracks found for playlist '{playlist_name}'.", "INFO", True)

    # Cap the number of tracks to the target count when creating playlists
    max_tracks_to_add = min(num_songs, len(final_tracklist_details))
    selected_tracks_for_creation = final_tracklist_details[:max_tracks_to_add]

    created_playlists_summary = {}
    navidrome_ids = [t['id'] for t in selected_tracks_for_creation if t['source'] == 'navidrome']
    plex_ids = [t['id'] for t in selected_tracks_for_creation if t['source'] == 'plex']
    local_ids = [t['id'] for t in selected_tracks_for_creation if t['source'] == 'local']

    if enable_navidrome:
        if navidrome_ids:
            nid = create_playlist_in_navidrome(navidrome_url, navidrome_user, navidrome_pass, playlist_name, navidrome_ids)
            created_playlists_summary['navidrome'] = {'id': nid, 'track_count': len(navidrome_ids) if nid else 0, 'status': 'success' if nid else 'failed'}
        else: created_playlists_summary['navidrome'] = {'id': None, 'track_count': 0, 'status': 'no_tracks'}

    if enable_plex:
        if plex_ids:
            pid, plex_count = create_playlist_in_plex(playlist_name, plex_ids, plex_server_url, plex_token, plex_machine_id)
            created_playlists_summary['plex'] = {'id': pid, 'track_count': plex_count if pid else 0, 'status': 'success' if pid else 'failed'}
        else: created_playlists_summary['plex'] = {'id': None, 'track_count': 0, 'status': 'no_tracks'}

    if use_local_matching:
        created_playlists_summary['local'] = {'id': None, 'track_count': len(local_ids), 'status': 'matched_only'}

    history = load_playlist_history()
    history.append({
        "name": playlist_name, "prompt": prompt, "num_songs_requested": num_songs,
        "num_songs_added_total": len(selected_tracks_for_creation),
        "services_targeted": services_to_use, "creation_results": created_playlists_summary,
        "tracks_details": selected_tracks_for_creation, "timestamp": datetime.now().isoformat()
    })
    save_playlist_history(history)

    return jsonify({
        "message": f"Playlist '{playlist_name}' generation complete. Found {len(final_tracklist_details)}/{num_songs} tracks.",
        "playlist_name": playlist_name, "tracks_added_count": len(selected_tracks_for_creation),
        "target_song_count": num_songs, "created_in_services": created_playlists_summary,
        "ollama_api_calls": ollama_api_calls_made, "playlist_id": playlist_id
    }), 200

@main_bp.route('/api/config', methods=['GET', 'POST'])
def api_config():
    if request.method == 'POST':
        data = request.get_json() # Use get_json() for better error handling
        if not data:
            return jsonify({"error": "Invalid or missing JSON payload"}), 400
        try:
            save_config(data) # data is expected to be a dict of dicts like {section: {key: value}}
            return jsonify({"message": "Configuration saved successfully"}), 200
        except Exception as e:
            debug_log(f"Error saving configuration via API: {e}", "ERROR", True)
            return jsonify({"error": f"Failed to save configuration: {str(e)}"}), 500
    else: # GET
        config_parser = load_config()
        config_data_to_send = {section: dict(config_parser.items(section)) for section in config_parser.sections()}
        return jsonify(config_data_to_send)

@main_bp.route('/api/history', methods=['GET'])
def api_history():
    history = load_playlist_history()
    return jsonify(history)

@main_bp.route('/api/plex_fetch_libraries', methods=['GET'])
def plex_fetch_libraries_route():
    plex_url = get_config_value('PLEX', 'ServerURL')
    plex_token = get_config_value('PLEX', 'Token')
    if not plex_url or not plex_token:
        return jsonify({"error": "Plex ServerURL or Token not configured."}), 400

    try:
        headers = {'X-Plex-Token': plex_token, 'Accept': 'application/json'}
        response = requests.get(f"{plex_url.rstrip('/')}/library/sections", headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        libraries = []
        if data.get('MediaContainer', {}).get('Directory'):
            for lib in data['MediaContainer']['Directory']:
                if lib.get('type') == 'artist': # Music libraries
                    libraries.append({'id': lib.get('key'), 'name': lib.get('title'), 'type': lib.get('type')})
        return jsonify(libraries)
    except requests.exceptions.Timeout:
        return jsonify({"error": "Timeout connecting to Plex server."}), 504
    except requests.exceptions.RequestException as e:
        err_msg = str(e)
        status = e.response.status_code if e.response is not None else 500
        try: 
            if e.response is not None: # Ensure response object exists
                err_msg = e.response.json().get('errors',[{}])[0].get('message', str(e))
        except: pass # Keep original if parsing fails
        debug_log(f"Error fetching Plex libraries: {err_msg}", "ERROR")
        return jsonify({"error": f"Failed to fetch Plex libraries: {err_msg}"}), status
    except Exception as e: # Catch-all for other errors like JSONDecodeError if not caught by RequestException
        debug_log(f"Unexpected error fetching Plex libraries: {e}", "ERROR")
        return jsonify({"error": "An unexpected error occurred."}), 500


@main_bp.route('/api/plex_fetch_machine_id', methods=['GET'])
def plex_fetch_machine_id_route():
    plex_url = get_config_value('PLEX', 'ServerURL')
    plex_token = get_config_value('PLEX', 'Token')
    if not plex_url or not plex_token:
        return jsonify({"error": "Plex ServerURL or Token not configured."}), 400

    try:
        headers = {'X-Plex-Token': plex_token, 'Accept': 'application/json'}
        # Try /identity first, then fallback to /
        for endpoint in ['/identity', '/']:
            response = requests.get(f"{plex_url.rstrip('/')}{endpoint}", headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            machine_id = data.get('MediaContainer', {}).get('machineIdentifier')
            if machine_id:
                return jsonify({"machine_identifier": machine_id})
        
        return jsonify({"error": "Could not determine Plex Machine Identifier from / or /identity."}), 404

    except requests.exceptions.Timeout:
        return jsonify({"error": "Timeout connecting to Plex server for machine ID."}), 504
    except requests.exceptions.RequestException as e:
        err_msg = str(e)
        status = e.response.status_code if e.response is not None else 500
        try: 
            if e.response is not None: # Ensure response object exists
                err_msg = e.response.json().get('errors',[{}])[0].get('message', str(e))
        except: pass
        debug_log(f"Error fetching Plex machine ID: {err_msg}", "ERROR")
        return jsonify({"error": f"Failed to fetch Plex machine ID: {err_msg}"}), status
    except Exception as e:
        debug_log(f"Unexpected error fetching Plex machine ID: {e}", "ERROR")
        return jsonify({"error": "An unexpected error occurred."}), 500

@main_bp.route('/api/logs/stream')
def api_logs_stream():
    """Stream logs in real-time for the frontend"""
    def generate():
        log_file = os.path.join(LOG_DIR, 'tuneforge_app.log')
        verbose_logging = get_config_value('APP', 'VerboseLogging', 'no').lower() == 'yes'
        
        # Send initial message
        yield f"data: {json.dumps({'type': 'info', 'message': 'Starting log stream for current session...'})}\n\n"
        
        # Get current file size to only show NEW logs from this point forward
        initial_size = os.path.exists(log_file) and os.path.getsize(log_file) or 0
        
        # Now monitor for new logs only
        yield f"data: {json.dumps({'type': 'info', 'message': 'Monitoring for new logs...'})}\n\n"
        
        # Monitor indefinitely until the connection is closed or an error occurs
        while True:
            try:
                if os.path.exists(log_file):
                    current_size = os.path.getsize(log_file)
                    if current_size > initial_size:
                        # New content added
                        with open(log_file, 'r', encoding='utf-8') as file:
                            file.seek(initial_size)
                            new_content = file.read()
                            for line in new_content.splitlines():
                                if line.strip():
                                    # Determine what to show based on verbose setting
                                    should_show = False
                                    
                                    if verbose_logging:
                                        # Verbose mode: show all detailed logs
                                        should_show = any(keyword in line for keyword in [
                                            'Playlist Gen:',  # Playlist generation progress
                                            'Ollama: Requesting',  # New Ollama requests
                                            'Ollama: Successfully parsed',  # Track parsing results
                                            'Navidrome: Searching for',  # Track search attempts
                                            'Navidrome: ✅ EXCELLENT MATCH',  # Excellent matches
                                            'Navidrome: ✅ GOOD MATCH',  # Good matches
                                            'Navidrome: ⚠️ ACCEPTABLE MATCH',  # Acceptable matches
                                            'Navidrome: 🎯 New best match',  # Best match updates
                                            'Navidrome: Evaluating',  # Track evaluation
                                            'Navidrome: ❌ No suitable match',  # No matches found
                                            'Navidrome: Creating/updating playlist',  # Playlist creation
                                            'Navidrome: Successfully created/updated playlist'  # Completion
                                        ])
                                    else:
                                        # Basic mode: only show live playlist additions
                                        should_show = any(keyword in line for keyword in [
                                            'Playlist Gen:',  # Playlist generation progress
                                            'Navidrome: ✅ EXCELLENT MATCH',  # Excellent matches
                                            'Navidrome: ✅ GOOD MATCH',  # Good matches
                                            'Navidrome: ⚠️ ACCEPTABLE MATCH',  # Acceptable matches
                                            'Navidrome: Creating/updating playlist',  # Playlist creation
                                            'Navidrome: Successfully created/updated playlist'  # Completion
                                        ])
                                    
                                    if should_show:
                                        yield f"data: {json.dumps({'type': 'log', 'message': line.strip()})}\n\n"
                        
                        initial_size = current_size
                
                # Use a shorter sleep to be more responsive
                time.sleep(0.5)
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Error reading logs: {str(e)}'})}\n\n"
                break
        
        yield f"data: {json.dumps({'type': 'complete', 'message': 'Log stream complete'})}\n\n"
    
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

# --- Local Music Management ---
def init_local_music_db():
    """Initialize the local music database"""
    db_path = os.path.join(DB_DIR, 'local_music.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE NOT NULL,
            title TEXT,
            artist TEXT,
            album TEXT,
            genre TEXT,
            year INTEGER,
            track_number INTEGER,
            duration REAL,
            file_size INTEGER,
            last_modified REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_title ON tracks(title)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_artist ON tracks(artist)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_album ON tracks(album)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_genre ON tracks(genre)')
    
    conn.commit()
    conn.close()
    return db_path

def scan_music_folder(folder_path):
    """Scan a music folder and index all tracks"""
    if not os.path.exists(folder_path):
        return {'success': False, 'error': 'Folder does not exist'}
    
    supported_extensions = {'.mp3', '.flac', '.m4a', '.ogg', '.wav', '.aac'}
    db_path = init_local_music_db()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    stats = {'total_files': 0, 'indexed': 0, 'errors': 0, 'skipped': 0}
    
    try:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower()
                
                if file_ext not in supported_extensions:
                    stats['skipped'] += 1
                    continue
                
                stats['total_files'] += 1
                
                try:
                    # Extract metadata using mutagen
                    metadata = extract_track_metadata(file_path)
                    if metadata:
                        # Check if track already exists
                        cursor.execute('SELECT id FROM tracks WHERE file_path = ?', (file_path,))
                        existing = cursor.fetchone()
                        
                        if existing:
                            # Update existing track
                            cursor.execute('''
                                UPDATE tracks SET 
                                    title = ?, artist = ?, album = ?, genre = ?, 
                                    year = ?, track_number, duration = ?, 
                                    file_size = ?, last_modified = ?
                                WHERE file_path = ?
                            ''', (
                                metadata.get('title'), metadata.get('artist'), metadata.get('album'),
                                metadata.get('genre'), metadata.get('year'), metadata.get('track_number'),
                                metadata.get('duration'), metadata.get('file_size'), metadata.get('last_modified'),
                                file_path
                            ))
                        else:
                            # Insert new track
                            cursor.execute('''
                                INSERT INTO tracks (file_path, title, artist, album, genre, 
                                                  year, track_number, duration, file_size, last_modified)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                file_path, metadata.get('title'), metadata.get('artist'), metadata.get('album'),
                                metadata.get('genre'), metadata.get('year'), metadata.get('track_number'),
                                metadata.get('duration'), metadata.get('file_size'), metadata.get('last_modified')
                            ))
                        
                        stats['indexed'] += 1
                    else:
                        stats['errors'] += 1
                        
                except Exception as e:
                    debug_log(f"Error indexing {file_path}: {str(e)}", "ERROR")
                    stats['errors'] += 1
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'stats': stats}
        
    except Exception as e:
        conn.close()
        return {'success': False, 'error': str(e)}

def scan_music_folder_with_progress(folder_path, scan_id):
    """Scan a music folder with progress tracking"""
    if not os.path.exists(folder_path):
        return {'success': False, 'error': 'Folder does not exist'}
    
    # Get the progress tracker
    progress_tracker = api_scan_music_folder.scan_progress.get(scan_id)
    if not progress_tracker:
        return {'success': False, 'error': 'Progress tracker not found'}
    
    supported_extensions = {'.mp3', '.flac', '.m4a', '.ogg', '.wav', '.aac'}
    db_path = init_local_music_db()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    stats = {'total_files': 0, 'indexed': 0, 'errors': 0, 'skipped': 0}
    
    try:
        # First pass: count total files with live progress updates
        progress_tracker['status'] = 'counting'
        progress_tracker['current_file'] = 'Counting all files...'
        progress_tracker['files_processed'] = 0
        progress_tracker['total_files'] = 0
        
        # Count all files first to get total with live updates
        all_files = 0
        music_files = 0
        files_checked = 0
        
        for root, dirs, files in os.walk(folder_path):
            all_files += len(files)
            for file in files:
                files_checked += 1
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in supported_extensions:
                    music_files += 1
                
                # Update counting progress every 1000 files or every file if < 1000
                if files_checked % max(1, min(1000, max(1, files_checked // 20))) == 0:
                    progress_tracker['files_processed'] = files_checked
                    progress_tracker['current_file'] = f'Counting... {files_checked} files checked, {music_files} music files found'
        
        # Update stats and progress tracker
        stats['total_files'] = music_files
        progress_tracker['total_files'] = music_files
        progress_tracker['current_file'] = f'Found {music_files} music files out of {all_files} total files'
        progress_tracker['files_processed'] = 0  # Reset for scanning phase
        progress_tracker['status'] = 'scanning'
        
        debug_log(f"Starting scanning phase: {music_files} music files to process", "INFO")
        
        # Second pass: process files with progress updates
        processed_count = 0
        progress_tracker['current_file'] = 'Starting to process music files...'
        debug_log(f"Entering scanning loop for {music_files} music files", "INFO")
        
        for root, dirs, files in os.walk(folder_path):
            debug_log(f"Processing directory: {root} with {len(files)} files", "INFO")
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower()
                
                if file_ext not in supported_extensions:
                    stats['skipped'] += 1
                    continue
                
                processed_count += 1
                progress_tracker['files_processed'] = processed_count
                progress_tracker['current_file'] = f'Processing {processed_count}/{music_files}: {os.path.basename(file_path)}'
                
                # Update progress every 100 files for good balance
                if processed_count % 100 == 0:
                    debug_log(f"Processed {processed_count}/{music_files} files", "INFO")
                    progress_tracker['files_processed'] = processed_count
                
                try:
                    # Extract metadata using mutagen
                    metadata = extract_track_metadata(file_path)
                    if metadata:
                        # Check if track already exists
                        cursor.execute('SELECT id FROM tracks WHERE file_path = ?', (file_path,))
                        existing = cursor.fetchone()
                        
                        if existing:
                            # Update existing track
                            cursor.execute('''
                                UPDATE tracks SET 
                                    title = ?, artist = ?, album = ?, genre = ?, 
                                    year = ?, track_number = ?, duration = ?, 
                                    file_size = ?, last_modified = ?
                                WHERE file_path = ?
                            ''', (
                                metadata.get('title'), metadata.get('artist'), metadata.get('album'),
                                metadata.get('genre'), metadata.get('year'), metadata.get('track_number'),
                                metadata.get('duration'), metadata.get('file_size'), metadata.get('last_modified'),
                                file_path
                            ))
                        else:
                            # Insert new track
                            cursor.execute('''
                                INSERT INTO tracks (file_path, title, artist, album, genre, 
                                                  year, track_number, duration, file_size, last_modified)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                file_path, metadata.get('title'), metadata.get('artist'), metadata.get('album'),
                                metadata.get('genre'), metadata.get('year'), metadata.get('track_number'),
                                metadata.get('duration'), metadata.get('file_size'), metadata.get('last_modified')
                            ))
                        
                        stats['indexed'] += 1
                        progress_tracker['indexed'] = stats['indexed']
                    else:
                        stats['errors'] += 1
                        progress_tracker['errors'] = stats['errors']
                        
                except Exception as e:
                    debug_log(f"Error indexing {file_path}: {str(e)}", "ERROR")
                    stats['errors'] += 1
                    progress_tracker['errors'] = stats['errors']
                
                # Update progress every 100 files for good balance
                if processed_count % 100 == 0:
                    progress_tracker['files_processed'] = processed_count
        
        # Final progress update
        progress_tracker['files_processed'] = processed_count
        progress_tracker['current_file'] = f'Completed! Processed {processed_count} music files'
        debug_log(f"Scanning completed: {processed_count} files processed, {stats['indexed']} indexed, {stats['errors']} errors", "INFO")
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'stats': stats}
        
    except Exception as e:
        conn.close()
        return {'success': False, 'error': str(e)}

def extract_track_metadata(file_path):
    """Extract metadata from a music file"""
    try:
        file_stat = os.stat(file_path)
        file_size = file_stat.st_size
        last_modified = file_stat.st_mtime
        
        # Try to load metadata
        audio = mutagen.File(file_path, easy=True)
        
        if audio is None:
            # Try without easy=True for FLAC files
            audio = mutagen.File(file_path)
        
        metadata = {
            'title': None,
            'artist': None,
            'album': None,
            'genre': None,
            'year': None,
            'track_number': None,
            'duration': None,
            'file_size': file_size,
            'last_modified': last_modified
        }
        
        if audio:
            # Extract common metadata fields
            if hasattr(audio, 'tags'):
                tags = audio.tags
                
                # Handle different tag formats
                if hasattr(tags, 'get'):
                    metadata['title'] = tags.get('title', [None])[0] if tags.get('title') else None
                    metadata['artist'] = tags.get('artist', [None])[0] if tags.get('artist') else None
                    metadata['album'] = tags.get('album', [None])[0] if tags.get('album') else None
                    metadata['genre'] = tags.get('genre', [None])[0] if tags.get('genre') else None
                    
                    # Handle year
                    year_str = tags.get('date', [None])[0] if tags.get('date') else None
                    if year_str:
                        try:
                            metadata['year'] = int(year_str[:4])
                        except (ValueError, TypeError):
                            pass
                    
                    # Handle track number
                    track_str = tags.get('tracknumber', [None])[0] if tags.get('tracknumber') else None
                    if track_str:
                        try:
                            metadata['track_number'] = int(track_str)
                        except (ValueError, TypeError):
                            pass
            
            # Get duration
            if hasattr(audio, 'info') and hasattr(audio.info, 'length'):
                metadata['duration'] = audio.info.length
        
        # Use filename as fallback for title if no metadata
        if not metadata['title']:
            filename = os.path.splitext(os.path.basename(file_path))[0]
            metadata['title'] = filename
        
        return metadata
        
    except Exception as e:
        debug_log(f"Error extracting metadata from {file_path}: {str(e)}", "ERROR")
        return None

def search_local_tracks(query, limit=50, genre=None, year=None, sort_by='title', sort_order='asc'):
    """Search for tracks in the local database with filters and sorting"""
    db_path = os.path.join(DB_DIR, 'local_music.db')
    if not os.path.exists(db_path):
        return []
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Build the WHERE clause based on filters
    where_conditions = []
    params = []
    
    if query:
        search_query = f"%{query}%"
        where_conditions.append("(title LIKE ? OR artist LIKE ? OR album LIKE ?)")
        params.extend([search_query, search_query, search_query])
    
    if genre:
        where_conditions.append("genre = ?")
        params.append(genre)
    
    if year:
        # Handle decade filtering
        if year == '2020s':
            where_conditions.append("year >= 2020")
        elif year == '2010s':
            where_conditions.append("year >= 2010 AND year < 2020")
        elif year == '2000s':
            where_conditions.append("year >= 2000 AND year < 2010")
        elif year == '1990s':
            where_conditions.append("year >= 1990 AND year < 2000")
        elif year == '1980s':
            where_conditions.append("year >= 1980 AND year < 1990")
        elif year == '1970s':
            where_conditions.append("year >= 1970 AND year < 1980")
        elif year == '1960s':
            where_conditions.append("year >= 1960 AND year < 1970")
        elif year == '1950s':
            where_conditions.append("year >= 1950 AND year < 1960")
    
    # Build the WHERE clause
    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
    
    # Build the ORDER BY clause
    sort_field_map = {
        'title': 'title',
        'artist': 'artist', 
        'album': 'album',
        'year': 'year',
        'genre': 'genre',
        'duration': 'duration'
    }
    
    sort_field = sort_field_map.get(sort_by, 'title')
    order_direction = 'DESC' if sort_order == 'desc' else 'ASC'
    
    # Handle NULL values in sorting
    if sort_field in ['year', 'duration']:
        order_clause = f"{sort_field} {order_direction}, title ASC"
    else:
        order_clause = f"{sort_field} {order_direction}"
    
    # Execute the query
    sql = f'''
        SELECT id, title, artist, album, genre, year, duration, file_path
        FROM tracks 
        WHERE {where_clause}
        ORDER BY {order_clause}
        LIMIT ?
    '''
    
    params.append(limit)
    cursor.execute(sql, params)
    
    results = []
    for row in cursor.fetchall():
        results.append({
            'id': row[0],
            'title': row[1] or 'Unknown Title',
            'artist': row[2] or 'Unknown Artist',
            'album': row[3] or 'Unknown Album',
            'genre': row[4],
            'year': row[5],
            'duration': row[6],
            'file_path': row[7]
        })
    
    conn.close()
    return results

@main_bp.route('/api/local-search')
def api_local_search():
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify([])
    rows = search_local_tracks(q, limit=25)
    return jsonify(rows)

def _get_db_path():
    return os.path.join(DB_DIR, 'local_music.db')

def _get_track_by_id(track_id):
    db_path = _get_db_path()
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, artist, album, genre, year, duration, file_path FROM tracks WHERE id = ?', (track_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'id': row[0], 'title': row[1], 'artist': row[2], 'album': row[3],
        'genre': row[4], 'year': row[5], 'duration': row[6], 'file_path': row[7]
    }

def _get_features_by_track_id(track_id):
    db_path = _get_db_path()
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute('PRAGMA table_info(audio_features)')
        if not cursor.fetchall():
            conn.close()
            return None
        cursor.execute('SELECT * FROM audio_features WHERE track_id = ?', (track_id,))
        col_names = [d[1] for d in cursor.description] if cursor.description else []
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return {col_names[i]: row[i] for i in range(len(row))}
    except Exception:
        conn.close()
        return None

@main_bp.route('/api/sonic/seed-info')
def api_sonic_seed_info():
    try:
        track_id = request.args.get('track_id', type=int)
        if not track_id:
            return jsonify({'success': False, 'error': 'track_id required'}), 400
        track = _get_track_by_id(track_id)
        if not track:
            return jsonify({'success': False, 'error': 'Track not found'}), 404
        db_path = os.path.join(DB_DIR, 'local_music.db')
        # Schema check (best-effort; if import missing, fall back to legacy)
        try:
            from feature_store import check_audio_feature_schema, fetch_track_features
            schema_ok, missing = check_audio_feature_schema(db_path)
            features = fetch_track_features(db_path, track_id) if schema_ok else None
            return jsonify({'success': True, 'track': track, 'features': features, 'schema_ok': schema_ok, 'missing': missing})
        except Exception:
            features = _get_features_by_track_id(track_id)
            return jsonify({'success': True, 'track': track, 'features': features, 'schema_ok': True, 'missing': []})
    except Exception as e:
        debug_log(f"Seed info error: {e}", 'ERROR')
        return jsonify({'success': False, 'error': 'Internal error'}), 500

def search_tracks_in_local_library(ollama_suggested_tracks, final_unique_matched_tracks_map):
    """Match Ollama-suggested tracks against the local `tracks` table and add best matches."""
    db_path = os.path.join(DB_DIR, 'local_music.db')
    if not os.path.exists(db_path):
        debug_log("Local DB not found for local matching.", "WARN")
        return []

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    newly_matched_for_batch = []

    def evaluate_local_candidates(title, artist, candidates):
        best = None
        best_score = 0.0
        for c in candidates:
            if is_unwanted_version(c.get('title'), c.get('album')):
                continue
            title_score = calculate_similarity(title, c.get('title'))
            artist_score = calculate_similarity(artist, c.get('artist'))
            combined = (title_score * 0.7) + (artist_score * 0.3)
            if combined > best_score and combined >= 0.82 and title_score >= 0.88 and artist_score >= 0.70:
                best = c
                best_score = combined
                if combined >= 0.92 and title_score >= 0.92:
                    break
        return best

    try:
        for suggested_track in ollama_suggested_tracks:
            title = suggested_track.get('title') or ''
            artist = suggested_track.get('artist') or ''
            if not title or not artist:
                continue
            track_key = (title.lower(), artist.lower())
            if track_key in final_unique_matched_tracks_map:
                continue

            # Exact lower-case match first
            cursor.execute(
                "SELECT id, title, artist, album FROM tracks WHERE lower(title)=? AND lower(artist)=? LIMIT 1",
                (title.lower(), artist.lower())
            )
            row = cursor.fetchone()
            candidates = []
            if row:
                candidates.append({'id': row[0], 'title': row[1] or '', 'artist': row[2] or '', 'album': row[3] or ''})
            else:
                # Fuzzy LIKE search
                like_title = f"%{title}%"
                like_artist = f"%{artist}%"
                cursor.execute(
                    "SELECT id, title, artist, album FROM tracks WHERE title LIKE ? AND artist LIKE ? LIMIT 50",
                    (like_title, like_artist)
                )
                for r in cursor.fetchall():
                    candidates.append({'id': r[0], 'title': r[1] or '', 'artist': r[2] or '', 'album': r[3] or ''})

                # If still nothing, broaden to either title or artist match
                if not candidates:
                    cursor.execute(
                        "SELECT id, title, artist, album FROM tracks WHERE title LIKE ? OR artist LIKE ? LIMIT 50",
                        (like_title, like_artist)
                    )
                    for r in cursor.fetchall():
                        candidates.append({'id': r[0], 'title': r[1] or '', 'artist': r[2] or '', 'album': r[3] or ''})

            if not candidates:
                continue

            best_match = evaluate_local_candidates(title, artist, candidates)

            if best_match:
                match_details = {
                    'id': best_match['id'], 'title': best_match['title'], 'artist': best_match['artist'],
                    'album': best_match['album'], 'source': 'local',
                    'original_suggestion': {'title': title, 'artist': artist, 'album': suggested_track.get('album')}
                }
                final_unique_matched_tracks_map[track_key] = match_details
                newly_matched_for_batch.append(match_details)

                # Update progress for individual track match
                if hasattr(api_generate_playlist, 'playlist_progress'):
                    for playlist_id, progress in api_generate_playlist.playlist_progress.items():
                        if progress.get('status') in ['starting', 'progress']:
                            progress.update({
                                'current_status': f"Matched (local): {best_match['artist']} - {best_match['title']}. Currently at tracks {len(final_unique_matched_tracks_map)}/{progress.get('target_songs', '?')}.",
                                'current_track': f"{best_match['artist']} - {best_match['title']}",
                                'tracks_found': len(final_unique_matched_tracks_map)
                            })
                            break
        return newly_matched_for_batch
    finally:
        conn.close()

def get_local_track_stats():
    """Get statistics about the local music database"""
    db_path = os.path.join(DB_DIR, 'local_music.db')
    if not os.path.exists(db_path):
        return {'total_tracks': 0, 'total_size': 0, 'genres': [], 'artists': 0, 'genre_counts': {}}
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Total tracks
    cursor.execute('SELECT COUNT(*) FROM tracks')
    total_tracks = cursor.fetchone()[0]
    
    # Total size
    cursor.execute('SELECT SUM(file_size) FROM tracks')
    total_size = cursor.fetchone()[0] or 0
    
    # Unique genres
    cursor.execute('SELECT DISTINCT genre FROM tracks WHERE genre IS NOT NULL')
    genres = [row[0] for row in cursor.fetchall()]
    
    # Genre counts
    genre_counts = {}
    for genre in genres:
        cursor.execute('SELECT COUNT(*) FROM tracks WHERE genre = ?', (genre,))
        count = cursor.fetchone()[0]
        genre_counts[genre] = count
    
    # Unique artists
    cursor.execute('SELECT COUNT(DISTINCT artist) FROM tracks WHERE artist IS NOT NULL')
    unique_artists = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_tracks': total_tracks,
        'total_size': total_size,
        'genres': genres,
        'artists': unique_artists,
        'genre_counts': genre_counts
    }

@main_bp.route('/local-music')
def local_music_page():
    """Local music management page"""
    stats = get_local_track_stats()
    return render_template('local_music.html', stats=stats)

@main_bp.route('/api/scan-music-folder', methods=['POST'])
def api_scan_music_folder():
    """API endpoint to scan a music folder"""
    data = request.get_json()
    if not data or 'folder_path' not in data:
        return jsonify({'success': False, 'error': 'Folder path is required'})
    
    folder_path = data['folder_path']
    
    # Start scanning in background with progress tracking
    import threading
    import time
    
    # Create a unique scan ID for this operation
    scan_id = f"scan_{int(time.time())}"
    
    # Initialize scan progress in a simple in-memory store
    if not hasattr(api_scan_music_folder, 'scan_progress'):
        api_scan_music_folder.scan_progress = {}
    
    api_scan_music_folder.scan_progress[scan_id] = {
        'status': 'starting',
        'current_file': '',
        'files_processed': 0,
        'total_files': 0,
        'indexed': 0,
        'errors': 0,
        'skipped': 0,
        'start_time': time.time()
    }
    
    def scan_with_progress():
        try:
            result = scan_music_folder_with_progress(folder_path, scan_id)
            api_scan_music_folder.scan_progress[scan_id]['status'] = 'completed'
            api_scan_music_folder.scan_progress[scan_id]['result'] = result
        except Exception as e:
            api_scan_music_folder.scan_progress[scan_id]['status'] = 'error'
            api_scan_music_folder.scan_progress[scan_id]['error'] = str(e)
    
    # Start scanning in background thread
    thread = threading.Thread(target=scan_with_progress)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True, 
        'scan_id': scan_id,
        'message': 'Scan started in background'
    })

@main_bp.route('/api/scan-progress/<scan_id>')
def api_scan_progress(scan_id):
    """API endpoint to get scan progress"""
    if not hasattr(api_scan_music_folder, 'scan_progress'):
        return jsonify({'error': 'No scan progress available'})
    
    progress = api_scan_music_folder.scan_progress.get(scan_id)
    if not progress:
        return jsonify({'error': 'Scan ID not found'})
    
    if progress['status'] == 'completed':
        # Clean up completed scan
        result = progress.get('result', {})
        if result.get('success'):
            stats = get_local_track_stats()
            return jsonify({
                'status': 'completed',
                'stats': stats,
                'result': result
            })
        else:
            return jsonify({
                'status': 'error',
                'error': result.get('error', 'Unknown error')
            })
    
    return jsonify(progress)

@main_bp.route('/api/playlist-progress/<playlist_id>')
def api_playlist_progress(playlist_id):
    """API endpoint to get playlist generation progress"""
    if not hasattr(api_generate_playlist, 'playlist_progress'):
        return jsonify({'error': 'No playlist progress available'})
    
    progress = api_generate_playlist.playlist_progress.get(playlist_id)
    if not progress:
        return jsonify({'error': 'Playlist ID not found'})
    
    if progress['status'] in ['completed', 'cancelled', 'error']:
        # Clean up completed playlist after a delay
        import threading
        def cleanup():
            time.sleep(10)  # Keep progress visible for 10 seconds
            if playlist_id in api_generate_playlist.playlist_progress:
                del api_generate_playlist.playlist_progress[playlist_id]
        
        thread = threading.Thread(target=cleanup)
        thread.daemon = True
        thread.start()
    
    return jsonify(progress)

@main_bp.route('/api/cancel-playlist/<playlist_id>', methods=['POST'])
def api_cancel_playlist(playlist_id):
    """API endpoint to cancel a playlist generation"""
    if not hasattr(api_generate_playlist, 'playlist_progress'):
        return jsonify({'error': 'No playlist progress available'})
    
    progress = api_generate_playlist.playlist_progress.get(playlist_id)
    if not progress:
        return jsonify({'error': 'Playlist ID not found'})
    
    if progress['status'] in ['completed', 'cancelled']:
        return jsonify({'error': 'Playlist cannot be cancelled'})
    
    # Mark as cancelled
    progress.update({
        'status': 'cancelled',
        'current_status': 'Playlist generation cancelled by user'
    })
    
    return jsonify({'status': 'cancelled'})

@main_bp.route('/api/log-error', methods=['POST'])
def api_log_error():
    """API endpoint to log JavaScript errors"""
    try:
        data = request.get_json()
        if data:
            debug_log(f"JavaScript error: {data.get('message', 'Unknown')} in {data.get('filename', 'Unknown')}:{data.get('lineno', 'Unknown')}:{data.get('colno', 'Unknown')}", "ERROR")
            debug_log(f"Error details: {data.get('error', 'Unknown')}", "DEBUG")
        return jsonify({"status": "logged"}), 200
    except Exception as e:
        debug_log(f"Failed to log JavaScript error: {str(e)}", "ERROR")
        return jsonify({"error": "Failed to log error"}), 500

@main_bp.route('/api/search-local-tracks', methods=['POST'])
def api_search_local_tracks():
    """API endpoint to search local tracks"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Request data is required'})
    
    # Get search parameters with defaults
    query = data.get('query', '')
    limit = data.get('limit', 50)
    genre = data.get('genre', None)
    year = data.get('year', None)
    sort_by = data.get('sort_by', 'title')
    sort_order = data.get('sort_order', 'asc')
    
    # Validate sort parameters
    valid_sort_fields = ['title', 'artist', 'album', 'year', 'genre', 'duration']
    valid_sort_orders = ['asc', 'desc']
    
    if sort_by not in valid_sort_fields:
        sort_by = 'title'
    if sort_order not in valid_sort_orders:
        sort_order = 'asc'
    
    # If no query and no filters, return empty results
    if not query and not genre and not year:
        return jsonify({'success': True, 'results': []})
    
    results = search_local_tracks(query, limit, genre, year, sort_by, sort_order)
    return jsonify({'success': True, 'results': results})

@main_bp.route('/api/local-music-stats')
def api_local_music_stats():
    """API endpoint to get local music statistics"""
    stats = get_local_track_stats()
    return jsonify({'success': True, 'stats': stats})

# Audio Analysis Web Interface Routes
@main_bp.route('/audio-analysis')
def audio_analysis_page():
    """Audio analysis management page"""
    try:
        # Get analysis progress from database
        from audio_analysis_service import AudioAnalysisService
        service = AudioAnalysisService()
        progress = service.get_analysis_progress()
        
        return render_template('audio_analysis.html', progress=progress)
    except Exception as e:
        debug_log(f"Error loading audio analysis page: {e}", "ERROR")
        return render_template('error.html', error="Failed to load audio analysis page")

# Global auto-recovery instance
_auto_recovery_instance = None

def get_auto_recovery():
    """Get or create the auto-recovery instance"""
    global _auto_recovery_instance
    
    if _auto_recovery_instance is None:
        try:
            from audio_analysis_auto_recovery import AudioAnalysisAutoRecovery, AutoRecoveryConfig
            from audio_analysis_monitor import AudioAnalysisMonitor
            
            # Initialize monitor
            monitor = AudioAnalysisMonitor()
            
            # Initialize auto-recovery with restart callback
            def restart_analysis_callback():
                """Callback to restart audio analysis"""
                try:
                    # This will be called by the auto-recovery system
                    # We'll implement the actual restart logic here
                    debug_log("Auto-recovery: Attempting to restart audio analysis", "INFO")
                    return True  # For now, assume success
                except Exception as e:
                    debug_log(f"Auto-recovery restart failed: {e}", "ERROR")
                    return False
            
            config = AutoRecoveryConfig(
                enabled=True,
                check_interval=60,  # Check every minute
                max_consecutive_failures=3,
                base_backoff_minutes=5,
                max_backoff_minutes=30
            )
            
            _auto_recovery_instance = AudioAnalysisAutoRecovery(
                config=config,
                monitor=monitor,
                restart_callback=restart_analysis_callback
            )
            
            debug_log("Auto-recovery system initialized", "INFO")
            
        except Exception as e:
            debug_log(f"Failed to initialize auto-recovery: {e}", "WARNING")
            _auto_recovery_instance = None
    
    return _auto_recovery_instance

@main_bp.route('/api/audio-analysis/start', methods=['POST'])
def api_start_audio_analysis():
    """Start audio analysis batch processing"""
    try:
        data = request.get_json() or {}
        # SQLite doesn't handle concurrent writes well, so default to 1 worker
        max_workers = data.get('max_workers', int(get_config_value('AUDIO_ANALYSIS', 'MaxWorkers', '1')))
        batch_size = data.get('batch_size', int(get_config_value('AUDIO_ANALYSIS', 'BatchSize', '100')))
        limit = data.get('limit', None)  # None = process all pending tracks
        
        # Check if required libraries are available
        try:
            import librosa
        except ImportError:
            return jsonify({
                'success': False, 
                'error': 'Audio analysis libraries not available. Please ensure librosa, numpy, and scipy are installed in the Flask environment.'
            })
        
        # Import and initialize the advanced batch processor
        try:
            from advanced_batch_processor import AdvancedBatchProcessor
        except ImportError as e:
            return jsonify({
                'success': False, 
                'error': f'Failed to import audio analysis modules: {str(e)}. Please check the module paths and virtual environment.'
            })
        
        # Check if processing is already running (and clear stale references)
        if hasattr(api_start_audio_analysis, 'processor') and api_start_audio_analysis.processor:
            try:
                current_status = api_start_audio_analysis.processor.get_status()
                if current_status and current_status.get('status') in ['running', 'stopping']:
                    return jsonify({'success': False, 'error': 'Audio analysis is already running'})
            except Exception:
                pass
            # Stale or not running – clear reference and continue
            api_start_audio_analysis.processor = None
        
        # Initialize processor
        processor = AdvancedBatchProcessor(
            max_workers=max_workers,
            batch_size=batch_size
        )
        
        # Initialize queue
        jobs_added = processor.initialize_queue(limit=limit)
        
        if jobs_added == 0:
            # Nothing to do; ensure no stale processor is kept
            api_start_audio_analysis.processor = None
            return jsonify({'success': False, 'error': 'No tracks available for analysis'})
        
        # Store processor instance only when there is actual work
        api_start_audio_analysis.processor = processor
        
        # Start processing in background thread
        def start_processing():
            try:
                processor.start_processing()
            except Exception as e:
                debug_log(f"Error in audio analysis processing: {e}", "ERROR")
        
        import threading
        thread = threading.Thread(target=start_processing, daemon=True)
        thread.start()
        
        # Start auto-recovery monitoring if available
        auto_recovery = get_auto_recovery()
        if auto_recovery:
            try:
                auto_recovery.start_monitoring()
                debug_log("Auto-recovery monitoring started", "INFO")
            except Exception as e:
                debug_log(f"Failed to start auto-recovery monitoring: {e}", "WARNING")
        
        # Return response with additional info for UI integration
        return jsonify({
            'success': True,
            'message': 'Started audio analysis',
            'jobs_queued': jobs_added,
            'max_workers': max_workers,
            'trigger_ui_update': True  # Signal to UI that status should be updated
        })
        
    except Exception as e:
        debug_log(f"Error starting audio analysis: {e}", "ERROR")
        return jsonify({'success': False, 'error': str(e)})

@main_bp.route('/api/audio-analysis/stop', methods=['POST'])
def api_stop_audio_analysis():
    """Stop audio analysis batch processing"""
    try:
        if not hasattr(api_start_audio_analysis, 'processor') or not api_start_audio_analysis.processor:
            return jsonify({'success': False, 'error': 'No audio analysis running'})
        
        processor = api_start_audio_analysis.processor
        success = processor.stop_processing()
        
        if success:
            # Stop auto-recovery monitoring if available
            auto_recovery = get_auto_recovery()
            if auto_recovery:
                try:
                    auto_recovery.stop_monitoring()
                    debug_log("Auto-recovery monitoring stopped", "INFO")
                except Exception as e:
                    debug_log(f"Failed to stop auto-recovery monitoring: {e}", "WARNING")
            
            api_start_audio_analysis.processor = None
            return jsonify({'success': True, 'message': 'Audio analysis stopped successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to stop audio analysis'})
            
    except Exception as e:
        debug_log(f"Error stopping audio analysis: {e}", "ERROR")
        return jsonify({'success': False, 'error': str(e)})

@main_bp.route('/api/audio-analysis/status')
def api_audio_analysis_status():
    """Get current audio analysis status"""
    try:
        if not hasattr(api_start_audio_analysis, 'processor') or not api_start_audio_analysis.processor:
            return jsonify({
                'status': 'stopped',
                'progress': {
                    'total_jobs': 0,
                    'completed_jobs': 0,
                    'failed_jobs': 0,
                    'progress_percentage': 0,
                    'success_rate': 0
                }
            })
        
        processor = api_start_audio_analysis.processor
        status = processor.get_status()
        
        return jsonify(status)
        
    except Exception as e:
        debug_log(f"Error getting audio analysis status: {e}", "ERROR")
        return jsonify({'error': str(e)})

@main_bp.route('/api/audio-analysis/progress')
def api_audio_analysis_progress():
    """Get audio analysis progress from database"""
    try:
        from audio_analysis_service import AudioAnalysisService
        service = AudioAnalysisService()
        progress = service.get_analysis_progress()
        
        return jsonify({'success': True, 'progress': progress})
        
    except Exception as e:
        debug_log(f"Error getting audio analysis progress: {e}", "ERROR")
        return jsonify({'success': False, 'error': str(e)})

@main_bp.route('/api/audio-analysis/cleanup', methods=['POST'])
def api_audio_analysis_cleanup():
    """Clean up old audio analysis data"""
    try:
        data = request.get_json() or {}
        days_old = data.get('days_old', 30)
        
        from audio_analysis_service import AudioAnalysisService
        service = AudioAnalysisService()
        removed_count = service.cleanup_old_analysis_data(days_old)
        
        return jsonify({
            'success': True,
            'message': f'Cleaned up {removed_count} old analysis records',
            'removed_count': removed_count
        })
        
    except Exception as e:
        debug_log(f"Error cleaning up audio analysis data: {e}", "ERROR")
        return jsonify({'success': False, 'error': str(e)})

@main_bp.route('/api/audio-analysis/health')
def api_audio_analysis_health():
    """Get comprehensive health status of audio analysis system"""
    try:
        from audio_analysis_monitor import AudioAnalysisMonitor
        
        # Initialize monitor
        monitor = AudioAnalysisMonitor()
        
        # Determine if analysis is running; if not, short-circuit with 'stopped' status
        is_running = False
        try:
            if hasattr(api_start_audio_analysis, 'processor') and api_start_audio_analysis.processor:
                current_status = api_start_audio_analysis.processor.get_status()
                is_running = bool(current_status and current_status.get('status') == 'running')
        except Exception:
            is_running = False
        
        # Get health status (with awareness of running state)
        health_status = monitor.get_health_status()
        if not is_running:
            # Override stall and warnings when stopped
            health_status['current_status'] = 'stopped'
            health_status['stalled'] = False
            health_status['processing_rate'] = 0.0
            # Clear anomalies/recommendations related to performance while stopped
            health_status['anomalies'] = []
            health_status['recommendations'] = ['Analysis is currently stopped. Start analysis to resume monitoring.']
        
        # Get stall analysis
        stall_analysis = monitor.get_stall_analysis()
        if not is_running:
            stall_analysis['stall_probability'] = 'low'
            stall_analysis['stall_indicators'] = []
        
        # Combine health information
        health_info = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'health': health_status,
            'stall_analysis': stall_analysis,
            'auto_recovery_available': True,  # Will be enhanced when auto-recovery is integrated
            'recommendations': health_status.get('recommendations', [])
        }
        
        return jsonify(health_info)
        
    except Exception as e:
        debug_log(f"Error getting audio analysis health: {e}", "ERROR")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

@main_bp.route('/api/audio-analysis/restart', methods=['POST'])
def api_audio_analysis_restart():
    """Manually restart audio analysis (for recovery)"""
    try:
        # Check if analysis is currently running
        if hasattr(api_start_audio_analysis, 'processor') and api_start_audio_analysis.processor:
            try:
                current_status = api_start_audio_analysis.processor.get_status()
                if current_status and current_status.get('status') == 'running':
                    # Stop current analysis
                    api_start_audio_analysis.processor.stop_processing()
                    api_start_audio_analysis.processor = None
                    debug_log("Stopped running audio analysis for restart", "INFO")
            except Exception as e:
                debug_log(f"Error stopping current analysis: {e}", "WARNING")
        
        # Start fresh analysis
        data = request.get_json() or {}
        max_workers = data.get('max_workers', int(get_config_value('AUDIO_ANALYSIS', 'MaxWorkers', '1')))
        batch_size = data.get('batch_size', int(get_config_value('AUDIO_ANALYSIS', 'BatchSize', '100')))
        
        # Import and initialize the advanced batch processor
        try:
            from advanced_batch_processor import AdvancedBatchProcessor
        except ImportError as e:
            return jsonify({
                'success': False,
                'error': f'Failed to import audio analysis modules: {str(e)}'
            })
        
        # Initialize processor
        processor = AdvancedBatchProcessor(
            max_workers=max_workers,
            batch_size=batch_size
        )
        
        # Initialize queue
        jobs_added = processor.initialize_queue()
        
        if jobs_added == 0:
            return jsonify({'success': False, 'error': 'No tracks available for analysis'})
        
        # Store processor instance
        api_start_audio_analysis.processor = processor
        
        # Start processing in background thread
        def start_processing():
            try:
                processor.start_processing()
            except Exception as e:
                debug_log(f"Error in audio analysis processing: {e}", "ERROR")
        
        import threading
        thread = threading.Thread(target=start_processing, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Audio analysis restarted successfully',
            'jobs_queued': jobs_added,
            'max_workers': max_workers,
            'trigger_ui_update': True
        })
        
    except Exception as e:
        debug_log(f"Error restarting audio analysis: {e}", "ERROR")
        return jsonify({'success': False, 'error': str(e)})

@main_bp.route('/api/audio-analysis/auto-recovery/status')
def api_auto_recovery_status():
    """Get auto-recovery system status"""
    try:
        auto_recovery = get_auto_recovery()
        if not auto_recovery:
            return jsonify({
                'success': False,
                'error': 'Auto-recovery system not available'
            })
        
        status = auto_recovery.get_status()
        history = auto_recovery.get_recovery_history()
        
        return jsonify({
            'success': True,
            'status': status,
            'history': history
        })
        
    except Exception as e:
        debug_log(f"Error getting auto-recovery status: {e}", "ERROR")
        return jsonify({'success': False, 'error': str(e)})

@main_bp.route('/api/audio-analysis/auto-recovery/start', methods=['POST'])
def api_auto_recovery_start():
    """Start auto-recovery monitoring"""
    try:
        auto_recovery = get_auto_recovery()
        if not auto_recovery:
            return jsonify({
                'success': False,
                'error': 'Auto-recovery system not available'
            })
        
        success = auto_recovery.start_monitoring()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Auto-recovery monitoring started'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to start auto-recovery monitoring'
            })
        
    except Exception as e:
        debug_log(f"Error starting auto-recovery: {e}", "ERROR")
        return jsonify({'success': False, 'error': str(e)})

@main_bp.route('/api/audio-analysis/auto-recovery/stop', methods=['POST'])
def api_auto_recovery_stop():
    """Stop auto-recovery monitoring"""
    try:
        auto_recovery = get_auto_recovery()
        if not auto_recovery:
            return jsonify({
                'success': False,
                'error': 'Auto-recovery system not available'
            })
        
        success = auto_recovery.stop_monitoring()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Auto-recovery monitoring stopped'
            })
        else:
                return jsonify({
                'success': False,
                'error': 'Failed to stop auto-recovery monitoring'
            })
        
    except Exception as e:
        debug_log(f"Error stopping auto-recovery: {e}", "ERROR")
        return jsonify({'success': False, 'error': str(e)})

@main_bp.route('/api/audio-analysis/auto-recovery/reset', methods=['POST'])
def api_auto_recovery_reset():
    """Reset auto-recovery failure count (manual intervention)"""
    try:
        auto_recovery = get_auto_recovery()
        if not auto_recovery:
            return jsonify({
                'success': False,
                'error': 'Auto-recovery system not available'
            })
        
        auto_recovery.reset_failure_count()
        
        return jsonify({
            'success': True,
            'message': 'Auto-recovery failure count reset'
        })
        
    except Exception as e:
        debug_log(f"Error resetting auto-recovery: {e}", "ERROR")
        return jsonify({'success': False, 'error': str(e)})

# --- Configuration Management ---
@main_bp.route('/api/audio-analysis/config', methods=['GET'])
def api_get_monitoring_config():
    """Get current monitoring configuration"""
    try:
        from monitoring_config import get_config_manager
        
        config_manager = get_config_manager()
        config = config_manager.get_monitoring_config()
        
        return jsonify({
            'success': True,
            'config': {
                'stall_detection_timeout': config.stall_detection_timeout,
                'monitoring_interval': config.monitoring_interval,
                'progress_history_retention_days': config.progress_history_retention_days,
                'auto_recovery_enabled': config.auto_recovery_enabled,
                'auto_recovery_check_interval': config.auto_recovery_check_interval,
                'max_consecutive_failures': config.max_consecutive_failures,
                'recovery_backoff_multiplier': config.recovery_backoff_multiplier,
                'recovery_max_delay': config.recovery_max_delay,
                'high_error_rate_threshold': config.high_error_rate_threshold,
                'stall_warning_threshold': config.stall_warning_threshold,
                'escalation_threshold': config.escalation_threshold,
                'critical_stall_threshold': config.critical_stall_threshold,
                'progress_stagnation_hours': config.progress_stagnation_hours,
                'health_update_interval': config.health_update_interval,
                'stall_detection_interval': config.stall_detection_interval,
                'progress_update_interval': config.progress_update_interval,
                'recovery_status_interval': config.recovery_status_interval
            }
        })
        
    except Exception as e:
        debug_log(f"Error getting monitoring config: {e}", "ERROR")
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/audio-analysis/config', methods=['POST'])
def api_update_monitoring_config():
    """Update monitoring configuration"""
    try:
        from monitoring_config import get_config_manager
        
        config_manager = get_config_manager()
        new_config = request.get_json()
        
        if not new_config:
            return jsonify({'success': False, 'error': 'No configuration data provided'}), 400
        
        # Update configuration
        config_manager.update_monitoring_config(**new_config)
        
        # Save to file
        config_manager.save_config()
        
        # Validate updated configuration
        validation = config_manager.validate_config()
        
        return jsonify({
            'success': True,
            'message': 'Configuration updated successfully',
            'validation': validation
        })
        
    except Exception as e:
        debug_log(f"Error updating monitoring config: {e}", "ERROR")
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/audio-analysis/config/reset', methods=['POST'])
def api_reset_monitoring_config():
    """Reset monitoring configuration to defaults"""
    try:
        from monitoring_config import get_config_manager
        
        config_manager = get_config_manager()
        
        # Reset to defaults
        config_manager.monitoring_config = config_manager.monitoring_config.__class__()
        
        # Save to file
        config_manager.save_config()
        
        # Validate reset configuration
        validation = config_manager.validate_config()
        
        return jsonify({
            'success': True,
            'message': 'Configuration reset to defaults',
            'config': config_manager.get_config_summary(),
            'validation': validation
        })
        
    except Exception as e:
        debug_log(f"Error resetting monitoring config: {e}", "ERROR")
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/audio-analysis/config/validate', methods=['POST'])
def api_validate_monitoring_config():
    """Validate monitoring configuration"""
    try:
        from monitoring_config import get_config_manager
        
        config_manager = get_config_manager()
        new_config = request.get_json()
        
        if not new_config:
            return jsonify({'success': False, 'error': 'No configuration data provided'}), 400
        
        # Create temporary config for validation
        temp_config = config_manager.monitoring_config.__class__()
        for key, value in new_config.items():
            if hasattr(temp_config, key):
                setattr(temp_config, key, value)
        
        # Validate configuration
        validation = config_manager.validate_config()
        
        return jsonify({
            'success': True,
            'validation': validation
        })
        
    except Exception as e:
        debug_log(f"Error validating monitoring config: {e}", "ERROR")
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/browse-path')
def api_browse_path():
    """API endpoint for file browsing"""
    import os
    from pathlib import Path
    
    # Get the path parameter, default to user's home directory
    path = request.args.get('path', '')
    
    if not path:
        # Default to user's home directory
        path = str(Path.home())
    
    try:
        # Ensure the path exists and is accessible
        if not os.path.exists(path):
            return jsonify({'error': 'Path does not exist'}), 404
        
        if not os.access(path, os.R_OK):
            return jsonify({'error': 'Path is not accessible'}), 403
        
        # List directory contents - optimized for performance
        try:
            items = os.listdir(path)
        except (OSError, PermissionError) as e:
            return jsonify({'error': f'Cannot read directory: {str(e)}'}), 403
        
        # Separate directories and files for faster processing
        dirs = []
        files = []
        
        # Process directories first (always fast)
        for item in items:
            if item.startswith('.'):  # Skip hidden items
                continue
                
            item_path = os.path.join(path, item)
            try:
                if os.path.isdir(item_path):
                    dirs.append({
                        'name': item,
                        'path': item_path,
                        'readable': os.access(item_path, os.R_OK)
                    })
            except (OSError, PermissionError):
                continue
        
        # Sort directories for better UX
        dirs.sort(key=lambda x: x['name'].lower())
        
        # Only scan for audio files if directory isn't too large
        total_items = len(items)
        if total_items <= 200:  # Much more aggressive limit for faster browsing
            max_files_to_scan = 25  # Reduced limit for faster browsing
            files_found = 0
            
            for item in items:
                if item.startswith('.'):
                    continue
                    
                item_path = os.path.join(path, item)
                try:
                    if os.path.isfile(item_path) and files_found < max_files_to_scan:
                        # Quick audio file check
                        if any(item.lower().endswith(ext) for ext in ['.mp3', '.flac', '.m4a', '.ogg', '.wav', '.aac']):
                            try:
                                size = os.path.getsize(item_path)
                                files.append({
                                    'name': item,
                                    'path': item_path,
                                    'size': size
                                })
                                files_found += 1
                            except (OSError, PermissionError):
                                continue
                except (OSError, PermissionError):
                    continue
            
            # Sort files for better UX
            files.sort(key=lambda x: x['name'].lower())
        else:
            # For large directories, skip file scanning entirely for speed
            files = []
            max_files_to_scan = 0
            files_found = 0
        
        # Get parent directory
        parent_path = str(Path(path).parent)
        if parent_path == path:  # We're at root
            parent_path = None
        
        # Add performance info
        total_items = len(items)
        hidden_items = len([i for i in items if i.startswith('.')])
        visible_items = total_items - hidden_items
        
        # Performance notes
        performance_note = None
        if total_items > 500:
            performance_note = "Large directory - audio files hidden for performance"
        elif files_found >= max_files_to_scan:
            performance_note = f"Showing first {max_files_to_scan} audio files for performance"
        
        return jsonify({
            'current_path': path,
            'parent_path': parent_path,
            'directories': dirs,
            'files': files,
            'performance_info': {
                'total_items': total_items,
                'visible_items': visible_items,
                'directories_count': len(dirs),
                'files_scanned': files_found,
                'max_files_scanned': max_files_to_scan,
                'note': performance_note
            }
        })
        
    except Exception as e:
        debug_log(f"Error browsing path {path}: {str(e)}", "ERROR")
        return jsonify({'error': f'Error browsing directory: {str(e)}'}), 500

# Cache directories
CACHE_DIR = os.path.join(os.getcwd(), '.cache')
ART_CACHE_DIR = os.path.join(CACHE_DIR, 'art')
os.makedirs(ART_CACHE_DIR, exist_ok=True)


def _build_art_cache_key(artist: str = '', album: str = '', title: str = '') -> str:
    base = f"artist={artist.strip().lower()}|album={album.strip().lower()}|title={title.strip().lower()}"
    return hashlib.md5(base.encode('utf-8')).hexdigest() + '.jpg'


def _itunes_search(term: str, entity: str = 'album'):
    try:
        params = {'term': term, 'entity': entity, 'limit': 1}
        r = requests.get('https://itunes.apple.com/search', params=params, timeout=6)
        if r.ok:
            return r.json()
    except Exception as e:
        debug_log(f"iTunes search failed: {e}", "WARN")
    return None


def _download_and_cache_image(url: str, dest_path: str) -> bool:
    try:
        resp = requests.get(url, timeout=10)
        if resp.ok and resp.content:
            with open(dest_path, 'wb') as f:
                f.write(resp.content)
            return True
    except Exception as e:
        debug_log(f"Download art failed: {e}", "WARN")
    return False


def fetch_art_image(artist: str = '', album: str = '', title: str = '') -> str:
    """Fetch art for given artist/album/title from cache or iTunes. Returns file path or empty string."""
    if not (artist or album or title):
        return ''
    cache_name = _build_art_cache_key(artist or '', album or '', title or '')
    cache_path = os.path.join(ART_CACHE_DIR, cache_name)
    if os.path.exists(cache_path):
        return cache_path

    # Try album art first if album provided
    artwork_url = None
    if artist and album:
        data = _itunes_search(f"{artist} {album}", entity='album')
        if data and data.get('resultCount'):
            artwork_url = data['results'][0].get('artworkUrl100')
    # Fallback to track art via song entity
    if not artwork_url and artist and title:
        data = _itunes_search(f"{artist} {title}", entity='song')
        if data and data.get('resultCount'):
            artwork_url = data['results'][0].get('artworkUrl100')
    # Fallback to artist
    if not artwork_url and artist:
        data = _itunes_search(artist, entity='musicArtist')
        if data and data.get('resultCount'):
            artwork_url = data['results'][0].get('artworkUrl100')

    if artwork_url:
        # Upscale to higher resolution if possible
        larger = artwork_url.replace('100x100', '600x600')
        if _download_and_cache_image(larger, cache_path) or _download_and_cache_image(artwork_url, cache_path):
            return cache_path

    return ''


@main_bp.route('/art')
def art_image():
    artist = request.args.get('artist', '', type=str)
    album = request.args.get('album', '', type=str)
    title = request.args.get('title', '', type=str)
    path = fetch_art_image(artist=artist, album=album, title=title)
    if path and os.path.exists(path):
        return send_file(path, mimetype='image/jpeg', conditional=True)
    # No art, return 204 to let frontend handle placeholder
    return ('', 204)

# Sonic Traveller Background Processing
_sonic_jobs = {}
_sonic_job_lock = threading.Lock()

class SonicTravellerJob:
    def __init__(self, job_id, seed_track_id, num_songs, threshold, ollama_model):
        self.job_id = job_id
        self.seed_track_id = seed_track_id
        self.num_songs = num_songs
        self.threshold = threshold
        self.ollama_model = ollama_model
        self.status = 'running'  # running, completed, failed, stopped
        self.progress = 0.0
        self.current_step = 'Initializing...'
        self.results = []
        self.error = None
        self.start_time = datetime.now()
        self.end_time = None
        self.total_candidates = 0
        self.accepted_tracks = 0
        self.attempts = 0
        self.max_attempts = 10
        self.candidate_multiplier = 3
        
        # NEW: Random seed for variety and feedback loop
        self.random_seed = str(uuid.uuid4())[:8]  # Short seed for prompts
        self.accepted_examples = []  # Track successful candidates for feedback
        self.rejected_examples = []  # Track rejected candidates for feedback
        self.iteration_history = []  # Track each iteration's results

    def update_progress(self, progress, step):
        self.progress = progress
        self.current_step = step

    def add_result(self, track):
        self.results.append(track)
        self.accepted_tracks = len(self.results)

    def complete(self, success=True):
        self.status = 'completed' if success else 'failed'
        self.progress = 100.0 if success else self.progress
        self.end_time = datetime.now()

    def stop(self):
        self.status = 'stopped'
        self.end_time = datetime.now()

def _run_sonic_traveller_job(job):
    """Background thread function for Sonic Traveller generation with enhanced feedback loop"""
    try:
        job.update_progress(5.0, 'Fetching seed track features...')
        
        # Get seed track info
        db_path = os.path.join(DB_DIR, 'local_music.db')
        seed_track = _get_track_by_id(job.seed_track_id)
        if not seed_track:
            job.error = 'Seed track not found'
            job.complete(False)
            return

        # Check if seed has features
        try:
            from feature_store import fetch_track_features
            seed_features = fetch_track_features(db_path, job.seed_track_id)
            if not seed_features:
                job.error = 'Seed track has no audio features'
                job.complete(False)
                return
        except Exception as e:
            job.error = f'Failed to fetch seed features: {str(e)}'
            job.complete(False)
            return

        job.update_progress(15.0, 'Computing feature statistics...')
        
        # Get feature stats for normalization
        try:
            from sonic_similarity import get_feature_stats, build_vector, compute_distance
            stats = get_feature_stats(db_path)
            seed_vec = build_vector(seed_features, stats)
        except Exception as e:
            job.error = f'Failed to compute feature statistics: {str(e)}'
            job.complete(False)
            return

        job.update_progress(25.0, 'Starting iterative generation with feedback loop...')
        
        # Generate candidates iteratively with feedback
        ollama_url = get_config_value('OLLAMA', 'URL')
        if not ollama_url:
            job.error = 'Ollama URL not configured'
            job.complete(False)
            return

        seed_text = f"{seed_track.get('title', '')} - {seed_track.get('artist', '')}"
        excludes = set()
        
        while len(job.results) < job.num_songs and job.attempts < job.max_attempts:
            job.attempts += 1
            remaining = job.num_songs - len(job.results)
            candidates_needed = min(remaining * job.candidate_multiplier, 50)  # Cap at 50
            
            job.update_progress(25.0 + (job.attempts * 5.0), f'Iteration {job.attempts}: Generating {candidates_needed} candidates with feedback...')
            
            # Build adaptive prompt based on iteration and feedback
            prompt = _build_adaptive_prompt(job, seed_text, candidates_needed, excludes)
            
            candidates = generate_tracks_with_ollama(ollama_url, job.ollama_model, prompt, candidates_needed, 0, []) or []
            if not candidates:
                continue
                
            job.total_candidates += len(candidates)
            
            job.update_progress(25.0 + (job.attempts * 5.0) + 10.0, f'Mapping {len(candidates)} candidates to local library...')
            
            # Map candidates to local tracks with features
            mapped = _map_candidates_to_local_with_features(candidates)
            if not mapped:
                continue
                
            # Filter out already accepted tracks
            mapped = [m for m in mapped if m['id'] not in {r['id'] for r in job.results}]
            if not mapped:
                continue
                
            job.update_progress(25.0 + (job.attempts * 5.0) + 20.0, f'Computing distances for {len(mapped)} candidates...')
            
            # Compute distances and accept tracks within threshold
            track_ids = [m['id'] for m in mapped]
            try:
                from feature_store import fetch_batch_features
                features_map = fetch_batch_features(db_path, track_ids)
                
                scored = []
                for m in mapped:
                    if m['id'] not in features_map:
                        continue
                    cand_vec = build_vector(features_map[m['id']], stats)
                    dist = compute_distance(seed_vec, cand_vec)
                    scored.append((dist, m))
                
                scored.sort(key=lambda x: x[0])
                
                # Track this iteration's results for feedback
                iteration_results = {
                    'iteration': job.attempts,
                    'candidates_generated': len(candidates),
                    'candidates_mapped': len(mapped),
                    'candidates_with_features': len(features_map),
                    'accepted': [],
                    'rejected': []
                }
                
                # Accept tracks within threshold and collect feedback
                for dist, track in scored:
                    if dist <= job.threshold and len(job.results) < job.num_songs:
                        track_with_dist = dict(track, distance=round(dist, 3))
                        job.add_result(track_with_dist)
                        
                        # Add to accepted examples for feedback
                        job.accepted_examples.append({
                            'title': track['title'],
                            'artist': track['artist'],
                            'distance': dist,
                            'iteration': job.attempts
                        })
                        
                        iteration_results['accepted'].append({
                            'title': track['title'],
                            'artist': track['artist'],
                            'distance': dist
                        })
                        
                        excludes.add(f"{track['title']} - {track['artist']}")
                        if len(job.results) >= job.num_songs:
                            break
                    else:
                        # Track rejected candidates for feedback
                        if dist > job.threshold:
                            job.rejected_examples.append({
                                'title': track['title'],
                                'artist': track['artist'],
                                'distance': dist,
                                'iteration': job.attempts
                            })
                            iteration_results['rejected'].append({
                                'title': track['title'],
                                'artist': track['artist'],
                                'distance': dist
                            })
                
                # Store iteration history
                job.iteration_history.append(iteration_results)
                            
            except Exception as e:
                debug_log(f"Distance computation error in job {job.job_id}: {e}", 'ERROR')
                continue
                
            job.update_progress(25.0 + (job.attempts * 5.0) + 30.0, f'Iteration {job.attempts}: Accepted {len([r for r in iteration_results["accepted"]])}/{remaining} tracks...')
            
            # If we got enough tracks, we're done
            if len(job.results) >= job.num_songs:
                break
                
            # Small delay to prevent overwhelming Ollama
            time.sleep(0.5)
        
        if job.results:
            job.complete(True)
            job.update_progress(100.0, f'Completed! Generated {len(job.results)} tracks from {job.total_candidates} candidates in {job.attempts} iterations with feedback loop.')
            
            # NEW: Save to playlist history
            _save_sonic_traveller_to_history(job, seed_track)
        else:
            job.error = f'Failed to generate enough tracks after {job.attempts} iterations'
            job.complete(False)
            
    except Exception as e:
        job.error = f'Unexpected error: {str(e)}'
        job.complete(False)
        debug_log(f"Sonic Traveller job {job.job_id} failed: {e}", 'ERROR')

def _save_sonic_traveller_to_history(job, seed_track):
    """Save Sonic Traveller playlist to the existing history system"""
    try:
        # Load existing history
        history_file = HISTORY_FILE  # Use the same file as the main history system
        playlist_history = []
        
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content and content.endswith(']'):
                        playlist_history = json.loads(content)
                    else:
                        debug_log(f"History file {history_file} appears corrupted, starting fresh", 'WARN')
                        playlist_history = []
            except Exception as e:
                debug_log(f"Error loading history file {history_file}: {e}, starting fresh", 'WARN')
                playlist_history = []
        
        # Create Sonic Traveller history entry
        history_entry = {
            'id': f"sonic_{job.job_id}",
            'name': f"Sonic Traveller: {seed_track.get('artist', 'Unknown')} - {seed_track.get('title', 'Unknown')}",
            'description': f"AI-generated playlist using Sonic Traveller with feedback loop",
            'tracks': job.results,
            'track_count': len(job.results),
            'timestamp': datetime.now().isoformat(),
            'generator_type': 'sonic_traveller',
            'metadata': {
                'seed_track': {
                    'id': seed_track.get('id'),
                    'title': seed_track.get('title'),
                    'artist': seed_track.get('artist'),
                    'album': seed_track.get('album')
                },
                'generation_params': {
                    'threshold': job.threshold,
                    'target_size': job.num_songs,
                    'ollama_model': job.ollama_model,
                    'random_seed': job.random_seed
                },
                'generation_stats': {
                    'iterations': job.attempts,
                    'total_candidates': job.total_candidates,
                    'acceptance_rate': len(job.results) / job.total_candidates if job.total_candidates > 0 else 0
                },
                'feedback_loop': {
                    'accepted_examples': job.accepted_examples,
                    'rejected_examples': job.rejected_examples,
                    'iteration_history': job.iteration_history
                }
            }
        }
        
        # Add to history (at the beginning for recent playlists)
        playlist_history.insert(0, history_entry)
        
        # Keep only last 100 entries to prevent history from growing too large
        if len(playlist_history) > 100:
            playlist_history = playlist_history[:100]
        
        # Validate JSON before saving
        try:
            json.dumps(playlist_history, indent=2, ensure_ascii=False)
        except Exception as e:
            debug_log(f"JSON validation failed before saving: {e}", 'ERROR')
            return
        
        # Save updated history
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(playlist_history, f, indent=2, ensure_ascii=False)
        
        debug_log(f"Saved Sonic Traveller playlist to history: {history_entry['name']}", 'INFO')
        debug_log(f"History file: {history_file}, Entries: {len(playlist_history)}", 'INFO')
        
    except Exception as e:
        debug_log(f"Failed to save Sonic Traveller playlist to history: {e}", 'ERROR')
        import traceback
        debug_log(f"Traceback: {traceback.format_exc()}", 'ERROR')

def _build_adaptive_prompt(job, seed_text, candidates_needed, excludes):
    """Build adaptive prompt based on iteration and feedback"""
    # Generate a new random seed for each LLM call to ensure variety
    import random
    import string
    current_seed = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    
    base_prompt = f"Suggest {candidates_needed} songs similar to: {seed_text}"
    
    # Add random seed for variety
    base_prompt += f"\n\nUse random seed {current_seed} to ensure variety and avoid repetitive suggestions."
    
    # Add specific musical style guidance
    base_prompt += "\n\nIMPORTANT: Focus on songs with similar musical characteristics:"
    base_prompt += "\n- Similar genre (rock, alternative rock, post-grunge)"
    base_prompt += "\n- Similar energy level and mood"
    base_prompt += "\n- Similar era and style"
    base_prompt += "\n- Avoid completely different genres from the source track."

    
    # Add feedback from previous iterations
    if job.accepted_examples:
        accepted_text = ", ".join([f"{ex['artist']} - {ex['title']}" for ex in job.accepted_examples[-5:]])  # Last 5 examples
        base_prompt += f"\n\nThese tracks were good matches: {accepted_text}"
        base_prompt += "\nPlease suggest more songs in a similar style and energy level."
    
    if job.rejected_examples:
        rejected_text = ", ".join([f"{ex['artist']} - {ex['title']}" for ex in job.rejected_examples[-3:]])  # Last 3 examples
        base_prompt += f"\n\nAvoid these styles: {rejected_text}"
    
    # Add exclusions
    if excludes:
        exclude_list = list(excludes)[:10]  # Limit to 10 exclusions
        exclude_text = ", ".join(exclude_list)
        base_prompt += f"\n\nExclude these tracks: {exclude_text}"
    
    base_prompt += "\n\nReturn only Title and Artist, one per line."
    
    return base_prompt

@main_bp.route('/api/sonic/start', methods=['POST'])
def api_sonic_start():
    """Start a new Sonic Traveller generation job"""
    try:
        data = request.get_json() or {}
        seed_track_id = data.get('seed_track_id')
        num_songs = int(data.get('num_songs', 20))
        threshold = float(data.get('threshold', 0.35))
        ollama_model = get_config_value('OLLAMA', 'Model', 'llama3')
        
        if not seed_track_id:
            return jsonify({'success': False, 'error': 'seed_track_id is required'}), 400
            
        # Check if there's already a running job
        with _sonic_job_lock:
            running_jobs = [j for j in _sonic_jobs.values() if j.status == 'running']
            if running_jobs:
                return jsonify({'success': False, 'error': 'Another Sonic Traveller job is already running'}), 409
        
        # Create new job
        job_id = str(uuid.uuid4())
        job = SonicTravellerJob(job_id, seed_track_id, num_songs, threshold, ollama_model)
        
        with _sonic_job_lock:
            _sonic_jobs[job_id] = job
        
        # Start background thread
        thread = threading.Thread(target=_run_sonic_traveller_job, args=(job,), daemon=True)
        thread.start()
        
        return jsonify({
            'success': True, 
            'job_id': job_id,
            'message': 'Sonic Traveller generation started'
        }), 200
        
    except Exception as e:
        debug_log(f"Sonic start error: {e}", 'ERROR')
        return jsonify({'success': False, 'error': 'Internal error'}), 500

@main_bp.route('/api/sonic/status')
def api_sonic_status():
    """Get status of Sonic Traveller jobs"""
    try:
        job_id = request.args.get('job_id')
        if not job_id:
            return jsonify({'success': False, 'error': 'job_id required'}), 400
            
        with _sonic_job_lock:
            job = _sonic_jobs.get(job_id)
            if not job:
                return jsonify({'success': False, 'error': 'Job not found'}), 404
                
            return jsonify({
                'success': True,
                'job': {
                    'id': job.job_id,
                    'status': job.status,
                    'progress': job.progress,
                    'current_step': job.current_step,
                    'results': job.results,
                    'error': job.error,
                    'start_time': job.start_time.isoformat() if job.start_time else None,
                    'end_time': job.end_time.isoformat() if job.end_time else None,
                    'total_candidates': job.total_candidates,
                    'accepted_tracks': job.accepted_tracks,
                    'attempts': job.attempts,
                    'max_attempts': job.max_attempts,
                    # NEW: Enhanced feedback loop information
                    'random_seed': job.random_seed,
                    'accepted_examples': job.accepted_examples,
                    'rejected_examples': job.rejected_examples,
                    'iteration_history': job.iteration_history
                }
            }), 200
            
    except Exception as e:
        debug_log(f"Sonic status error: {e}", 'ERROR')
        return jsonify({'success': False, 'error': 'Internal error'}), 500

@main_bp.route('/api/sonic/stop', methods=['POST'])
def api_sonic_stop():
    """Stop a running Sonic Traveller job"""
    try:
        data = request.get_json() or {}
        job_id = data.get('job_id')
        
        if not job_id:
            return jsonify({'success': False, 'error': 'job_id required'}), 400
            
        with _sonic_job_lock:
            job = _sonic_jobs.get(job_id)
            if not job:
                return jsonify({'success': False, 'error': 'Job not found'}), 404
                
            if job.status != 'running':
                return jsonify({'success': False, 'error': 'Job is not running'}), 400
                
            job.stop()
            
            return jsonify({
                'success': True,
                'message': 'Sonic Traveller generation stopped'
            }), 200
            
    except Exception as e:
        debug_log(f"Sonic stop error: {e}", 'ERROR')
        return jsonify({'success': False, 'error': 'Internal error'}), 500

@main_bp.route('/api/sonic/cleanup', methods=['POST'])
def api_sonic_cleanup():
    """Clean up completed/failed Sonic Traveller jobs"""
    try:
        data = request.get_json() or {}
        job_id = data.get('job_id')
        
        with _sonic_job_lock:
            if job_id:
                # Clean up specific job
                if job_id in _sonic_jobs:
                    del _sonic_jobs[job_id]
            else:
                # Clean up all completed/failed jobs older than 1 hour
                cutoff = datetime.now().timestamp() - 3600
                to_remove = []
                for jid, job in _sonic_jobs.items():
                    if job.status in ['completed', 'failed', 'stopped']:
                        if job.end_time and job.end_time.timestamp() < cutoff:
                            to_remove.append(jid)
                
                for jid in to_remove:
                    del _sonic_jobs[jid]
                    
            return jsonify({
                'success': True,
                'message': 'Cleanup completed'
            }), 200
            
    except Exception as e:
        debug_log(f"Sonic cleanup error: {e}", 'ERROR')
        return jsonify({'success': False, 'error': 'Internal error'}), 500

@main_bp.route('/api/sonic/export-json')
def api_sonic_export_json():
    """Export Sonic Traveller results as JSON"""
    try:
        job_id = request.args.get('job_id')
        if not job_id:
            return jsonify({'success': False, 'error': 'job_id required'}), 400
            
        with _sonic_job_lock:
            job = _sonic_jobs.get(job_id)
            if not job:
                return jsonify({'success': False, 'error': 'Job not found'}), 404
                
            if job.status not in ['completed', 'stopped']:
                return jsonify({'success': False, 'error': 'Job not completed'}), 400
                
            # Create export data
            export_data = {
                'export_info': {
                    'exported_at': datetime.now().isoformat(),
                    'job_id': job.job_id,
                    'status': job.status,
                    'start_time': job.start_time.isoformat() if job.start_time else None,
                    'end_time': job.end_time.isoformat() if job.end_time else None,
                    'total_candidates': job.total_candidates,
                    'attempts': job.attempts,
                    'threshold': getattr(job, 'threshold', None),
                },
                'seed_track': {
                    'id': job.seed_track_id,
                    'info': _get_track_by_id(job.seed_track_id)
                },
                'results': job.results
            }
            
            # Create filename
            seed_track = _get_track_by_id(job.seed_track_id)
            if seed_track:
                artist = seed_track.get('artist', 'Unknown').replace('/', '_').replace('\\', '_')
                title = seed_track.get('title', 'Unknown').replace('/', '_').replace('\\', '_')
                filename = f"sonic_traveller_{artist}_{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            else:
                filename = f"sonic_traveller_job_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Return JSON response with download headers
            response = jsonify(export_data)
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            response.headers['Content-Type'] = 'application/json'
            return response
            
    except Exception as e:
        debug_log(f"Sonic export JSON error: {e}", 'ERROR')
        return jsonify({'success': False, 'error': 'Internal error'}), 500

@main_bp.route('/api/sonic/export-m3u')
def api_sonic_export_m3u():
    """Export Sonic Traveller results as M3U playlist"""
    try:
        job_id = request.args.get('job_id')
        if not job_id:
            return jsonify({'success': False, 'error': 'job_id required'}), 400
            
        with _sonic_job_lock:
            job = _sonic_jobs.get(job_id)
            if not job:
                return jsonify({'success': False, 'error': 'Job not found'}), 404
                
            if job.status not in ['completed', 'stopped']:
                return jsonify({'success': False, 'error': 'Job not completed'}), 400
                
            # Get seed track info for header
            seed_track = _get_track_by_id(job.seed_track_id)
            seed_text = f"{seed_track.get('artist', 'Unknown')} - {seed_track.get('title', 'Unknown')}" if seed_track else f"Job {job_id}"
            
            # Build M3U content
            m3u_lines = [
                '#EXTM3U',
                f'# Sonic Traveller Playlist',
                f'# Generated from seed: {seed_text}',
                f'# Exported: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                f'# Total tracks: {len(job.results)}',
                f'# Threshold: {getattr(job, "threshold", "N/A")}',
                f'# Attempts: {job.attempts}',
                f'# Candidates processed: {job.total_candidates}',
                ''
            ]
            
            # Add tracks
            for i, track in enumerate(job.results, 1):
                # Get file path for local tracks
                db_path = os.path.join(DB_DIR, 'local_music.db')
                file_path = None
                if os.path.exists(db_path):
                    conn = sqlite3.connect(db_path)
                    try:
                        cur = conn.cursor()
                        cur.execute('SELECT file_path FROM tracks WHERE id = ?', (track['id'],))
                        row = cur.fetchone()
                        if row:
                            file_path = row[0]
                    finally:
                        conn.close()
                
                # Add track info
                distance_info = f" (distance: {track.get('distance', 'N/A')})" if track.get('distance') is not None else ""
                m3u_lines.append(f'#EXTINF:-1,{track["artist"]} - {track["title"]}{distance_info}')
                
                if file_path and os.path.exists(file_path):
                    # Use absolute file path for local files
                    m3u_lines.append(file_path)
                else:
                    # Fallback to track info if file not found
                    m3u_lines.append(f'# {track["artist"]} - {track["title"]} (file not found)')
            
            # Create filename
            if seed_track:
                artist = seed_track.get('artist', 'Unknown').replace('/', '_').replace('\\', '_')
                title = seed_track.get('title', 'Unknown').replace('/', '_').replace('\\', '_')
                filename = f"sonic_traveller_{artist}_{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.m3u"
            else:
                filename = f"sonic_traveller_job_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.m3u"
            
            # Return M3U response with download headers
            m3u_content = '\n'.join(m3u_lines)
            response = Response(m3u_content, mimetype='audio/x-mpegurl')
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
    except Exception as e:
        debug_log(f"Sonic export M3U error: {e}", 'ERROR')
        return jsonify({'success': False, 'error': 'Internal error'}), 500

# --- Sonic Traveller Music Service Integration ---

@main_bp.route('/api/sonic/save-to-navidrome', methods=['POST'])
def api_save_sonic_to_navidrome():
    """Save Sonic Traveller playlist to Navidrome"""
    try:
        data = request.get_json() or {}
        job_id = data.get('job_id')
        playlist_name = data.get('playlist_name', '').strip()
        
        if not job_id:
            return jsonify({'success': False, 'error': 'job_id required'}), 400
            
        # Check if Navidrome is enabled
        if get_config_value('APP', 'EnableNavidrome', 'no').lower() != 'yes':
            return jsonify({'success': False, 'error': 'Navidrome is not enabled'}), 400
            
        # Get Navidrome configuration
        navidrome_url = get_config_value('NAVIDROME', 'URL', '')
        navidrome_username = get_config_value('NAVIDROME', 'Username', '')
        navidrome_password = get_config_value('NAVIDROME', 'Password', '')
        
        if not all([navidrome_url, navidrome_username, navidrome_password]):
            return jsonify({'success': False, 'error': 'Navidrome configuration incomplete'}), 400
            
        # Get the Sonic Traveller job
        with _sonic_job_lock:
            job = _sonic_jobs.get(job_id)
            if not job:
                return jsonify({'success': False, 'error': 'Job not found'}), 404
                
            if job.status not in ['completed', 'stopped']:
                return jsonify({'success': False, 'error': 'Job not completed'}), 400
                
            if not job.results:
                return jsonify({'success': False, 'error': 'No tracks to save'}), 400
        
        # Generate playlist name if not provided
        if not playlist_name:
            seed_track = _get_track_by_id(job.seed_track_id)
            if seed_track:
                artist = seed_track.get('artist', 'Unknown')
                title = seed_track.get('title', 'Unknown')
                playlist_name = f"Sonic Traveller: {artist} - {title} ({datetime.now().strftime('%Y-%m-%d')})"
            else:
                playlist_name = f"Sonic Traveller Playlist ({datetime.now().strftime('%Y-%m-%d')})"
        
        # Map local tracks to Navidrome tracks
        navidrome_track_ids = []
        mapping_results = {
            'found': [],
            'not_found': [],
            'total_processed': len(job.results)
        }
        
        for track in job.results:
            # Try multiple search strategies for better matching
            search_strategies = []
            
            # Strategy 1: Direct filename search (most accurate for same NFS share)
            try:
                # Get the file path from the database
                with sqlite3.connect('db/local_music.db') as conn:
                    cur = conn.cursor()
                    cur.execute('SELECT file_path FROM tracks WHERE id = ?', (track['id'],))
                    result = cur.fetchone()
                    if result and result[0]:
                        file_path = result[0]
                        # Extract just the filename (without path)
                        filename = os.path.basename(file_path)
                        # Remove file extension
                        filename_without_ext = os.path.splitext(filename)[0]
                        if filename_without_ext:
                            search_strategies.append(('filename', filename_without_ext))
                            debug_log(f"Added filename search strategy: {filename_without_ext}", 'DEBUG')
            except Exception as e:
                debug_log(f"Failed to get file path for track {track['id']}: {e}", 'WARN')
            
            # Add other search strategies
            search_strategies.extend([
                ('artist_title', f"{track['artist']} {track['title']}"),  # Artist first (often better)
                ('title_only', track['title']),  # Title only
                ('artist_only', track['artist']),  # Artist only
                ('title_artist', f"{track['title']} {track['artist']}"),  # Title first (original strategy)
            ])
            
            navidrome_tracks = []
            used_strategy = None
            
            for strategy_type, strategy_query in search_strategies:
                if not strategy_query or not strategy_query.strip(): continue
                try:
                    navidrome_tracks = search_track_in_navidrome(strategy_query, navidrome_url, navidrome_username, navidrome_password)
                    if navidrome_tracks:
                        used_strategy = f"{strategy_type}: {strategy_query}"
                        debug_log(f"Found match using strategy: {used_strategy}", 'DEBUG')
                        break
                except Exception as e:
                    debug_log(f"Search strategy '{strategy_type}: {strategy_query}' failed: {e}", 'WARN')
                    continue
            
            if navidrome_tracks:
                # Use the first (best) match
                best_match = navidrome_tracks[0]
                navidrome_track_ids.append(best_match['id'])
                mapping_results['found'].append({
                    'local': {'title': track['title'], 'artist': track['artist']},
                    'navidrome': {'id': best_match['id'], 'title': best_match['title'], 'artist': best_match['artist']},
                    'search_strategy': used_strategy
                })
            else:
                mapping_results['not_found'].append({
                    'title': track['title'],
                    'artist': track['artist']
                })
        
        if not navidrome_track_ids:
            return jsonify({
                'success': False, 
                'error': 'No tracks could be found in Navidrome',
                'mapping_results': mapping_results
            }), 400
        
        # Create playlist in Navidrome
        playlist_id = create_playlist_in_navidrome(
            navidrome_url, navidrome_username, navidrome_password, 
            playlist_name, navidrome_track_ids
        )
        
        if playlist_id:
            # Update local history with Navidrome creation results
            _update_sonic_history_with_service_results(job_id, 'navidrome', {
                'playlist_id': playlist_id,
                'playlist_name': playlist_name,
                'tracks_added': len(navidrome_track_ids),
                'mapping_results': mapping_results
            })
            
            return jsonify({
                'success': True,
                'message': f'Playlist "{playlist_name}" created in Navidrome with {len(navidrome_track_ids)} tracks',
                'playlist_id': playlist_id,
                'playlist_name': playlist_name,
                'tracks_added': len(navidrome_track_ids),
                'mapping_results': mapping_results
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create playlist in Navidrome',
                'mapping_results': mapping_results
            }), 500
            
    except Exception as e:
        debug_log(f"Error saving Sonic Traveller to Navidrome: {e}", 'ERROR')
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/sonic/save-to-plex', methods=['POST'])
def api_save_sonic_to_plex():
    """Save Sonic Traveller playlist to Plex"""
    try:
        data = request.get_json() or {}
        job_id = data.get('job_id')
        playlist_name = data.get('playlist_name', '').strip()
        
        if not job_id:
            return jsonify({'success': False, 'error': 'job_id required'}), 400
            
        # Check if Plex is enabled
        if get_config_value('APP', 'EnablePlex', 'no').lower() != 'yes':
            return jsonify({'success': False, 'error': 'Plex is not enabled'}), 400
            
        # Get Plex configuration
        plex_server_url = get_config_value('PLEX', 'ServerURL', '')
        plex_token = get_config_value('PLEX', 'Token', '')
        plex_machine_id = get_config_value('PLEX', 'MachineID', '')
        plex_music_section_id = get_config_value('PLEX', 'MusicSectionID', '')
        
        if not all([plex_server_url, plex_token, plex_machine_id, plex_music_section_id]):
            return jsonify({'success': False, 'error': 'Plex configuration incomplete'}), 400
            
        # Get the Sonic Traveller job
        with _sonic_job_lock:
            job = _sonic_jobs.get(job_id)
            if not job:
                return jsonify({'success': False, 'error': 'Job not found'}), 404
                
            if job.status not in ['completed', 'stopped']:
                return jsonify({'success': False, 'error': 'Job not completed'}), 400
                
            if not job.results:
                return jsonify({'success': False, 'error': 'No tracks to save'}), 400
        
        # Generate playlist name if not provided
        if not playlist_name:
            seed_track = _get_track_by_id(job.seed_track_id)
            if seed_track:
                artist = seed_track.get('artist', 'Unknown')
                title = seed_track.get('title', 'Unknown')
                playlist_name = f"Sonic Traveller: {artist} - {title} ({datetime.now().strftime('%Y-%m-%d')})"
            else:
                playlist_name = f"Sonic Traveller Playlist ({datetime.now().strftime('%Y-%m-%d')})"
        
        # Map local tracks to Plex tracks
        plex_track_ids = []
        mapping_results = {
            'found': [],
            'not_found': [],
            'total_processed': len(job.results)
        }
        
        for track in job.results:
            # Try multiple search strategies for better matching
            search_strategies = []
            
            # Strategy 1: Direct filename search (most accurate for same NFS share)
            try:
                # Get the file path from the database
                with sqlite3.connect('db/local_music.db') as conn:
                    cur = conn.cursor()
                    cur.execute('SELECT file_path FROM tracks WHERE id = ?', (track['id'],))
                    result = cur.fetchone()
                    if result and result[0]:
                        file_path = result[0]
                        # Extract just the filename (without path)
                        filename = os.path.basename(file_path)
                        # Remove file extension
                        filename_without_ext = os.path.splitext(filename)[0]
                        if filename_without_ext:
                            search_strategies.append(('filename', filename_without_ext, None))
                            debug_log(f"Added filename search strategy: {filename_without_ext}", 'DEBUG')
            except Exception as e:
                debug_log(f"Failed to get file path for track {track['id']}: {e}", 'WARN')
            
            # Add other search strategies
            search_strategies.extend([
                ('full_info', track['title'], track['artist'], track.get('album')),  # Full info
                ('no_album', track['title'], track['artist'], None),  # No album
                ('title_only', track['title'], None, None),  # Title only
                ('artist_only', None, track['artist'], None),  # Artist only
            ])
            
            plex_track = None
            used_strategy = None
            
            for strategy_type, title, artist, album in search_strategies:
                if not title and not artist: continue
                try:
                    plex_track = search_track_in_plex(
                        plex_server_url, plex_token,
                        title or '', artist or '', album,
                        plex_music_section_id
                    )
                    if plex_track:
                        used_strategy = f"{strategy_type}: Title: {title or 'N/A'}, Artist: {artist or 'N/A'}"
                        debug_log(f"Found match using strategy: {used_strategy}", 'DEBUG')
                        break
                except Exception as e:
                    debug_log(f"Plex search strategy failed: {e}", 'WARN')
                    continue
            
            if plex_track:
                plex_track_ids.append(plex_track['id'])
                mapping_results['found'].append({
                    'local': {'title': track['title'], 'artist': track['artist']},
                    'plex': {'id': plex_track['id'], 'title': plex_track['title'], 'artist': plex_track['artist']},
                    'search_strategy': used_strategy
                })
            else:
                mapping_results['not_found'].append({
                    'title': track['title'],
                    'artist': track['artist']
                })
        
        if not plex_track_ids:
            return jsonify({
                'success': False, 
                'error': 'No tracks could be found in Plex',
                'mapping_results': mapping_results
            }), 400
        
        # Create playlist in Plex
        playlist_id, tracks_added = create_playlist_in_plex(
            playlist_name, plex_track_ids, plex_server_url, plex_token, plex_machine_id
        )
        
        if playlist_id:
            # Update local history with Plex creation results
            _update_sonic_history_with_service_results(job_id, 'plex', {
                'playlist_id': playlist_id,
                'playlist_name': playlist_name,
                'tracks_added': tracks_added,
                'mapping_results': mapping_results
            })
            
            return jsonify({
                'success': True,
                'message': f'Playlist "{playlist_name}" created in Plex with {tracks_added} tracks',
                'playlist_id': playlist_id,
                'playlist_name': playlist_name,
                'tracks_added': tracks_added,
                'mapping_results': mapping_results
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create playlist in Plex',
                'mapping_results': mapping_results
            }), 500
            
    except Exception as e:
        debug_log(f"Error saving Sonic Traveller to Plex: {e}", 'ERROR')
        return jsonify({'success': False, 'error': str(e)}), 500

def _update_sonic_history_with_service_results(job_id, service_name, results):
    """Update Sonic Traveller history with service creation results"""
    try:
        # Load current history
        history = load_playlist_history()
        
        # Find the Sonic Traveller entry
        for entry in history:
            if entry.get('id') == f"sonic_{job_id}":
                # Initialize service results if not present
                if 'service_results' not in entry['metadata']:
                    entry['metadata']['service_results'] = {}
                
                # Update with new service results
                entry['metadata']['service_results'][service_name] = {
                    'created_at': datetime.now().isoformat(),
                    'playlist_id': results['playlist_id'],
                    'playlist_name': results['playlist_name'],
                    'tracks_added': results['tracks_added'],
                    'mapping_results': results['mapping_results']
                }
                
                # Save updated history
                save_playlist_history(history)
                debug_log(f"Updated Sonic Traveller history with {service_name} results for job {job_id}", 'INFO')
                break
                
    except Exception as e:
        debug_log(f"Error updating Sonic Traveller history with {service_name} results: {e}", 'ERROR')

@main_bp.route('/api/sonic/service-config')
def api_sonic_service_config():
    """Get service configuration for Sonic Traveller"""
    try:
        return jsonify({
            'success': True,
            'navidrome_enabled': get_config_value('APP', 'EnableNavidrome', 'no').lower() == 'yes',
            'plex_enabled': get_config_value('APP', 'EnablePlex', 'no').lower() == 'yes'
        })
    except Exception as e:
        debug_log(f"Error getting service config: {e}", 'ERROR')
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/history/save-to-navidrome', methods=['POST'])
def api_save_history_to_navidrome():
    """Save History playlist to Navidrome"""
    try:
        data = request.get_json() or {}
        playlist_name = data.get('playlist_name', '').strip()
        tracks = data.get('tracks', [])
        
        if not tracks:
            return jsonify({'success': False, 'error': 'No tracks provided'}), 400
            
        # Check if Navidrome is enabled
        if get_config_value('APP', 'EnableNavidrome', 'no').lower() != 'yes':
            return jsonify({'success': False, 'error': 'Navidrome is not enabled'}), 400
            
        # Get Navidrome configuration
        navidrome_url = get_config_value('NAVIDROME', 'URL', '')
        navidrome_username = get_config_value('NAVIDROME', 'Username', '')
        navidrome_password = get_config_value('NAVIDROME', 'Password', '')
        
        if not all([navidrome_url, navidrome_username, navidrome_password]):
            return jsonify({'success': False, 'error': 'Navidrome configuration incomplete'}), 400
        
        # Map tracks to Navidrome tracks
        navidrome_track_ids = []
        mapping_results = {
            'found': [],
            'not_found': [],
            'total_processed': len(tracks)
        }
        
        for track in tracks:
            # Try multiple search strategies for better matching
            search_strategies = [
                f"{track.get('artist', '')} {track.get('title', '')}",  # Artist first (often better)
                track.get('title', ''),  # Title only
                track.get('artist', ''),  # Artist only
                f"{track.get('title', '')} {track.get('artist', '')}",  # Title first (original strategy)
            ]
            
            navidrome_tracks = []
            used_strategy = None
            
            for strategy in search_strategies:
                if not strategy.strip():
                    continue
                    
                try:
                    navidrome_tracks = search_track_in_navidrome(strategy, navidrome_url, navidrome_username, navidrome_password)
                    if navidrome_tracks:
                        used_strategy = strategy
                        break
                except Exception as e:
                    debug_log(f"Search strategy '{strategy}' failed: {e}", 'WARN')
                    continue
            
            if navidrome_tracks:
                # Use the first (best) match
                best_match = navidrome_tracks[0]
                navidrome_track_ids.append(best_match['id'])
                mapping_results['found'].append({
                    'local': {'title': track.get('title', ''), 'artist': track.get('artist', '')},
                    'navidrome': {'id': best_match['id'], 'title': best_match['title'], 'artist': best_match['artist']},
                    'search_strategy': used_strategy
                })
            else:
                mapping_results['not_found'].append({
                    'title': track.get('title', ''),
                    'artist': track.get('artist', '')
                })
        
        if not navidrome_track_ids:
            return jsonify({
                'success': False, 
                'error': 'No tracks could be found in Navidrome',
                'mapping_results': mapping_results
            }), 400
        
        # Create playlist in Navidrome
        playlist_id = create_playlist_in_navidrome(
            navidrome_url, navidrome_username, navidrome_password, 
            playlist_name, navidrome_track_ids
        )
        
        if playlist_id:
            return jsonify({
                'success': True,
                'message': f'Playlist "{playlist_name}" created in Navidrome with {len(navidrome_track_ids)} tracks',
                'playlist_id': playlist_id,
                'playlist_name': playlist_name,
                'tracks_added': len(navidrome_track_ids),
                'mapping_results': mapping_results
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create playlist in Navidrome',
                'mapping_results': mapping_results
            }), 500
            
    except Exception as e:
        debug_log(f"Error saving History playlist to Navidrome: {e}", 'ERROR')
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/history/save-to-plex', methods=['POST'])
def api_save_history_to_plex():
    """Save History playlist to Plex"""
    try:
        data = request.get_json() or {}
        playlist_name = data.get('playlist_name', '').strip()
        tracks = data.get('tracks', [])
        
        if not tracks:
            return jsonify({'success': False, 'error': 'No tracks provided'}), 400
            
        # Check if Plex is enabled
        if get_config_value('APP', 'EnablePlex', 'no').lower() != 'yes':
            return jsonify({'success': False, 'error': 'Plex is not enabled'}), 400
            
        # Get Plex configuration
        plex_server_url = get_config_value('PLEX', 'ServerURL', '')
        plex_token = get_config_value('PLEX', 'Token', '')
        plex_machine_id = get_config_value('PLEX', 'MachineID', '')
        plex_music_section_id = get_config_value('PLEX', 'MusicSectionID', '')
        
        if not all([plex_server_url, plex_token, plex_machine_id, plex_music_section_id]):
            return jsonify({'success': False, 'error': 'Plex configuration incomplete'}), 400
        
        # Map tracks to Plex tracks
        plex_track_ids = []
        mapping_results = {
            'found': [],
            'not_found': [],
            'total_processed': len(tracks)
        }
        
        for track in tracks:
            # Try multiple search strategies for better matching
            search_strategies = [
                (track.get('title', ''), track.get('artist', ''), track.get('album')),  # Full info
                (track.get('title', ''), track.get('artist', ''), None),  # No album
                (track.get('title', ''), None, None),  # Title only
                (None, track.get('artist', ''), None),  # Artist only
            ]
            
            plex_track = None
            used_strategy = None
            
            for title, artist, album in search_strategies:
                if not title and not artist:
                    continue
                    
                try:
                    plex_track = search_track_in_plex(
                        plex_server_url, plex_token, 
                        title or '', artist or '', album, 
                        plex_music_section_id
                    )
                    if plex_track:
                        used_strategy = f"Title: {title or 'N/A'}, Artist: {artist or 'N/A'}"
                        break
                except Exception as e:
                    debug_log(f"Plex search strategy failed: {e}", 'WARN')
                    continue
            
            if plex_track:
                plex_track_ids.append(plex_track['id'])
                mapping_results['found'].append({
                    'local': {'title': track.get('title', ''), 'artist': track.get('artist', '')},
                    'plex': {'id': plex_track['id'], 'title': plex_track['title'], 'artist': plex_track['artist']},
                    'search_strategy': used_strategy
                })
            else:
                mapping_results['not_found'].append({
                    'title': track.get('title', ''),
                    'artist': track.get('artist', '')
                })
        
        if not plex_track_ids:
            return jsonify({
                'success': False, 
                'error': 'No tracks could be found in Plex',
                'mapping_results': mapping_results
            }), 400
        
        # Create playlist in Plex
        playlist_id, tracks_added = create_playlist_in_plex(
            playlist_name, plex_track_ids, plex_server_url, plex_token, plex_machine_id
        )
        
        if playlist_id:
            return jsonify({
                'success': True,
                'message': f'Playlist "{playlist_name}" created in Plex with {tracks_added} tracks',
                'playlist_id': playlist_id,
                'playlist_name': playlist_name,
                'tracks_added': tracks_added,
                'mapping_results': mapping_results
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create playlist in Plex',
                'mapping_results': mapping_results
            }), 500
            
    except Exception as e:
        debug_log(f"Error saving History playlist to Plex: {e}", 'ERROR')
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/audio-analysis/problematic-files')
def api_get_problematic_files():
    """Get detailed report of problematic files causing stalls."""
    try:
        monitor = get_audio_analysis_monitor()
        if not monitor:
            return jsonify({'error': 'Audio analysis monitoring not available'}), 500
        
        report = monitor.get_problematic_files_report()
        return jsonify(report)
        
    except Exception as e:
        logger.error(f"Error getting problematic files report: {e}")
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/audio-analysis/force-skip', methods=['POST'])
def api_force_skip_file():
    """Force skip a problematic file to prevent stalls."""
    try:
        data = request.get_json()
        if not data or 'file_path' not in data:
            return jsonify({'error': 'file_path is required'}), 400
        
        file_path = data['file_path']
        reason = data.get('reason', 'Manually skipped to prevent stall')
        
        # Get the audio analysis service
        from audio_analysis_service import AudioAnalysisService
        service = AudioAnalysisService()
        
        # Find the track by file path
        track_id = service.get_track_id_by_file_path(file_path)
        if not track_id:
            return jsonify({'error': f'Track not found for file: {file_path}'}), 404
        
        # Update status to skipped
        if service.update_analysis_status(track_id, 'skipped', reason):
            logger.info(f"Force skipped file {file_path} with reason: {reason}")
            return jsonify({'success': True, 'message': f'File {os.path.basename(file_path)} skipped successfully'})
        else:
            return jsonify({'error': 'Failed to update track status'}), 500
        
    except Exception as e:
        logger.error(f"Error force skipping file: {e}")
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/audio-analysis/force-reset', methods=['POST'])
def api_force_reset_file():
    """Force reset a stuck file back to pending status."""
    try:
        data = request.get_json()
        if not data or 'file_path' not in data:
            return jsonify({'error': 'file_path is required'}), 400
        
        file_path = data['file_path']
        reason = data.get('reason', 'Manually reset from stuck state')
        
        # Get the audio analysis service
        from audio_analysis_service import AudioAnalysisService
        service = AudioAnalysisService()
        
        # Find the track by file path
        track_id = service.get_track_id_by_file_path(file_path)
        if not track_id:
            return jsonify({'error': f'Track not found for file: {file_path}'}), 404
        
        # Update status back to pending
        if service.update_analysis_status(track_id, 'pending', reason):
            logger.info(f"Force reset file {file_path} with reason: {reason}")
            return jsonify({'success': True, 'message': f'File {os.path.basename(file_path)} reset to pending successfully'})
        else:
            return jsonify({'error': 'Failed to update track status'}), 500
        
    except Exception as e:
        logger.error(f"Error force resetting file: {e}")
        return jsonify({'error': str(e)}), 500
