import sqlite3
import math
import os
import logging
from logging.handlers import RotatingFileHandler
import requests
import configparser
import json
from typing import List, Dict, Optional, Any
from mcp.server.fastmcp import FastMCP
import sonic_similarity
import feature_store

# Configure logging
# Set up logging with separate handlers for file and console
# File handler: INFO level for detailed logs to disk
# Console handler: WARNING level to reduce output to LLM agent
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Remove any existing handlers to avoid duplicates
logger.handlers.clear()

# File handler for detailed logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'mcp_server.log')

# Check if log file exists and fix permissions if needed
if os.path.exists(log_file):
    try:
        # Try to open in append mode to check permissions
        with open(log_file, 'a'):
            pass
    except PermissionError:
        # If we can't write, remove the file so it can be recreated with correct permissions
        try:
            os.remove(log_file)
        except Exception:
            pass  # If we can't remove it, RotatingFileHandler will handle it

file_handler = RotatingFileHandler(
    log_file,
    maxBytes=5*1024*1024,  # 5 MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Console handler for minimal output (only WARNING and above)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_formatter = logging.Formatter('%(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# Prevent propagation to root logger to avoid duplicate output
logger.propagate = False

# Initialize FastMCP server
mcp = FastMCP("TuneForge", debug=False)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db', 'local_music.db')

def get_db_connection():
    """Get a connection to the local music database."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@mcp.tool()
def find_similar_songs(song_title: str, artist_name: str = None, limit: int = 5) -> str:
    """
    Find similar songs based on audio features.
    
    Args:
        song_title: The title of the song to find similarities for.
        artist_name: Optional artist name to narrow down the search.
        limit: The maximum number of similar songs to return (default: 5).
        
    Returns:
        A formatted string containing the list of similar songs and their similarity scores.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Find the seed track
        query = "SELECT id, title, artist, file_path FROM tracks WHERE title LIKE ?"
        params = [f"%{song_title}%"]
        
        if artist_name:
            query += " AND artist LIKE ?"
            params.append(f"%{artist_name}%")
            
        cursor.execute(query, params)
        tracks = cursor.fetchall()
        
        if not tracks:
            return f"No tracks found matching title '{song_title}'" + (f" and artist '{artist_name}'" if artist_name else "")
            
        # If multiple matches, pick the first one (or could ask for clarification, but for tool simplicity we pick first)
        seed_track = tracks[0]
        seed_id = seed_track['id']
        
        # 2. Get features for seed track
        seed_features = feature_store.fetch_track_features(DB_PATH, seed_id)
        if not seed_features:
            return f"No audio features found for track '{seed_track['title']}' (ID: {seed_id}). Please analyze it first."
            
        # 3. Get stats for normalization
        stats = sonic_similarity.get_feature_stats(DB_PATH)
        seed_vector = sonic_similarity.build_vector(seed_features, stats)
        
        # 4. Get all other tracks with features
        # Optimization: In a real large DB, we wouldn't fetch ALL. We might use a vector DB or pre-cluster.
        # For this local DB, we'll fetch IDs that have features.
        cursor.execute("SELECT track_id FROM audio_features WHERE track_id != ?", (seed_id,))
        candidate_ids = [row['track_id'] for row in cursor.fetchall()]
        
        if not candidate_ids:
            return "No other tracks with audio features found in the database."
            
        # 5. Calculate similarities
        # Fetch features for candidates in batches could be better, but fetch_batch_features exists
        candidate_features_map = feature_store.fetch_batch_features(DB_PATH, candidate_ids)
        
        similarities = []
        for cid, features in candidate_features_map.items():
            cand_vector = sonic_similarity.build_vector(features, stats)
            distance = sonic_similarity.compute_distance(seed_vector, cand_vector)
            # Convert distance to similarity score (0 to 1)
            # Assuming max distance is roughly sqrt(len(features)) since features are 0-1.
            # 8 features -> max dist sqrt(8) ~= 2.82
            similarity = max(0.0, 1.0 - (distance / 2.82)) 
            similarities.append((cid, similarity))
            
        # Sort by similarity desc
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_matches = similarities[:limit]
        
        # 6. Fetch details for top matches
        results = []
        results.append(f"Similar songs to: **{seed_track['title']}** by **{seed_track['artist']}**")
        results.append("")
        
        for tid, score in top_matches:
            cursor.execute("SELECT title, artist FROM tracks WHERE id = ?", (tid,))
            track = cursor.fetchone()
            if track:
                results.append(f"- **{track['title']}** by {track['artist']} (Similarity: {score:.2%})")
                
        conn.close()
        return "\n".join(results)
        
    except Exception as e:
        logger.error(f"Error finding similar songs: {e}")
        return f"Error processing request: {str(e)}"

# --- Playlist Management Tools ---

def _search_navidrome_tracks(query: str, limit: int) -> List[Dict[str, Any]]:
    """
    Helper function to search for tracks in Navidrome.
    
    Args:
        query: The search query
        limit: Maximum number of results to return
        
    Returns:
        List of track dictionaries with 'id', 'title', 'artist', 'album' keys.
        Returns empty list on error.
    """
    url = get_config_value('NAVIDROME', 'URL')
    user = get_config_value('NAVIDROME', 'Username')
    password = get_config_value('NAVIDROME', 'Password')
    
    if not all([url, user, password]):
        return []
        
    try:
        base_url = url.rstrip('/')
        if '/rest' not in base_url: base_url = f"{base_url}/rest"
        
        params = {
            'u': user, 'p': password, 'v': '1.16.1', 'c': 'TuneForge', 'f': 'json',
            'query': query, 'songCount': limit
        }
        
        response = requests.get(f"{base_url}/search3.view", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('subsonic-response', {}).get('status') == 'ok':
            songs = data.get('subsonic-response', {}).get('searchResult3', {}).get('song', [])
            results = []
            for song in songs:
                results.append({
                    'id': song.get('id'),
                    'title': song.get('title'),
                    'artist': song.get('artist'),
                    'album': song.get('album')
                })
            return results
        else:
            logger.warning(f"Navidrome search error for '{query}': {data.get('subsonic-response', {}).get('error', {}).get('message')}")
            return []
            
    except Exception as e:
        logger.error(f"Error searching Navidrome for '{query}': {str(e)}")
        return []

def _search_plex_tracks(query: str, limit: int) -> List[Dict[str, Any]]:
    """
    Helper function to search for tracks in Plex.
    
    Args:
        query: The search query
        limit: Maximum number of results to return
        
    Returns:
        List of track dictionaries with 'id', 'title', 'artist', 'album' keys.
        Returns empty list on error.
    """
    url = get_config_value('PLEX', 'ServerURL')
    token = get_config_value('PLEX', 'Token')
    section_id = get_config_value('PLEX', 'MusicSectionID')
    
    if not all([url, token, section_id]):
        return []
        
    try:
        headers = {'X-Plex-Token': token, 'Accept': 'application/json'}
        metadata = []
        all_url = f"{url.rstrip('/')}/library/sections/{section_id}/all"
        search_url = f"{url.rstrip('/')}/library/sections/{section_id}/search"
        query_lower = query.lower().strip()
        
        # Strategy 1: Try genre filtering if the query looks like a genre
        genre_keywords = ['rock', 'pop', 'jazz', 'classical', 'electronic', 'hip hop', 'rap', 'country', 
                        'blues', 'folk', 'metal', 'punk', 'reggae', 'r&b', 'soul', 'funk', 'disco',
                        'techno', 'house', 'trance', 'dubstep', 'indie', 'alternative', 'grunge']
        
        might_be_genre = any(keyword in query_lower for keyword in genre_keywords) or len(query.split()) <= 2
        
        if might_be_genre:
            try:
                genre_params = {'type': '10', 'genre.tag': query, 'X-Plex-Token': token}
                response = requests.get(all_url, headers=headers, params=genre_params, timeout=10)
                response.raise_for_status()
                data = response.json()
                genre_tracks = data.get('MediaContainer', {}).get('Metadata', [])
                if genre_tracks:
                    metadata.extend(genre_tracks)
            except Exception as e:
                logger.debug(f"Plex: Genre filter failed for '{query}': {e}")
                pass
        
        # Strategy 2: Try to find the artist first, then get all their tracks
        if not metadata or len(metadata) < limit:
            artist_params = {'type': '8', 'query': query, 'X-Plex-Token': token}
            
            try:
                response = requests.get(search_url, headers=headers, params=artist_params, timeout=10)
                response.raise_for_status()
                data = response.json()
                artist_results = data.get('MediaContainer', {}).get('Metadata', [])
                
                matching_artist = None
                for artist in artist_results:
                    artist_title = artist.get('title', '').lower()
                    if artist_title == query_lower or query_lower in artist_title or artist_title in query_lower:
                        matching_artist = artist
                        break
                
                if matching_artist:
                    artist_id = matching_artist.get('ratingKey')
                    track_params = {'type': '10', 'artist.id': artist_id, 'X-Plex-Token': token}
                    
                    try:
                        response = requests.get(all_url, headers=headers, params=track_params, timeout=10)
                        response.raise_for_status()
                        data = response.json()
                        artist_tracks = data.get('MediaContainer', {}).get('Metadata', [])
                        if artist_tracks:
                            existing_ids = {track.get('ratingKey') for track in metadata}
                            for track in artist_tracks:
                                if track.get('ratingKey') not in existing_ids:
                                    metadata.append(track)
                    except Exception as e:
                        logger.debug(f"Plex: Failed to get tracks for artist: {e}")
                        pass
            except Exception as e:
                logger.debug(f"Plex: Artist search failed: {e}")
                pass
        
        # Strategy 3: General text search
        if not metadata or len(metadata) < limit:
            track_params = {'type': '10', 'query': query, 'X-Plex-Token': token}
            
            try:
                response = requests.get(search_url, headers=headers, params=track_params, timeout=10)
                response.raise_for_status()
                data = response.json()
                general_metadata = data.get('MediaContainer', {}).get('Metadata', [])
                
                existing_ids = {track.get('ratingKey') for track in metadata}
                exact_matches = []
                artist_matches = []
                title_matches = []
                other_matches = []
                
                for track in general_metadata:
                    track_id = track.get('ratingKey')
                    if track_id in existing_ids:
                        continue
                    
                    title = track.get('title', '').lower()
                    artist = track.get('grandparentTitle', '').lower()
                    
                    if query_lower == title or query_lower == artist:
                        exact_matches.append(track)
                    elif artist and query_lower in artist:
                        artist_matches.append(track)
                    elif title and query_lower in title:
                        title_matches.append(track)
                    else:
                        other_matches.append(track)
                
                metadata = metadata + exact_matches + artist_matches + title_matches + other_matches
            except Exception as e:
                logger.debug(f"Plex: General search failed: {e}")
                pass
        
        results = []
        if metadata:
            for track in metadata[:limit]:
                results.append({
                    'id': track.get('ratingKey'),
                    'title': track.get('title'),
                    'artist': track.get('grandparentTitle'),
                    'album': track.get('parentTitle')
                })
        return results
        
    except Exception as e:
        logger.error(f"Plex search error for '{query}': {e}")
        return []

def get_config_value(section, key, default=None):
    """Helper to read config.ini"""
    config = configparser.ConfigParser()
    config.optionxform = lambda optionstr: optionstr
    # Use absolute path to ensure we always find config.ini
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'config.ini')
    
    if not os.path.exists(config_path):
        logger.warning(f"Config file not found at {config_path}")
        return default
        
    try:
        config.read(config_path)
        if config.has_section(section):
            if key in config[section]:
                return config[section][key]
            else:
                logger.debug(f"Key '{key}' not found in section '{section}'")
        else:
            logger.debug(f"Section '{section}' not found in config")
    except Exception as e:
        logger.error(f"Error reading config: {e}")
        
    return default

@mcp.tool()
def search_tracks(query: str, platform: str = "plex", limit: int = 20) -> str:
    """
    Search for tracks in the user's Plex or Navidrome library by title, artist, genre, tags, or any text query.
    
    CRITICAL: All results returned by this function are tracks that EXIST in the user's library. 
    These are REAL tracks that can be immediately added to playlists. Never question whether 
    these results are valid - they are confirmed library tracks.
    
    This function supports flexible searching:
    - Artist names (e.g., "The Beatles", "Oasis")
    - Song titles (e.g., "Stairway to Heaven", "Wonderwall")
    - Genres (e.g., "classic rock", "jazz", "electronic")
    - Tags or keywords (e.g., "80s", "acoustic", "live")
    - Any combination of the above
    
    Args:
        query: The search query - can be a title, artist, genre, tag, or any text
        platform: "plex" or "navidrome"
        limit: Maximum number of results to return (default: 20, max: 50)
        
    Returns:
        JSON string containing list of found tracks WITH VALID TRACK IDs from the user's library.
        These track IDs can be immediately used with add_to_playlist. All results are confirmed 
        to exist in the user's Plex or Navidrome library.
    """
    # Enforce reasonable limits
    limit = min(max(1, limit), 50)
    platform = platform.lower()
    
    if platform == "navidrome":
        url = get_config_value('NAVIDROME', 'URL')
        user = get_config_value('NAVIDROME', 'Username')
        password = get_config_value('NAVIDROME', 'Password')
        
        if not all([url, user, password]):
            return "Error: Navidrome not configured."
        
        results = _search_navidrome_tracks(query, limit)
        if results:
            return json.dumps(results, indent=2)
        else:
            return "Error: No results found or search failed."

    elif platform == "plex":
        url = get_config_value('PLEX', 'ServerURL')
        token = get_config_value('PLEX', 'Token')
        section_id = get_config_value('PLEX', 'MusicSectionID')
        
        if not all([url, token, section_id]):
            return "Error: Plex not configured (URL, Token, or MusicSectionID missing)."
        
        results = _search_plex_tracks(query, limit)
        if results:
            return json.dumps(results, indent=2)
        else:
            return "Error: No results found or search failed."
            
    else:
        return "Error: Unsupported platform. Use 'plex' or 'navidrome'."

@mcp.tool()
def bulk_search_tracks(queries: List[str], platform: str = "plex", limit: int = 50) -> str:
    """
    Search for multiple tracks in a single call across Plex or Navidrome libraries.
    
    CRITICAL: All results returned by this function are tracks that EXIST in the user's library. 
    These are REAL tracks that can be immediately added to playlists. Never question whether 
    these results are valid - they are confirmed library tracks.
    
    This function allows searching for multiple tracks (e.g., 10 queries) in a single MCP call,
    returning results grouped by query with track IDs for each match.
    
    Args:
        queries: List of search queries (e.g., ["Oasis", "Wonderwall", "The Beatles"])
        platform: "plex" or "navidrome" (default: "plex")
        limit: Total maximum number of results across all queries (default: 50, max: 200)
        
    Returns:
        JSON string containing results grouped by query:
        {
            "query1": [{"id": "...", "title": "...", "artist": "...", "album": "..."}, ...],
            "query2": [{"id": "...", "title": "...", "artist": "...", "album": "..."}, ...],
            ...
        }
        Each query's results contain track IDs that can be immediately used with add_to_playlist.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    # Validate inputs
    if not queries or not isinstance(queries, list) or len(queries) == 0:
        return json.dumps({"error": "No queries provided. Please provide a list of search queries."}, indent=2)
    
    # Enforce reasonable limits
    limit = min(max(1, limit), 200)
    platform = platform.lower()
    
    if platform not in ["plex", "navidrome"]:
        return json.dumps({"error": "Unsupported platform. Use 'plex' or 'navidrome'."}, indent=2)
    
    # Check platform configuration
    if platform == "navidrome":
        url = get_config_value('NAVIDROME', 'URL')
        user = get_config_value('NAVIDROME', 'Username')
        password = get_config_value('NAVIDROME', 'Password')
        if not all([url, user, password]):
            return json.dumps({"error": "Navidrome not configured."}, indent=2)
    else:  # plex
        url = get_config_value('PLEX', 'ServerURL')
        token = get_config_value('PLEX', 'Token')
        section_id = get_config_value('PLEX', 'MusicSectionID')
        if not all([url, token, section_id]):
            return json.dumps({"error": "Plex not configured (URL, Token, or MusicSectionID missing)."}, indent=2)
    
    # Calculate per-query limit (distribute total limit across queries)
    # Use equal distribution, but ensure each query can get at least 1 result
    num_queries = len(queries)
    per_query_limit = max(1, limit // num_queries)
    # Allow some queries to get more if we have remainder
    remainder = limit % num_queries
    
    # Execute searches concurrently
    results = {}
    errors = {}
    
    def search_single_query(query: str, query_limit: int) -> tuple:
        """Search a single query and return (query, results, error)"""
        try:
            if platform == "navidrome":
                tracks = _search_navidrome_tracks(query, query_limit)
            else:  # plex
                tracks = _search_plex_tracks(query, query_limit)
            return (query, tracks, None)
        except Exception as e:
            logger.error(f"Error searching '{query}' on {platform}: {e}")
            return (query, [], str(e))
    
    # Execute searches with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=min(10, num_queries)) as executor:
        # Submit all queries
        future_to_query = {}
        for i, query in enumerate(queries):
            # Distribute remainder to first queries
            query_limit = per_query_limit + (1 if i < remainder else 0)
            future = executor.submit(search_single_query, query, query_limit)
            future_to_query[future] = query
        
        # Collect results as they complete
        for future in as_completed(future_to_query):
            query, tracks, error = future.result()
            if error:
                errors[query] = error
                results[query] = []
            else:
                results[query] = tracks
    
    # Enforce total limit across all results
    total_results = sum(len(tracks) for tracks in results.values())
    if total_results > limit:
        # Trim results to respect total limit
        # Priority: keep results from queries that have fewer results first
        sorted_queries = sorted(results.items(), key=lambda x: len(x[1]))
        remaining_limit = limit
        
        trimmed_results = {}
        for query, tracks in sorted_queries:
            if remaining_limit <= 0:
                trimmed_results[query] = []
            elif len(tracks) <= remaining_limit:
                trimmed_results[query] = tracks
                remaining_limit -= len(tracks)
            else:
                trimmed_results[query] = tracks[:remaining_limit]
                remaining_limit = 0
        
        results = trimmed_results
    
    # Build response with results and any errors
    response = {"results": results}
    if errors:
        response["errors"] = errors
    
    return json.dumps(response, indent=2)

@mcp.tool()
def create_playlist(name: str, platform: str = "plex") -> str:
    """
    Create a new empty playlist.
    
    Args:
        name: Name of the playlist
        platform: "plex" or "navidrome"
        
    Returns:
        Status message with Playlist ID if successful.
    """
    platform = platform.lower()
    
    if platform == "navidrome":
        url = get_config_value('NAVIDROME', 'URL')
        user = get_config_value('NAVIDROME', 'Username')
        password = get_config_value('NAVIDROME', 'Password')
        
        if not all([url, user, password]):
            return "Error: Navidrome not configured."
            
        try:
            base_url = url.rstrip('/')
            if '/rest' not in base_url: base_url = f"{base_url}/rest"
            
            params = {
                'u': user, 'p': password, 'v': '1.16.1', 'c': 'TuneForge', 'f': 'json',
                'name': name
            }
            
            response = requests.get(f"{base_url}/createPlaylist.view", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('subsonic-response', {}).get('status') == 'ok':
                playlist = data['subsonic-response'].get('playlist', {})
                return f"Successfully created Navidrome playlist '{name}' with ID: {playlist.get('id')}"
            else:
                return f"Navidrome Error: {data.get('subsonic-response', {}).get('error', {}).get('message')}"
                
        except Exception as e:
            return f"Error creating Navidrome playlist: {str(e)}"

    elif platform == "plex":
        url = get_config_value('PLEX', 'ServerURL')
        token = get_config_value('PLEX', 'Token')
        machine_id = get_config_value('PLEX', 'MachineID')
        
        if not all([url, token, machine_id]):
            return "Error: Plex not configured (URL, Token, or MachineID missing)."
            
        return "Error: Plex requires at least one track ID to create a playlist. Use 'add_to_playlist' (which can create new ones if supported) or provide a track."
        
    else:
        return "Error: Unsupported platform."

@mcp.tool()
def add_to_playlist(playlist_id: str, track_ids: list[str], platform: str = "navidrome", playlist_name: str = "") -> str:
    """
    Add tracks to a playlist.
    
    IMPORTANT: You MUST use the 'search_tracks' tool with the same platform to get valid track IDs before calling this function.
    Track IDs from different platforms or services (e.g., Deezer IDs) are NOT compatible and will be rejected.
    - For Plex: Use search_tracks with platform='plex' to get Plex track IDs (typically 6-7 digit numbers).
    - For Navidrome: Use search_tracks with platform='navidrome' to get Navidrome track IDs (32-character hex strings).
    
    Args:
        playlist_id: The ID of the playlist to add to. Use "NEW" to create a new playlist.
        track_ids: A list of track IDs to add. MUST be obtained from search_tracks using the same platform.
        platform: The platform to use ("navidrome" or "plex").
        playlist_name: The name of the playlist (required if playlist_id is "NEW").
        
    Returns:
        Status message indicating success or failure. If tracks were not added, the message will indicate this.
    """
    import datetime
    def log_mcp(msg):
        try:
            with open('/opt/tuneforge/logs/mcp_debug.log', 'a') as f:
                f.write(f"{datetime.datetime.now()} - {msg}\n")
        except:
            pass

    log_mcp(f"add_to_playlist called with: playlist_id={playlist_id}, track_ids={track_ids}, platform={platform}, playlist_name={playlist_name}")

    if not track_ids:
        return "Error: No track IDs provided."
        
    platform = platform.lower()
    
    if platform == "navidrome":
        base_url = get_config_value('NAVIDROME', 'URL')
        user = get_config_value('NAVIDROME', 'Username')
        password = get_config_value('NAVIDROME', 'Password')
        
        log_mcp(f"Navidrome Config Check: URL={base_url}, Username={user}, Password={'[SET]' if password else '[NOT SET]'}")
        
        if not all([base_url, user, password]):
            missing = []
            if not base_url: missing.append('URL')
            if not user: missing.append('Username')
            if not password: missing.append('Password')
            log_mcp(f"Navidrome Config Missing: {', '.join(missing)}")
            return f"Error: Navidrome not configured. Missing: {', '.join(missing)}"
        
        # Validate track ID format: Navidrome uses hex strings (32 chars), Plex uses numeric
        # Check if track IDs look like Plex IDs (all numeric, typically 6 digits)
        invalid_ids = [tid for tid in track_ids if tid.isdigit() and len(tid) <= 8]
        if invalid_ids:
            log_mcp(f"Warning: Track IDs appear to be Plex format (numeric): {invalid_ids[:3]}")
            return f"Error: Invalid track IDs for Navidrome. These appear to be Plex track IDs (numeric format). Navidrome requires hex-format track IDs. Please search for tracks using platform='navidrome' to get valid Navidrome track IDs."
             
        params = {
            'u': user,
            'p': password,
            'v': '1.16.1',
            'c': 'TuneForge',
            'f': 'json'
        }
        
        try:
            base_url = base_url.rstrip('/')
            if '/rest' not in base_url: base_url = f"{base_url}/rest"

            if playlist_id == "NEW":
                if not playlist_name:
                    return "Error: playlist_name is required when creating a new Navidrome playlist."
                
                params['name'] = playlist_name
                params['songId'] = track_ids
                endpoint = "createPlaylist.view"
            else:
                # So for existing playlist, we should use updatePlaylist with songIdToAdd
                endpoint = "updatePlaylist.view"
                params['playlistId'] = playlist_id
                # params['songId'] = track_ids # This replaces?
                params['songIdToAdd'] = track_ids # This adds
                if 'songId' in params: del params['songId']
            
            log_mcp(f"Navidrome Request: {endpoint} with params {params}")
            response = requests.get(f"{base_url}/{endpoint}", params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            log_mcp(f"Navidrome Response: {data}")
            
            if data.get('subsonic-response', {}).get('status') == 'ok':
                if playlist_id == "NEW":
                    # Extract playlist ID from response when creating new playlist
                    playlist_data = data.get('subsonic-response', {}).get('playlist', {})
                    new_playlist_id = playlist_data.get('id')
                    song_count = playlist_data.get('songCount', len(track_ids))
                    return f"Successfully created Navidrome playlist '{playlist_name}' (ID: {new_playlist_id}) with {song_count} tracks."
                else:
                    return f"Successfully added {len(track_ids)} tracks to Navidrome playlist ID {playlist_id}."
            else:
                return f"Navidrome Error: {data.get('subsonic-response', {}).get('error', {}).get('message')}"
                
        except Exception as e:
            log_mcp(f"Navidrome Exception: {e}")
            return f"Error updating Navidrome playlist: {str(e)}"

    elif platform == "plex":
        url = get_config_value('PLEX', 'ServerURL')
        token = get_config_value('PLEX', 'Token')
        machine_id = get_config_value('PLEX', 'MachineID')
        
        log_mcp(f"Plex Config Check: URL={url}, Token={'[SET]' if token else '[NOT SET]'}, MachineID={machine_id}")
        
        if not all([url, token, machine_id]):
            missing = []
            if not url: missing.append('ServerURL')
            if not token: missing.append('Token')
            if not machine_id: missing.append('MachineID')
            log_mcp(f"Plex Config Missing: {', '.join(missing)}")
            return f"Error: Plex not configured. Missing: {', '.join(missing)}"
        
        # Validate track ID format: Plex uses numeric IDs (typically 6-7 digits), Navidrome uses hex strings (32 chars)
        # Check if track IDs look like Navidrome IDs (hex, 32 chars)
        invalid_ids = [tid for tid in track_ids if len(tid) == 32 and all(c in '0123456789abcdef' for c in tid.lower())]
        if invalid_ids:
            log_mcp(f"Warning: Track IDs appear to be Navidrome format (hex): {invalid_ids[0]}")
            return f"Error: Invalid track IDs for Plex. These appear to be Navidrome track IDs (hex format). Plex requires numeric track IDs. Please search for tracks using platform='plex' to get valid Plex track IDs."
        
        # Check if track IDs look like Deezer IDs (9 digits) or other invalid formats
        # Plex track IDs are typically 6-7 digits, rarely up to 8 digits
        suspicious_ids = [tid for tid in track_ids if tid.isdigit() and len(tid) >= 9]
        if suspicious_ids:
            log_mcp(f"Warning: Track IDs appear to be from another service (9+ digits): {suspicious_ids[0]}")
            return f"Error: Invalid track IDs for Plex. These appear to be from another service (e.g., Deezer with 9-digit IDs). Plex track IDs are typically 6-7 digits. You MUST use the 'search_tracks' tool with platform='plex' to get valid Plex track IDs before adding them to playlists. Do not use track IDs from other services like Deezer."
            
        try:
            headers = {'X-Plex-Token': token, 'Accept': 'application/json'}
            
            if playlist_id == "NEW":
                if not playlist_name:
                    return "Error: playlist_name is required when creating a new Plex playlist."
                
                first_track = track_ids[0]
                remaining_tracks = track_ids[1:]
                
                uri = f"server://{machine_id}/com.plexapp.plugins.library/library/metadata/{first_track}"
                params = {'type': 'audio', 'title': playlist_name, 'smart': '0', 'uri': uri, 'X-Plex-Token': token}
                
                log_mcp(f"Plex Create Request: {url}/playlists with params {params}")
                resp = requests.post(f"{url.rstrip('/')}/playlists", headers=headers, params=params)
                log_mcp(f"Plex Create Response: {resp.status_code} - {resp.text}")
                resp.raise_for_status()
                data = resp.json()
                
                if not data.get('MediaContainer', {}).get('Metadata'):
                    return "Error: Failed to create Plex playlist."
                    
                new_playlist_id = data['MediaContainer']['Metadata'][0]['ratingKey']
                log_mcp(f"Created Plex playlist ID: {new_playlist_id}")
                
                # Verify first track was added
                created_playlist_meta = data['MediaContainer']['Metadata'][0]
                first_track_added = created_playlist_meta.get('leafCount', created_playlist_meta.get('size', '0'))
                tracks_added_so_far = int(first_track_added) if first_track_added else 0
                
                if remaining_tracks:
                    # Plex API requires adding tracks one at a time
                    added_count = 0
                    for tid in remaining_tracks:
                        uri = f"server://{machine_id}/com.plexapp.plugins.library/library/metadata/{tid}"
                        put_params = {'X-Plex-Token': token, 'uri': uri}
                        try:
                            put_resp = requests.put(f"{url.rstrip('/')}/playlists/{new_playlist_id}/items", headers=headers, params=put_params, timeout=30)
                            put_resp.raise_for_status()
                            result = put_resp.json()
                            if result.get('MediaContainer', {}).get('leafCountAdded', 0) > 0:
                                added_count += 1
                        except Exception as e:
                            log_mcp(f"Plex: Error adding track {tid}: {e}")
                    
                    total_added = tracks_added_so_far + added_count
                    log_mcp(f"Plex: Added {added_count} of {len(remaining_tracks)} remaining tracks to playlist {new_playlist_id}")
                    
                    if total_added < len(track_ids):
                        return f"Warning: Created Plex playlist '{playlist_name}' (ID: {new_playlist_id}) but only {total_added} out of {len(track_ids)} tracks were added."
                    return f"Successfully created Plex playlist '{playlist_name}' (ID: {new_playlist_id}) with {total_added} tracks."
                
                # If only one track or verification failed, return basic success message
                if tracks_added_so_far == 0:
                    return f"Warning: Created Plex playlist '{playlist_name}' (ID: {new_playlist_id}) but no tracks were added. The provided track IDs may be invalid. Please use the 'search_tracks' tool with platform='plex' to get valid Plex track IDs."
                else:
                    return f"Successfully created Plex playlist '{playlist_name}' (ID: {new_playlist_id}) with {tracks_added_so_far} track(s)."
                
            else:
                # Add tracks to existing playlist - Plex API requires adding one track at a time
                added_count = 0
                for tid in track_ids:
                    uri = f"server://{machine_id}/com.plexapp.plugins.library/library/metadata/{tid}"
                    put_params = {'X-Plex-Token': token, 'uri': uri}
                    try:
                        resp = requests.put(f"{url.rstrip('/')}/playlists/{playlist_id}/items", headers=headers, params=put_params, timeout=30)
                        resp.raise_for_status()
                        result = resp.json()
                        if result.get('MediaContainer', {}).get('leafCountAdded', 0) > 0:
                            added_count += 1
                    except Exception as e:
                        log_mcp(f"Plex: Error adding track {tid}: {e}")
                
                log_mcp(f"Plex: Added {added_count} of {len(track_ids)} tracks to playlist {playlist_id}")
                
                if added_count == 0:
                    return f"Warning: No tracks were added to Plex playlist ID {playlist_id}. The provided track IDs may be invalid."
                elif added_count < len(track_ids):
                    return f"Warning: Only {added_count} out of {len(track_ids)} tracks were added to Plex playlist ID {playlist_id}."
                else:
                    return f"Successfully added {added_count} tracks to Plex playlist ID {playlist_id}."
                
        except Exception as e:
            log_mcp(f"Plex Exception: {e}")
            return f"Error updating Plex playlist: {str(e)}"
    
    else:
        return f"Error: Unknown platform '{platform}'"

@mcp.tool()
def delete_playlist(playlist_id: str, platform: str = "navidrome") -> str:
    """
    Delete a playlist from Plex or Navidrome.
    
    Args:
        playlist_id: The ID of the playlist to delete.
        platform: The platform to use ("navidrome" or "plex").
        
    Returns:
        Status message indicating success or failure.
    """
    import datetime
    def log_mcp(msg):
        try:
            with open('/opt/tuneforge/logs/mcp_debug.log', 'a') as f:
                f.write(f"{datetime.datetime.now()} - {msg}\n")
        except:
            pass

    log_mcp(f"delete_playlist called with: playlist_id={playlist_id}, platform={platform}")
    platform = platform.lower()
    
    if platform == "navidrome":
        base_url = get_config_value('NAVIDROME', 'URL')
        user = get_config_value('NAVIDROME', 'Username')
        password = get_config_value('NAVIDROME', 'Password')
        
        if not all([base_url, user, password]):
            return "Error: Navidrome not configured."
        
        try:
            base_url = base_url.rstrip('/')
            if '/rest' not in base_url:
                base_url = f"{base_url}/rest"
            
            params = {
                'u': user,
                'p': password,
                'v': '1.16.1',
                'c': 'TuneForge',
                'f': 'json',
                'id': playlist_id
            }
            
            log_mcp(f"Navidrome Delete Request: deletePlaylist.view with params {params}")
            response = requests.get(f"{base_url}/deletePlaylist.view", params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            log_mcp(f"Navidrome Delete Response: {data}")
            
            if data.get('subsonic-response', {}).get('status') == 'ok':
                return f"Successfully deleted Navidrome playlist ID {playlist_id}."
            else:
                return f"Navidrome Error: {data.get('subsonic-response', {}).get('error', {}).get('message')}"
                
        except Exception as e:
            log_mcp(f"Navidrome Delete Exception: {e}")
            return f"Error deleting Navidrome playlist: {str(e)}"
    
    elif platform == "plex":
        url = get_config_value('PLEX', 'ServerURL')
        token = get_config_value('PLEX', 'Token')
        
        if not all([url, token]):
            return "Error: Plex not configured."
        
        try:
            headers = {'X-Plex-Token': token, 'Accept': 'application/json'}
            
            log_mcp(f"Plex Delete Request: {url}/playlists/{playlist_id}")
            resp = requests.delete(f"{url.rstrip('/')}/playlists/{playlist_id}", headers=headers, timeout=30)
            log_mcp(f"Plex Delete Response: {resp.status_code} - {resp.text}")
            resp.raise_for_status()
            
            return f"Successfully deleted Plex playlist ID {playlist_id}."
            
        except Exception as e:
            log_mcp(f"Plex Delete Exception: {e}")
            return f"Error deleting Plex playlist: {str(e)}"
    
    else:
        return f"Error: Unknown platform '{platform}'"


if __name__ == "__main__":
    # Run the service using uvicorn when executed directly
    import uvicorn
    # Import the mcp object to be served
    # The FastMCP object exposes a .sse_handler property that is an ASGI app
    uvicorn.run(mcp.streamable_http_app, host="0.0.0.0", port=8000)
