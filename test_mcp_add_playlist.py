import sys
import os

# Add current directory to path
sys.path.append('/opt/tuneforge')

from mcp_server import add_to_playlist

# Test parameters (same as reproduction script)
playlist_name = "Test Playlist MCP Direct"
# Use the track ID found in previous step: 399221
track_ids = ['399221']
platform = "plex"
playlist_id = "NEW"

print(f"Testing add_to_playlist with: {playlist_name}, {track_ids}")

result = add_to_playlist(playlist_id=playlist_id, track_ids=track_ids, platform=platform, playlist_name=playlist_name)
print(f"Result: {result}")
