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
            metadata = []
            
            # Strategy 1: Try to find the artist first, then get all their tracks
            # This is the most reliable way to find tracks by a specific artist
            search_url = f"{url.rstrip('/')}/library/sections/{section_id}/search"
            artist_params = {'type': '8', 'query': query, 'X-Plex-Token': token}  # type 8 is artist
            
            try:
                response = requests.get(search_url, headers=headers, params=artist_params, timeout=10)
                response.raise_for_status()
                data = response.json()
                artist_results = data.get('MediaContainer', {}).get('Metadata', [])
                
                # Look for exact artist name match (case-insensitive)
                query_lower = query.lower().strip()
                matching_artist = None
                for artist in artist_results:
                    if artist.get('title', '').lower() == query_lower:
                        matching_artist = artist
                        break
                
                # If we found a matching artist, get all their tracks
                if matching_artist:
                    artist_id = matching_artist.get('ratingKey')
                    all_url = f"{url.rstrip('/')}/library/sections/{section_id}/all"
                    track_params = {'type': '10', 'artist.id': artist_id, 'X-Plex-Token': token}
                    
                    try:
                        response = requests.get(all_url, headers=headers, params=track_params, timeout=10)
                        response.raise_for_status()
                        data = response.json()
                        metadata = data.get('MediaContainer', {}).get('Metadata', [])
                    except Exception:
                        pass  # Fall through to general search
            except Exception:
                pass  # Fall through to general search
            
            # Strategy 2: If we didn't find tracks via artist search, use general text search
            # This will catch track titles, partial matches, etc.
            if not metadata or len(metadata) < limit:
                track_params = {'type': '10', 'query': query, 'X-Plex-Token': token}
                
                try:
                    response = requests.get(search_url, headers=headers, params=track_params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    general_metadata = data.get('MediaContainer', {}).get('Metadata', [])
                    
                    # Prioritize results where artist name matches query
                    query_lower = query.lower().strip()
                    artist_matches = []
                    other_matches = []
                    existing_ids = {track.get('ratingKey') for track in metadata}
                    
                    for track in general_metadata:
                        track_id = track.get('ratingKey')
                        if track_id in existing_ids:
                            continue
                        artist = track.get('grandparentTitle', '')
                        if artist and artist.lower() == query_lower:
                            artist_matches.append(track)
                        else:
                            other_matches.append(track)
                    
                    # Combine: existing metadata (from artist search), then artist matches, then others
                    metadata = metadata + artist_matches + other_matches
                except Exception:
                    pass  # Use whatever we got from artist search
            
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
                    items_uris = [f"server://{machine_id}/com.plexapp.plugins.library/library/metadata/{tid}" for tid in remaining_tracks]
                    # Use PUT with proper format to ADD tracks (not replace)
                    put_params = {'uri': ','.join(items_uris), 'X-Plex-Token': token}
                    log_mcp(f"Plex Add Remaining Request: {url}/playlists/{new_playlist_id}/items with params {put_params}")
                    put_resp = requests.put(f"{url.rstrip('/')}/playlists/{new_playlist_id}/items", headers=headers, params=put_params, timeout=60)
                    log_mcp(f"Plex Add Remaining Response: {put_resp.status_code} - {put_resp.text}")
                    put_resp.raise_for_status()
                    
                    # Verify remaining tracks were added
                    try:
                        put_data = put_resp.json()
                        put_playlist_meta = put_data.get('MediaContainer', {}).get('Metadata', [])
                        if put_playlist_meta:
                            put_playlist_info = put_playlist_meta[0]
                            leaf_count_added = put_playlist_info.get('leafCountAdded')
                            if leaf_count_added is not None:
                                additional_added = int(leaf_count_added)
                                total_added = tracks_added_so_far + additional_added
                                if total_added < len(track_ids):
                                    return f"Warning: Created Plex playlist '{playlist_name}' (ID: {new_playlist_id}) but only {total_added} out of {len(track_ids)} tracks were added. Some track IDs may be invalid. Please use the 'search_tracks' tool with platform='plex' to get valid Plex track IDs."
                                else:
                                    return f"Successfully created Plex playlist '{playlist_name}' (ID: {new_playlist_id}) with {total_added} tracks."
                            else:
                                final_count = put_playlist_info.get('leafCount', put_playlist_info.get('size'))
                                if final_count:
                                    return f"Successfully created Plex playlist '{playlist_name}' (ID: {new_playlist_id}) with {final_count} tracks."
                    except (ValueError, KeyError, AttributeError) as e:
                        log_mcp(f"Plex: Error parsing response for remaining tracks: {e}")
                
                # If only one track or verification failed, return basic success message
                if tracks_added_so_far == 0:
                    return f"Warning: Created Plex playlist '{playlist_name}' (ID: {new_playlist_id}) but no tracks were added. The provided track IDs may be invalid. Please use the 'search_tracks' tool with platform='plex' to get valid Plex track IDs."
                else:
                    return f"Successfully created Plex playlist '{playlist_name}' (ID: {new_playlist_id}) with {tracks_added_so_far} track(s)."
                
            else:
                # Add tracks to existing playlist - matches working implementation from routes.py
                items_uris = [f"server://{machine_id}/com.plexapp.plugins.library/library/metadata/{tid}" for tid in track_ids]
                items_uri_param = ','.join(items_uris)
                # Important: X-Plex-Token must come BEFORE uri in params dict
                put_params = {
                    'X-Plex-Token': token,
                    'uri': items_uri_param
                }
                log_mcp(f"Plex Add Request: {url}/playlists/{playlist_id}/items with params {put_params}")
                resp = requests.put(f"{url.rstrip('/')}/playlists/{playlist_id}/items", headers=headers, params=put_params, timeout=60)
                log_mcp(f"Plex Add Response: {resp.status_code} - {resp.text}")
                resp.raise_for_status()
                
                # Verify tracks were actually added by checking the response
                try:
                    response_data = resp.json()
                    playlist_meta = response_data.get('MediaContainer', {}).get('Metadata', [])
                    if playlist_meta:
                        playlist_info = playlist_meta[0]
                        leaf_count_added = playlist_info.get('leafCountAdded')
                        if leaf_count_added is not None:
                            added_count = int(leaf_count_added)
                            if added_count == 0:
                                return f"Warning: No tracks were added to Plex playlist ID {playlist_id}. The provided track IDs may be invalid (e.g., from Deezer or another service). Please use the 'search_tracks' tool with platform='plex' to get valid Plex track IDs before adding them to playlists."
                            elif added_count < len(track_ids):
                                return f"Warning: Only {added_count} out of {len(track_ids)} tracks were added to Plex playlist ID {playlist_id}. Some track IDs may be invalid. Please use the 'search_tracks' tool with platform='plex' to get valid Plex track IDs."
                            else:
                                return f"Successfully added {added_count} tracks to Plex playlist ID {playlist_id}."
                        else:
                            # If leafCountAdded is not available, check final count
                            final_count = playlist_info.get('leafCount', playlist_info.get('size'))
                            if final_count is not None:
                                log_mcp(f"Plex: leafCountAdded not available, but final count is {final_count}")
                                return f"Successfully added tracks to Plex playlist ID {playlist_id}. (Final track count: {final_count})"
                            else:
                                # Fallback: assume success but warn
                                log_mcp(f"Plex: Could not verify track count from response")
                                return f"Successfully added {len(track_ids)} tracks to Plex playlist ID {playlist_id}. (Note: Unable to verify exact count from Plex API response)"
                    else:
                        log_mcp(f"Plex: No metadata in response to verify track addition")
                        return f"Successfully added {len(track_ids)} tracks to Plex playlist ID {playlist_id}. (Note: Unable to verify from Plex API response)"
                except (ValueError, KeyError, AttributeError) as e:
                    log_mcp(f"Plex: Error parsing response to verify tracks: {e}")
                    return f"Successfully added {len(track_ids)} tracks to Plex playlist ID {playlist_id}. (Note: Unable to verify from Plex API response)"
                
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
