import sqlite3
import math
import os
import logging
from logging.handlers import RotatingFileHandler
import requests
import configparser
import json
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import List, Dict, Optional, Any, Annotated
import sonic_similarity
import feature_store

# Configure logging
# Set up logging with separate handlers for file and console
# File handler: INFO level for detailed logs to disk
# Console handler: WARNING level to reduce output to LLM agent
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Console handler for debug output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter('%(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# Prevent propagation to root logger to avoid duplicate output
logger.propagate = False

# Initialize FastMCP server
mcp = FastMCP("TuneForge", debug=True)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db', 'local_music.db')

def get_db_connection():
    """Get a connection to the local music database."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@mcp.tool()
def find_similar_songs(
    song_title: Annotated[str, Field(description="The title of the song to find similarities for.", json_schema_extra={"inputType": "text"})],
    artist_name: Annotated[str, Field(default="", description="Optional artist name to narrow down the search (leave empty to skip).", json_schema_extra={"inputType": "text"})] = "",
    limit: Annotated[float, Field(default=5.0, description="The maximum number of similar songs to return (default: 5).", json_schema_extra={"inputType": "number"})] = 5.0
) -> str:
    """
    Find similar songs based on audio features.
    
    Args:
        song_title: The title of the song to find similarities for.
        artist_name: Optional artist name to narrow down the search (leave empty to skip).
        limit: The maximum number of similar songs to return (default: 5).
        
    Returns:
        A formatted string containing the list of similar songs and their similarity scores.
    """
    # Cast limit to int
    limit = int(limit)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Find the seed track
        query = "SELECT id, title, artist, file_path FROM tracks WHERE title LIKE ?"
        params = [f"%{song_title}%"]
        
        # Treat empty string as "no value"
        if artist_name and artist_name.strip():
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
        top_matches = similarities[:int(limit)]
        
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
            for track in metadata[:int(limit)]:
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
def search_tracks(
    query: Annotated[str, Field(description="The search query - can be a title, artist, genre, tag, or any text", json_schema_extra={"inputType": "text"})],
    limit: Annotated[float, Field(default=20.0, description="Maximum number of results to return (default: 20, max: 50)", json_schema_extra={"inputType": "number"})] = 20.0
) -> str:
    """
    Search for tracks in the user's Plex library by title, artist, genre, tags, or any text query.
    
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
        limit: Maximum number of results to return (default: 20, max: 50)
        
    Returns:
        JSON string containing list of found tracks WITH VALID TRACK IDs from the user's library.
        These track IDs can be immediately used with add_to_playlist. All results are confirmed 
        to exist in the user's Plex library.
    """
    # Cast limit to int
    limit = int(limit)

    # Enforce reasonable limits
    limit = min(max(1, limit), 50)
    
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

@mcp.tool()
def bulk_search_tracks(
    queries: Annotated[str, Field(description="List of search queries (e.g., [\"Oasis\", \"Wonderwall\", \"The Beatles\"]) as a JSON string", json_schema_extra={"inputType": "json"})],
    limit: Annotated[float, Field(default=50.0, description="Total maximum number of results across all queries (default: 50, max: 200)", json_schema_extra={"inputType": "number"})] = 50.0
) -> str:
    """
    Search for multiple tracks in a single call across Plex library.
    
    CRITICAL: All results returned by this function are tracks that EXIST in the user's library. 
    These are REAL tracks that can be immediately added to playlists. Never question whether 
    these results are valid - they are confirmed library tracks.
    
    This function allows searching for multiple tracks (e.g., 10 queries) in a single MCP call,
    returning results grouped by query with track IDs for each match.
    
    Args:
        queries: List of search queries (e.g., ["Oasis", "Wonderwall", "The Beatles"]) as a JSON string
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
    
    # Parse inputs
    limit = int(limit)
    try:
        if isinstance(queries, str):
            queries = json.loads(queries)
    except Exception as e:
        return json.dumps({"error": f"Invalid JSON for queries: {e}"}, indent=2)

    
    # Validate inputs
    if not queries or not isinstance(queries, list) or len(queries) == 0:
        return json.dumps({"error": "No queries provided. Please provide a list of search queries."}, indent=2)
    
    # Enforce reasonable limits
    limit = min(max(1, limit), 200)
    
    # Check platform configuration
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
            tracks = _search_plex_tracks(query, query_limit)
            return (query, tracks, None)
        except Exception as e:
            logger.error(f"Error searching '{query}' on plex: {e}")
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
def create_playlist(
    name: Annotated[str, Field(description="Name of the playlist", json_schema_extra={"inputType": "text"})]
) -> str:
    """
    Create a new empty playlist.
    
    Args:
        name: Name of the playlist
        
    Returns:
        Status message with Playlist ID if successful.
    """
    url = get_config_value('PLEX', 'ServerURL')
    token = get_config_value('PLEX', 'Token')
    machine_id = get_config_value('PLEX', 'MachineID')
    
    if not all([url, token, machine_id]):
        return "Error: Plex not configured (URL, Token, or MachineID missing)."
        
    return "Error: Plex requires at least one track ID to create a playlist. Use 'add_to_playlist' (which can create new ones if supported) or provide a track."

@mcp.tool()
def add_to_playlist(
    playlist_id: Annotated[str, Field(description="The ID of the playlist to add to. Use \"NEW\" to create a new playlist.", json_schema_extra={"inputType": "text"})],
    track_ids: Annotated[str, Field(description="A list of track IDs to add (as JSON string). MUST be obtained from search_tracks.", json_schema_extra={"inputType": "json"})],
    playlist_name: Annotated[str, Field(default="", description="The name of the playlist (required if playlist_id is \"NEW\").", json_schema_extra={"inputType": "text"})] = ""
) -> str:
    """
    Add tracks to a playlist.
    
    IMPORTANT: You MUST use the 'search_tracks' tool to get valid track IDs before calling this function.
    Track IDs from different platforms or services (e.g., Deezer IDs) are NOT compatible and will be rejected.
    - For Plex: Use search_tracks to get Plex track IDs (typically 6-7 digit numbers).
    
    Args:
        playlist_id: The ID of the playlist to add to. Use "NEW" to create a new playlist.
        track_ids: A list of track IDs to add (as JSON string). MUST be obtained from search_tracks.
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

    # Parse track_ids
    try:
        if isinstance(track_ids, str):
            track_ids = json.loads(track_ids)
    except Exception as e:
        return f"Error: Invalid JSON for track_ids: {e}"

    log_mcp(f"add_to_playlist called with: playlist_id={playlist_id}, track_ids={track_ids}, playlist_name={playlist_name}")

    if not track_ids:
        return "Error: No track IDs provided."
        
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
    
    # Check if track IDs look like Deezer IDs (9 digits) or other invalid formats
    # Plex track IDs are typically 6-7 digits, rarely up to 8 digits
    suspicious_ids = [tid for tid in track_ids if tid.isdigit() and len(tid) >= 9]
    if suspicious_ids:
        log_mcp(f"Warning: Track IDs appear to be from another service (9+ digits): {suspicious_ids[0]}")
        return f"Error: Invalid track IDs for Plex. These appear to be from another service (e.g., Deezer with 9-digit IDs). Plex track IDs are typically 6-7 digits. You MUST use the 'search_tracks' tool to get valid Plex track IDs before adding them to playlists. Do not use track IDs from other services like Deezer."
        
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
                return f"Warning: Created Plex playlist '{playlist_name}' (ID: {new_playlist_id}) but no tracks were added. The provided track IDs may be invalid. Please use the 'search_tracks' tool to get valid Plex track IDs."
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

@mcp.tool()
def delete_playlist(
    playlist_id: Annotated[str, Field(description="The ID of the playlist to delete.", json_schema_extra={"inputType": "text"})]
) -> str:
    """
    Delete a playlist from Plex.
    
    Args:
        playlist_id: The ID of the playlist to delete.
        
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

    log_mcp(f"delete_playlist called with: playlist_id={playlist_id}")
    
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

@mcp.tool()
def search_playlists(
    query: Annotated[str, Field(description="The name or partial name of the playlist to search for.", json_schema_extra={"inputType": "text"})],
    limit: Annotated[float, Field(default=10.0, description="Maximum number of results to return (default: 10).", json_schema_extra={"inputType": "number"})] = 10.0
) -> str:
    """
    Search for playlists in Plex.
    
    Args:
        query: The name or partial name of the playlist to search for.
        limit: Maximum number of results to return (default: 10).
        
    Returns:
        JSON string containing list of playlists with 'id', 'title', 'track_count'.
    """
    # Cast limit to int
    limit = int(limit)

    url = get_config_value('PLEX', 'ServerURL')
    token = get_config_value('PLEX', 'Token')
    
    if not all([url, token]):
        return "Error: Plex not configured."
        
    try:
        headers = {'X-Plex-Token': token, 'Accept': 'application/json'}
        
        # Use general search restricted to playlists (type 15)
        params = {'query': query, 'type': '15', 'limit': limit}
        response = requests.get(f"{url.rstrip('/')}/search", headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        playlists = []
        metadata = data.get('MediaContainer', {}).get('Metadata', [])
        
        for item in metadata:
            playlists.append({
                'id': item.get('ratingKey'),
                'title': item.get('title'),
                'track_count': item.get('leafCount')
            })
            
        return json.dumps(playlists, indent=2)
        
    except Exception as e:
        return f"Error searching playlists: {str(e)}"

@mcp.tool()
def get_playlist_tracks(
    playlist_id: Annotated[str, Field(description="The ID of the playlist.", json_schema_extra={"inputType": "text"})]
) -> str:
    """
    Get all tracks from a specific Plex playlist.
    
    Args:
        playlist_id: The ID of the playlist.
        
    Returns:
        JSON string containing list of tracks with 'id', 'title', 'artist', 'album', and 'playlist_item_id'.
        'playlist_item_id' is REQUIRED for reordering tracks within the playlist.
    """
    url = get_config_value('PLEX', 'ServerURL')
    token = get_config_value('PLEX', 'Token')
    
    if not all([url, token]):
        return "Error: Plex not configured."
        
    try:
        headers = {'X-Plex-Token': token, 'Accept': 'application/json'}
        
        response = requests.get(f"{url.rstrip('/')}/playlists/{playlist_id}/items", headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        tracks = []
        metadata = data.get('MediaContainer', {}).get('Metadata', [])
        
        for item in metadata:
            tracks.append({
                'id': item.get('ratingKey'),
                'title': item.get('title'),
                'artist': item.get('grandparentTitle', 'Unknown'), # grandparentTitle is usually Artist for tracks
                'album': item.get('parentTitle', 'Unknown'),      # parentTitle is usually Album
                'playlist_item_id': item.get('playlistItemID')    # Required for reordering
            })
            
        return json.dumps(tracks, indent=2)
        
    except Exception as e:
        return f"Error getting playlist tracks: {str(e)}"

@mcp.tool()
def move_playlist_item(
    playlist_id: Annotated[str, Field(description="The ID of the playlist.", json_schema_extra={"inputType": "text"})],
    playlist_item_id: Annotated[str, Field(description="The ID of the item to move (from get_playlist_tracks).", json_schema_extra={"inputType": "text"})],
    after_playlist_item_id: Annotated[str, Field(default="", description="The ID of the item to place the moved item AFTER. Leave empty to move the item to the beginning of the playlist.", json_schema_extra={"inputType": "text"})] = ""
) -> str:
    """
    Move a track to a new position within a playlist.
    
    Args:
        playlist_id: The ID of the playlist.
        playlist_item_id: The ID of the item to move (from get_playlist_tracks).
        after_playlist_item_id: The ID of the item to place the moved item AFTER. 
                                Leave empty to move the item to the beginning of the playlist.
        
    Returns:
        Status message indicating success or failure.
    """
    url = get_config_value('PLEX', 'ServerURL')
    token = get_config_value('PLEX', 'Token')
    
    if not all([url, token]):
        return "Error: Plex not configured."
        
    try:
        headers = {'X-Plex-Token': token, 'Accept': 'application/json'}
        
        # Endpoint: PUT /playlists/{playlistID}/items/{playlistItemID}/move
        # Query param: after={afterPlaylistItemID} (optional)
        
        move_url = f"{url.rstrip('/')}/playlists/{playlist_id}/items/{playlist_item_id}/move"
        params = {}
        # Treat empty string as "no value"
        if after_playlist_item_id and after_playlist_item_id.strip():
            params['after'] = after_playlist_item_id
            
        response = requests.put(move_url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        return f"Successfully moved item {playlist_item_id} in playlist {playlist_id}."
        
    except Exception as e:
        return f"Error moving playlist item: {str(e)}"


# Add request logging middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import json as json_lib

class MCPRequestLogger(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Log incoming request
        logger.debug(f"=== INCOMING REQUEST ===")
        logger.debug(f"Method: {request.method}")
        logger.debug(f"URL: {request.url}")
        logger.debug(f"Headers: {dict(request.headers)}")
        
        # Try to read body if it's a POST
        if request.method == "POST":
            try:
                body = await request.body()
                if body:
                    try:
                        body_json = json_lib.loads(body)
                        logger.debug(f"Request body: {json_lib.dumps(body_json, indent=2)}")
                    except:
                        logger.debug(f"Request body (raw): {body[:500]}")
            except Exception as e:
                logger.debug(f"Error reading body: {e}")
        
        # Process request
        response = await call_next(request)
        
        # Log response
        logger.debug(f"=== RESPONSE ===")
        logger.debug(f"Status: {response.status_code}")
        logger.debug(f"Headers: {dict(response.headers)}")
        
        # Try to read response body
        try:
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            if response_body:
                try:
                    response_json = json_lib.loads(response_body)
                    logger.debug(f"Response body: {json_lib.dumps(response_json, indent=2)}")
                except:
                    logger.debug(f"Response body (raw): {response_body[:500]}")
            # Recreate response with body
            from starlette.responses import Response
            response = Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
        except Exception as e:
            logger.debug(f"Error reading response body: {e}")
        
        return response

# Add logging hook and fix schemas for n8n compatibility
_original_list_tools_method = mcp.list_tools
async def list_tools_with_logging():
    logger.debug("=== list_tools() called ===")
    result = await _original_list_tools_method()
    logger.debug(f"list_tools() returning {len(result)} tools")
    
    # Fix schemas for n8n compatibility
    from mcp.types import Tool as MCPTool
    fixed_tools = []
    
    for tool in result:
        logger.debug(f"Tool: {tool.name}")
        
        # Convert schema to dict if needed
        schema = tool.inputSchema if isinstance(tool.inputSchema, dict) else tool.inputSchema.model_dump() if hasattr(tool.inputSchema, 'model_dump') else {}
        
        # Ensure schema is a dict
        if not isinstance(schema, dict):
            logger.warning(f"⚠️  {tool.name}: inputSchema is not a dict: {type(schema)}")
            schema = {}
        
        # Add inputType to schema root (n8n might expect this)
        if 'inputType' not in schema:
            schema['inputType'] = 'object'
            logger.debug(f"  Added inputType='object' to schema root")
        
        # Ensure properties exist and are a dict
        if 'properties' not in schema:
            schema['properties'] = {}
            logger.warning(f"⚠️  {tool.name}: inputSchema missing properties, added empty dict")
        
        props = schema.get('properties', {})
        if not isinstance(props, dict):
            logger.warning(f"⚠️  {tool.name}: properties is not a dict: {type(props)}")
            props = {}
            schema['properties'] = props
        
        logger.debug(f"  Properties: {list(props.keys())}")
        
        # Ensure all properties are dicts and have inputType
        # CRITICAL: Process in a way that ensures no undefined values
        prop_names_to_process = list(props.keys())
        for prop_name in prop_names_to_process:
            prop_def = props.get(prop_name)
            
            # Handle None or missing properties
            if prop_def is None:
                logger.warning(f"⚠️  {tool.name}.{prop_name}: prop_def is None, creating default")
                props[prop_name] = {'type': 'string', 'inputType': 'text', 'title': prop_name.replace('_', ' ').title()}
                prop_def = props[prop_name]
            elif not isinstance(prop_def, dict):
                logger.warning(f"⚠️  {tool.name}.{prop_name}: prop_def is not a dict: {type(prop_def)}, converting")
                props[prop_name] = {'type': 'string', 'inputType': 'text', 'title': prop_name.replace('_', ' ').title()}
                prop_def = props[prop_name]
            
            # Ensure prop_def is a proper dict with all required fields
            if not isinstance(prop_def, dict):
                continue  # Skip if still not a dict after conversion
            
            # Ensure type exists
            if 'type' not in prop_def:
                prop_def['type'] = 'string'
                logger.debug(f"    {prop_name}: Added missing type='string'")
            
            # CRITICAL FIX: n8n doesn't support 'integer' type, only 'number'
            # Convert 'integer' to 'number' for n8n compatibility (GitHub issue #21569)
            prop_type = prop_def.get('type', 'string')
            if prop_type == 'integer':
                prop_def['type'] = 'number'
                prop_type = 'number'
                logger.debug(f"    {prop_name}: Converted type from 'integer' to 'number' for n8n compatibility")
            
            # Ensure inputType exists
            if 'inputType' not in prop_def:
                # Infer inputType from type
                if prop_type == 'number':
                    prop_def['inputType'] = 'number'
                elif prop_type == 'array':
                    prop_def['inputType'] = 'json'
                else:
                    prop_def['inputType'] = 'text'
                logger.debug(f"    {prop_name}: Added inputType='{prop_def['inputType']}'")
            
            # CRITICAL: Ensure default value doesn't cause issues
            # If default exists, ensure it's a simple value (not an object that n8n might try to access inputType on)
            if 'default' in prop_def:
                default_val = prop_def['default']
                # If default is None, remove it (empty string is better for n8n)
                if default_val is None:
                    prop_def['default'] = ''
                    logger.debug(f"    {prop_name}: Changed None default to empty string")
                # If default is a complex object, convert to string representation
                elif isinstance(default_val, (dict, list)):
                    prop_def['default'] = str(default_val)
                    logger.debug(f"    {prop_name}: Converted complex default to string")
            
            prop_type = prop_def.get('type')
            logger.debug(f"    {prop_name}: type={prop_type}, has inputType={prop_def.get('inputType')}")
            
            # Fix array items - ensure items is always a proper dict
            if prop_type == 'array':
                # CRITICAL: n8n may access items.inputType, so ensure items exists and is a dict
                items = prop_def.get('items')
                if items is None:
                    logger.warning(f"⚠️  {tool.name}.{prop_name}: array missing items, adding default")
                    prop_def['items'] = {'type': 'string', 'inputType': 'text'}
                    items = prop_def['items']
                elif not isinstance(items, dict):
                    logger.warning(f"⚠️  {tool.name}.{prop_name}.items: not a dict: {type(items)}, fixing")
                    prop_def['items'] = {'type': 'string', 'inputType': 'text'}
                    items = prop_def['items']
                
                # Ensure items is a dict and has all required fields
                if not isinstance(items, dict):
                    prop_def['items'] = {'type': 'string', 'inputType': 'text'}
                    items = prop_def['items']
                
                # Ensure items has both type and inputType (CRITICAL for n8n)
                if 'type' not in items:
                    items['type'] = 'string'
                    logger.debug(f"      items: Added missing type='string'")
                if 'inputType' not in items:
                    items['inputType'] = 'text'
                    logger.debug(f"      items: Added inputType='text'")
                
                # Ensure array property itself has inputType (should already be set above)
                if 'inputType' not in prop_def:
                    prop_def['inputType'] = 'json'
                    logger.debug(f"      array property: Added inputType='json'")
        
        # Ensure required array only contains properties that exist
        # CRITICAL: n8n may have a bug with required array properties that are arrays
        # So we'll keep required as-is but ensure all required properties are fully defined
        if 'required' in schema and isinstance(schema['required'], list):
            existing_props = set(props.keys())
            schema['required'] = [r for r in schema['required'] if r in existing_props]
            logger.debug(f"  Required array filtered to existing properties: {schema['required']}")
            
            # Ensure all required properties (especially arrays) are fully defined
            for req_prop in schema['required']:
                if req_prop in props:
                    req_prop_def = props[req_prop]
                    if isinstance(req_prop_def, dict):
                        # Ensure required property has inputType
                        if 'inputType' not in req_prop_def:
                            prop_type = req_prop_def.get('type', 'string')
                            if prop_type == 'number':
                                req_prop_def['inputType'] = 'number'
                            elif prop_type == 'array':
                                req_prop_def['inputType'] = 'json'
                            else:
                                req_prop_def['inputType'] = 'text'
                            logger.debug(f"  Required property {req_prop}: Added inputType")
                        
                        # If required property is an array, ensure items are fully defined
                        if req_prop_def.get('type') == 'array':
                            items = req_prop_def.get('items')
                            if items is None:
                                req_prop_def['items'] = {'type': 'string', 'inputType': 'text'}
                                logger.debug(f"  Required array {req_prop}: Created items")
                            elif isinstance(items, dict):
                                if 'type' not in items:
                                    items['type'] = 'string'
                                    logger.debug(f"  Required array {req_prop}.items: Added type")
                                if 'inputType' not in items:
                                    items['inputType'] = 'text'
                                    logger.debug(f"  Required array {req_prop}.items: Added inputType")
                            else:
                                req_prop_def['items'] = {'type': 'string', 'inputType': 'text'}
                                logger.debug(f"  Required array {req_prop}: Fixed items (was {type(items)})")
        
        # Fix outputSchema if it exists
        output_schema = tool.outputSchema
        if output_schema and isinstance(output_schema, dict):
            # Ensure outputSchema properties have inputType
            output_props = output_schema.get('properties', {})
            if isinstance(output_props, dict):
                for prop_name, prop_def in output_props.items():
                    if isinstance(prop_def, dict) and 'inputType' not in prop_def:
                        prop_type = prop_def.get('type', 'string')
                        if prop_type in ['integer', 'number']:
                            prop_def['inputType'] = 'number'
                        elif prop_type == 'array':
                            prop_def['inputType'] = 'json'
                        else:
                            prop_def['inputType'] = 'text'
                        logger.debug(f"  outputSchema.{prop_name}: Added inputType='{prop_def['inputType']}'")
        
        # Log the final schema structure for debugging
        logger.debug(f"  Final schema keys: {sorted(schema.keys())}")
        logger.debug(f"  Final properties count: {len(props)}")
        
        # Ensure meta exists and has inputType if n8n expects it
        tool_meta = tool._meta if hasattr(tool, '_meta') else {}
        if tool_meta is None:
            tool_meta = {}
        if not isinstance(tool_meta, dict):
            tool_meta = {}
        # Add inputType to meta in case n8n looks for it there
        if 'inputType' not in tool_meta:
            tool_meta['inputType'] = 'object'
        
        # CRITICAL: Ensure schema is a plain dict, not a Pydantic model
        # Deep copy to avoid any reference issues
        import copy
        schema_dict = copy.deepcopy(schema)
        output_schema_dict = copy.deepcopy(output_schema) if output_schema else None
        
        # Create new tool with fixed schema
        fixed_tool = MCPTool(
            name=tool.name,
            title=tool.title,
            description=tool.description,
            inputSchema=schema_dict,  # Use deep copy of fixed schema
            outputSchema=output_schema_dict,  # Use deep copy of fixed output schema
            annotations=tool.annotations,
            icons=tool.icons,
            _meta=tool_meta if tool_meta else None,
        )
        
        # CRITICAL FIX: After creating MCPTool, ensure integer->number conversion, array items, and inputType persist
        # MCPTool might convert schema to a Pydantic model, so we need to ensure it's a dict with our fixes
        if hasattr(fixed_tool, 'inputSchema'):
            if isinstance(fixed_tool.inputSchema, dict):
                # Ensure integer->number conversion and array items are properly set
                props = fixed_tool.inputSchema.get('properties', {})
                for prop_name, prop_def in props.items():
                    if isinstance(prop_def, dict):
                        # Convert integer to number
                        if prop_def.get('type') == 'integer':
                            prop_def['type'] = 'number'
                            logger.debug(f"  Post-MCPTool: Converted {prop_name} from integer to number")
                        # Ensure array items have type and inputType
                        if prop_def.get('type') == 'array':
                            items = prop_def.get('items')
                            if isinstance(items, dict):
                                if 'type' not in items:
                                    items['type'] = 'string'
                                    logger.debug(f"  Post-MCPTool: Added type to {prop_name}.items")
                                if 'inputType' not in items:
                                    items['inputType'] = 'text'
                                    logger.debug(f"  Post-MCPTool: Added inputType to {prop_name}.items")
                            elif items is None:
                                prop_def['items'] = {'type': 'string', 'inputType': 'text'}
                                logger.debug(f"  Post-MCPTool: Created items for {prop_name}")
                # Ensure inputType at root
                if 'inputType' not in fixed_tool.inputSchema:
                    fixed_tool.inputSchema['inputType'] = 'object'
            else:
                # If it's a Pydantic model, convert to dict and apply all fixes
                schema_from_model = fixed_tool.inputSchema.model_dump() if hasattr(fixed_tool.inputSchema, 'model_dump') else dict(fixed_tool.inputSchema)
                # Apply integer->number conversion and array items fixes
                props = schema_from_model.get('properties', {})
                for prop_name, prop_def in props.items():
                    if isinstance(prop_def, dict):
                        # Convert integer to number
                        if prop_def.get('type') == 'integer':
                            prop_def['type'] = 'number'
                            logger.debug(f"  Post-MCPTool (from model): Converted {prop_name} from integer to number")
                        # Ensure array items have type and inputType
                        if prop_def.get('type') == 'array':
                            items = prop_def.get('items')
                            if isinstance(items, dict):
                                if 'type' not in items:
                                    items['type'] = 'string'
                                    logger.debug(f"  Post-MCPTool (from model): Added type to {prop_name}.items")
                                if 'inputType' not in items:
                                    items['inputType'] = 'text'
                                    logger.debug(f"  Post-MCPTool (from model): Added inputType to {prop_name}.items")
                            elif items is None:
                                prop_def['items'] = {'type': 'string', 'inputType': 'text'}
                                logger.debug(f"  Post-MCPTool (from model): Created items for {prop_name}")
                # Ensure inputType at root
                if 'inputType' not in schema_from_model:
                    schema_from_model['inputType'] = 'object'
                # Recreate tool with fixed dict schema
                fixed_tool = MCPTool(
                    name=tool.name,
                    title=tool.title,
                    description=tool.description,
                    inputSchema=schema_from_model,
                    outputSchema=output_schema_dict,
                    annotations=tool.annotations,
                    icons=tool.icons,
                    _meta=tool_meta if tool_meta else None,
                )
        
        fixed_tools.append(fixed_tool)
        
        # Log final tool structure for debugging n8n issues
        logger.debug(f"  Tool object created: name={fixed_tool.name}, has inputSchema={hasattr(fixed_tool, 'inputSchema')}")
    
    logger.debug(f"Fixed {len(fixed_tools)} tools for n8n compatibility")
    return fixed_tools

# Replace the method
mcp.list_tools = list_tools_with_logging

# Wrap streamable_http_app to add logging middleware  
_original_streamable_http_app = mcp.streamable_http_app
def streamable_http_app_with_logging():
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    
    app = _original_streamable_http_app()
    # Add logging middleware
    app.add_middleware(MCPRequestLogger)
    return app

mcp.streamable_http_app = streamable_http_app_with_logging

if __name__ == "__main__":
    # Run the service using uvicorn when executed directly
    import uvicorn
    # Import the mcp object to be served
    # The FastMCP object exposes a .sse_handler property that is an ASGI app
    # Enable uvicorn debug logging
    logger.info("Starting MCP server with debug logging enabled")
    uvicorn.run(mcp.streamable_http_app, host="0.0.0.0", port=8000, log_level="debug")
