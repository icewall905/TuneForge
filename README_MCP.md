# TuneForge MCP Server

This project includes a Model Context Protocol (MCP) server that provides access to TuneForge's audio analysis features.

## Connection Details

- **Server URL:** `http://10.0.10.87:8000/mcp` (or `http://localhost:8000/mcp` locally)
- **Protocol:** MCP over HTTP Streamable (SSE + POST)

The server listens on all network interfaces (`0.0.0.0`), so you can connect using any valid IP address of this machine, including `10.0.10.87`.

## Available Tools

### `find_similar_songs`
- **Description**: Find similar songs based on audio features.
- **Arguments**:
  - `song_title` (string): The title of the song to find similarities for.
  - `artist_name` (string, optional): Artist name to narrow down the search.
  - `limit` (integer, optional): Maximum number of results (default: 5).

### `search_tracks`
- **Description**: Search for tracks on Plex or Navidrome to get their IDs.
- **Arguments**:
  - `query` (string): The search query (title, artist, etc.).
  - `platform` (string): "plex" or "navidrome" (default: "plex").
  - `limit` (integer, optional): Maximum number of results (default: 20, max: 50).
- **Note**: For Plex, searching by artist name (e.g., "Oasis") will prioritize tracks by that artist. The search first looks for an exact artist match, then retrieves all tracks from that artist.

### `create_playlist`
- **Description**: Create a new empty playlist (Navidrome only).
- **Arguments**:
  - `name` (string): Name of the playlist.
  - `platform` (string): "navidrome" (Plex requires adding items to create).

### `add_to_playlist`
- **Description**: Add tracks to a playlist.
- **Arguments**:
  - `playlist_id` (string): ID of the playlist. Use "NEW" to create a new playlist on Plex.
  - `track_ids` (list[string]): List of track IDs to add.
  - `platform` (string): "plex" or "navidrome".
  - `playlist_name` (string): Required if `playlist_id` is "NEW" (for Plex).

## n8n Integration
1. **Add "MCP Client" Node**:
   - Install the `n8n-nodes-mcp` community node if not already present.
2. **Configure Connection**:
   - **Transport**: HTTP Streamable (or SSE if supported).
   - **Server URL**: `http://10.0.10.87:8000/mcp`
3. **Select Tool**:
   - The dropdown should now show `find_similar_songs`, `search_tracks`, `create_playlist`, and `add_to_playlist`.

1. Ensure the server is running:
   ```bash
   ./start_mcp.sh
   ```

2. In n8n, use an **SSE Trigger** node (if available) or an **HTTP Request** node configured for streaming to consume the endpoint at `http://localhost:8000/sse`.
   
   *Note: Full MCP protocol support in n8n may require a dedicated MCP Client node or custom implementation to handle the JSON-RPC message exchange over SSE.*

## Connecting with other MCP Clients

Any client that supports the MCP SSE transport can connect using the URL:
`http://localhost:8000/sse`

## Troubleshooting

- **Logs:** Check the terminal where `./start_mcp.sh` is running for server logs.
- **Database:** The server uses `db/local_music.db`. Ensure this database is populated and tracks have been analyzed (features extracted) for the similarity search to work.
- **Playlist Creation:** If playlists don't appear, check:
  - Navidrome: Verify credentials in `config.ini` use `Username` and `Password` (not `User`, `Token`, `Salt`)
  - Plex: Verify `X-Plex-Token` is valid and has playlist creation permissions
  - Both: Check MCP debug logs at `/opt/tuneforge/logs/mcp_debug.log`
- **Search Issues:** 
  - If Plex search doesn't find expected tracks, verify `MusicSectionID` is correct in `config.ini`
  - For artist searches, the tool prioritizes exact artist name matches
  - Track IDs must match the platform: Plex uses numeric IDs, Navidrome uses hex IDs

## Testing

A comprehensive test script is available to verify playlist creation:
```bash
cd /opt/tuneforge
source venv/bin/activate
python debug_scripts/test_mcp_playlist_creation.py
```

This will test:
- Track search on both platforms
- Empty playlist creation (Navidrome)
- Playlist creation with tracks (both platforms)
- Verification that playlists appear in the services
