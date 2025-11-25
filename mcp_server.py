import sqlite3
import math
import os
import logging
import requests
import configparser
import json
from typing import List, Dict, Optional, Any
from mcp.server.fastmcp import FastMCP
import sonic_similarity
import feature_store

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    logger.info(f"Finding similar songs for: title='{song_title}', artist='{artist_name}', limit={limit}")
    
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
        logger.info(f"Found seed track: {seed_track['title']} by {seed_track['artist']} (ID: {seed_id})")
        
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

def get_config_value(section, key, default=None):
    """Helper to read config.ini"""
    config = configparser.ConfigParser()
    config.optionxform = lambda optionstr: optionstr
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    if os.path.exists(config_path):
        config.read(config_path)
        if config.has_section(section):
            if key in config[section]:
                return config[section][key]
    return default

@mcp.tool()
def search_tracks(query: str, platform: str = "plex", limit: int = 20) -> str:
    """
    Search for tracks on Plex or Navidrome.
    
    Args:
        query: The search query (title, artist, etc.)
        platform: "plex" or "navidrome"
        limit: Maximum number of results to return (default: 20, max: 50)
        
    Returns:
        JSON string containing list of found tracks with IDs.
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
                return json.dumps(results, indent=2)
            else:
                return f"Navidrome Error: {data.get('subsonic-response', {}).get('error', {}).get('message')}"
                
        except Exception as e:
            return f"Error searching Navidrome: {str(e)}"

    elif platform == "plex":
        url = get_config_value('PLEX', 'ServerURL')
        token = get_config_value('PLEX', 'Token')
        section_id = get_config_value('PLEX', 'MusicSectionID')
        
        if not all([url, token, section_id]):
            return "Error: Plex not configured (URL, Token, or MusicSectionID missing)."
            
        try:
            headers = {'X-Plex-Token': token, 'Accept': 'application/json'}
            params = {'type': '10', 'query': query, 'X-Plex-Token': token} # type 10 is track
            
            # Search in the specific section
            search_url = f"{url.rstrip('/')}/library/sections/{section_id}/search"
            
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            metadata = data.get('MediaContainer', {}).get('Metadata', [])
            
            # Fallback: If no results and query has spaces, try splitting (e.g. "Title Artist" -> "Title")
            if not metadata and ' ' in query:
                words = query.split()
                # Try removing words from the end, one by one
                for i in range(len(words)-1, 0, -1):
                    sub_query = ' '.join(words[:i])
                    # Don't search for very short queries to avoid noise
                    if len(sub_query) < 3: 
                        break
                        
                    params['query'] = sub_query
                    try:
                        resp = requests.get(search_url, headers=headers, params=params, timeout=5)
                        if resp.status_code == 200:
                            sub_data = resp.json()
                            sub_metadata = sub_data.get('MediaContainer', {}).get('Metadata', [])
                            if sub_metadata:
                                metadata = sub_metadata
                                break
                    except Exception:
                        continue
            
            results = []
            if metadata:
                for track in metadata[:limit]:  # Limit results
                    results.append({
                        'id': track.get('ratingKey'),
                        'title': track.get('title'),
                        'artist': track.get('grandparentTitle'),
                        'album': track.get('parentTitle')
                    })
            return json.dumps(results, indent=2)
            
        except Exception as e:
            return f"Error searching Plex: {str(e)}"
            
    else:
        return "Error: Unsupported platform. Use 'plex' or 'navidrome'."

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
def add_to_playlist(playlist_id: str, track_ids: list[str], platform: str = "plex", playlist_name: str = None) -> str:
    """
    Add tracks to a playlist.
    
    Args:
        playlist_id: ID of the playlist (if existing). If creating new on Plex, pass "NEW" and provide playlist_name.
        track_ids: List of track IDs to add.
        platform: "plex" or "navidrome"
        playlist_name: Required if creating a new playlist on Plex (playlist_id="NEW"). Optional otherwise.
        
    Returns:
        Status message.
    """
    platform = platform.lower()
    
    if not track_ids:
        return "Error: No track IDs provided."
        
    if platform == "navidrome":
        url = get_config_value('NAVIDROME', 'URL')
        user = get_config_value('NAVIDROME', 'Username')
        password = get_config_value('NAVIDROME', 'Password')
        
        if not all([url, user, password]):
            return "Error: Navidrome not configured."
            
        try:
            base_url = url.rstrip('/')
            if '/rest' not in base_url: base_url = f"{base_url}/rest"
            
            if playlist_id and playlist_id != "NEW":
                params = {
                    'u': user, 'p': password, 'v': '1.16.1', 'c': 'TuneForge', 'f': 'json',
                    'playlistId': playlist_id,
                    'songIdToAdd': track_ids
                }
                endpoint = "updatePlaylist.view"
            elif playlist_name:
                params = {
                    'u': user, 'p': password, 'v': '1.16.1', 'c': 'TuneForge', 'f': 'json',
                    'name': playlist_name,
                    'songId': track_ids
                }
                endpoint = "createPlaylist.view"
            else:
                return "Error: Provide either playlist_id or playlist_name for Navidrome."

            response = requests.get(f"{base_url}/{endpoint}", params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('subsonic-response', {}).get('status') == 'ok':
                return f"Successfully added {len(track_ids)} tracks to Navidrome playlist."
            else:
                return f"Navidrome Error: {data.get('subsonic-response', {}).get('error', {}).get('message')}"
                
        except Exception as e:
            return f"Error updating Navidrome playlist: {str(e)}"

    elif platform == "plex":
        url = get_config_value('PLEX', 'ServerURL')
        token = get_config_value('PLEX', 'Token')
        machine_id = get_config_value('PLEX', 'MachineID')
        
        if not all([url, token, machine_id]):
            return "Error: Plex not configured."
            
        try:
            headers = {'X-Plex-Token': token, 'Accept': 'application/json'}
            
            if playlist_id == "NEW":
                if not playlist_name:
                    return "Error: playlist_name is required when creating a new Plex playlist."
                
                first_track = track_ids[0]
                remaining_tracks = track_ids[1:]
                
                uri = f"server://{machine_id}/com.plexapp.plugins.library/library/metadata/{first_track}"
                params = {'type': 'audio', 'title': playlist_name, 'smart': '0', 'uri': uri, 'X-Plex-Token': token}
                
                resp = requests.post(f"{url.rstrip('/')}/playlists", headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
                
                if not data.get('MediaContainer', {}).get('Metadata'):
                    return "Error: Failed to create Plex playlist."
                    
                new_playlist_id = data['MediaContainer']['Metadata'][0]['ratingKey']
                
                if remaining_tracks:
                    items_uris = [f"server://{machine_id}/com.plexapp.plugins.library/library/metadata/{tid}" for tid in remaining_tracks]
                    # Use PUT with proper format to ADD tracks (not replace)
                    put_params = {'uri': ','.join(items_uris), 'X-Plex-Token': token}
                    requests.put(f"{url.rstrip('/')}/playlists/{new_playlist_id}/items", headers=headers, params=put_params).raise_for_status()
                    
                return f"Successfully created Plex playlist '{playlist_name}' (ID: {new_playlist_id}) with {len(track_ids)} tracks."
                
            else:
                # Add tracks to existing playlist - matches working implementation from routes.py
                items_uris = [f"server://{machine_id}/com.plexapp.plugins.library/library/metadata/{tid}" for tid in track_ids]
                items_uri_param = ','.join(items_uris)
                # Important: X-Plex-Token must come BEFORE uri in params dict
                put_params = {
                    'X-Plex-Token': token,
                    'uri': items_uri_param
                }
                resp = requests.put(f"{url.rstrip('/')}/playlists/{playlist_id}/items", headers=headers, params=put_params, timeout=60)
                resp.raise_for_status()
                return f"Successfully added {len(track_ids)} tracks to Plex playlist ID {playlist_id}."
                
        except Exception as e:
            return f"Error updating Plex playlist: {str(e)}"
    
    else:
        return f"Error: Unknown platform '{platform}'"


if __name__ == "__main__":
    # Run the service using uvicorn when executed directly
    import uvicorn
    # Import the mcp object to be served
    # The FastMCP object exposes a .sse_handler property that is an ASGI app
    uvicorn.run(mcp.streamable_http_app, host="0.0.0.0", port=8000)
