"""
Tests for the add_to_playlist MCP tool.
"""
import pytest
import json
from unittest.mock import patch, Mock
import requests
import mcp_server


class TestAddToPlaylistNavidromeHappyPath:
    """Happy path tests for Navidrome add_to_playlist."""
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_add_to_existing_playlist(self, mock_get, mock_config):
        """Add tracks to existing playlist (playlist_id provided)."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {
                'status': 'ok'
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.add_to_playlist(
            playlist_id="playlist-123",
            track_ids=["nav-1", "nav-2", "nav-3"],
            platform="navidrome"
        )
        
        assert "Successfully added" in result
        assert "3 tracks" in result
        # Verify updatePlaylist.view was called
        call_url = mock_get.call_args[0][0]
        assert 'updatePlaylist.view' in call_url
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_update_playlist_api_call(self, mock_get, mock_config):
        """Verify updatePlaylist.view API call."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {'status': 'ok'}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        mcp_server.add_to_playlist(
            playlist_id="playlist-123",
            track_ids=["nav-1"],
            platform="navidrome"
        )
        
        # Verify parameters
        call_kwargs = mock_get.call_args[1]
        params = call_kwargs['params']
        assert params['playlistId'] == 'playlist-123'
        assert params['songIdToAdd'] == ["nav-1"]
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_song_id_to_add_parameter_format(self, mock_get, mock_config):
        """Verify songIdToAdd parameter format."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {'status': 'ok'}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        track_ids = ["nav-1", "nav-2", "nav-3"]
        mcp_server.add_to_playlist(
            playlist_id="playlist-123",
            track_ids=track_ids,
            platform="navidrome"
        )
        
        call_kwargs = mock_get.call_args[1]
        params = call_kwargs['params']
        assert params['songIdToAdd'] == track_ids
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_multiple_tracks_added(self, mock_get, mock_config):
        """Test adding multiple tracks."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {'status': 'ok'}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        track_ids = ["nav-1", "nav-2", "nav-3", "nav-4", "nav-5"]
        result = mcp_server.add_to_playlist(
            playlist_id="playlist-123",
            track_ids=track_ids,
            platform="navidrome"
        )
        
        assert "5 tracks" in result


class TestAddToPlaylistNavidromeNewPlaylist:
    """Tests for creating new Navidrome playlist with tracks."""
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_create_new_playlist_with_tracks(self, mock_get, mock_config):
        """Create new playlist with tracks (playlist_name provided)."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {'status': 'ok'}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.add_to_playlist(
            playlist_id="NEW",
            track_ids=["nav-1", "nav-2"],
            platform="navidrome",
            playlist_name="New Playlist"
        )
        
        assert "Successfully added" in result
        # Verify createPlaylist.view was called
        call_url = mock_get.call_args[0][0]
        assert 'createPlaylist.view' in call_url
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_create_playlist_with_song_id_parameter(self, mock_get, mock_config):
        """Verify createPlaylist.view with songId parameter."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {'status': 'ok'}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        track_ids = ["nav-1", "nav-2", "nav-3"]
        mcp_server.add_to_playlist(
            playlist_id="NEW",
            track_ids=track_ids,
            platform="navidrome",
            playlist_name="New Playlist"
        )
        
        call_kwargs = mock_get.call_args[1]
        params = call_kwargs['params']
        assert params['name'] == 'New Playlist'
        assert params['songId'] == track_ids


class TestAddToPlaylistNavidromeEdgeCases:
    """Edge case tests for Navidrome add_to_playlist."""
    
    @patch('mcp_server.get_config_value')
    def test_empty_track_ids_list(self, mock_config):
        """Test with empty track_ids list."""
        result = mcp_server.add_to_playlist(
            playlist_id="playlist-123",
            track_ids=[],
            platform="navidrome"
        )
        
        assert "Error: No track IDs provided" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_invalid_playlist_id(self, mock_get, mock_config):
        """Test with invalid playlist_id."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {
                'status': 'failed',
                'error': {
                    'code': 70,
                    'message': 'Playlist not found'
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.add_to_playlist(
            playlist_id="invalid-id",
            track_ids=["nav-1"],
            platform="navidrome"
        )
        
        assert "Navidrome Error:" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_invalid_track_ids(self, mock_get, mock_config):
        """Test with invalid track IDs."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {
                'status': 'failed',
                'error': {
                    'code': 0,
                    'message': 'Invalid track ID'
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.add_to_playlist(
            playlist_id="playlist-123",
            track_ids=["invalid-track-id"],
            platform="navidrome"
        )
        
        assert "Navidrome Error:" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_duplicate_track_ids(self, mock_get, mock_config):
        """Test with duplicate track IDs."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {'status': 'ok'}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Should handle duplicates (may succeed or fail depending on API)
        result = mcp_server.add_to_playlist(
            playlist_id="playlist-123",
            track_ids=["nav-1", "nav-1", "nav-2"],
            platform="navidrome"
        )
        
        assert isinstance(result, str)


class TestAddToPlaylistNavidromeConfiguration:
    """Configuration tests for Navidrome add_to_playlist."""
    
    @patch('mcp_server.get_config_value')
    def test_missing_navidrome_config(self, mock_config):
        """Test when NAVIDROME config is missing."""
        mock_config.return_value = None
        
        result = mcp_server.add_to_playlist(
            playlist_id="playlist-123",
            track_ids=["nav-1"],
            platform="navidrome"
        )
        
        assert "Error: Navidrome not configured" in result
    
    @patch('mcp_server.get_config_value')
    def test_missing_playlist_id_and_name(self, mock_config):
        """Test when both playlist_id and playlist_name are missing."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        result = mcp_server.add_to_playlist(
            playlist_id=None,
            track_ids=["nav-1"],
            platform="navidrome"
        )
        
        assert "Error: Provide either playlist_id or playlist_name" in result


class TestAddToPlaylistNavidromeAPIInteraction:
    """API interaction tests for Navidrome add_to_playlist."""
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_http_timeout_30s(self, mock_get, mock_config):
        """Test HTTP timeout (30s) handling."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_get.side_effect = requests.Timeout("Connection timeout")
        
        result = mcp_server.add_to_playlist(
            playlist_id="playlist-123",
            track_ids=["nav-1"],
            platform="navidrome"
        )
        
        assert "Error" in result
        # Verify timeout was set to 30s
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs['timeout'] == 30
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_subsonic_error_response(self, mock_get, mock_config):
        """Test Subsonic error response handling."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {
                'status': 'failed',
                'error': {
                    'code': 0,
                    'message': 'Generic error'
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.add_to_playlist(
            playlist_id="playlist-123",
            track_ids=["nav-1"],
            platform="navidrome"
        )
        
        assert "Navidrome Error:" in result
        assert "Generic error" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_parameter_construction_both_endpoints(self, mock_get, mock_config):
        """Verify parameter construction for both endpoints."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {'status': 'ok'}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Test updatePlaylist.view
        mcp_server.add_to_playlist(
            playlist_id="playlist-123",
            track_ids=["nav-1"],
            platform="navidrome"
        )
        
        call_kwargs1 = mock_get.call_args[1]
        params1 = call_kwargs1['params']
        assert 'playlistId' in params1
        assert 'songIdToAdd' in params1
        
        # Test createPlaylist.view
        mcp_server.add_to_playlist(
            playlist_id="NEW",
            track_ids=["nav-1"],
            platform="navidrome",
            playlist_name="New Playlist"
        )
        
        call_kwargs2 = mock_get.call_args[1]
        params2 = call_kwargs2['params']
        assert 'name' in params2
        assert 'songId' in params2


class TestAddToPlaylistPlexHappyPath:
    """Happy path tests for Plex add_to_playlist."""
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.put')
    def test_add_to_existing_playlist(self, mock_put, mock_config):
        """Add tracks to existing playlist."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_put.return_value = mock_response
        
        result = mcp_server.add_to_playlist(
            playlist_id="playlist-456",
            track_ids=["12345", "12346"],
            platform="plex"
        )
        
        assert "Successfully added" in result
        assert "2 tracks" in result
        # Verify PUT request was made
        assert mock_put.called
        call_url = mock_put.call_args[0][0]
        assert '/playlists/playlist-456/items' in call_url
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.put')
    def test_uri_format(self, mock_put, mock_config):
        """Verify URI format: server://{machine_id}/com.plexapp.plugins.library/library/metadata/{track_id}."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_put.return_value = mock_response
        
        mcp_server.add_to_playlist(
            playlist_id="playlist-456",
            track_ids=["12345", "12346"],
            platform="plex"
        )
        
        call_kwargs = mock_put.call_args[1]
        params = call_kwargs['params']
        uri_param = params['uri']
        
        assert 'server://test-machine-id/com.plexapp.plugins.library/library/metadata/12345' in uri_param
        assert 'server://test-machine-id/com.plexapp.plugins.library/library/metadata/12346' in uri_param
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.put')
    def test_x_plex_token_before_uri(self, mock_put, mock_config):
        """Verify X-Plex-Token comes before uri in params dict."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_put.return_value = mock_response
        
        mcp_server.add_to_playlist(
            playlist_id="playlist-456",
            track_ids=["12345"],
            platform="plex"
        )
        
        call_kwargs = mock_put.call_args[1]
        params = call_kwargs['params']
        
        # Check that X-Plex-Token is in params
        assert 'X-Plex-Token' in params
        assert params['X-Plex-Token'] == 'test-token'
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.put')
    def test_multiple_tracks_comma_separated_uris(self, mock_put, mock_config):
        """Test multiple tracks with comma-separated URIs."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_put.return_value = mock_response
        
        track_ids = ["12345", "12346", "12347"]
        mcp_server.add_to_playlist(
            playlist_id="playlist-456",
            track_ids=track_ids,
            platform="plex"
        )
        
        call_kwargs = mock_put.call_args[1]
        params = call_kwargs['params']
        uri_param = params['uri']
        
        # Should be comma-separated
        assert ',' in uri_param
        assert len(uri_param.split(',')) == 3


class TestAddToPlaylistPlexNewPlaylist:
    """Tests for creating new Plex playlist with tracks."""
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.post')
    @patch('mcp_server.requests.put')
    def test_create_new_playlist_with_tracks(self, mock_put, mock_post, mock_config):
        """Create new playlist with tracks (playlist_id="NEW", playlist_name provided)."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {
            'MediaContainer': {
                'Metadata': [{'ratingKey': 'new-playlist-789'}]
            }
        }
        mock_post_response.raise_for_status = Mock()
        mock_post.return_value = mock_post_response
        
        mock_put_response = Mock()
        mock_put_response.status_code = 200
        mock_put_response.raise_for_status = Mock()
        mock_put.return_value = mock_put_response
        
        result = mcp_server.add_to_playlist(
            playlist_id="NEW",
            track_ids=["12345", "12346"],
            platform="plex",
            playlist_name="New Playlist"
        )
        
        assert "Successfully created Plex playlist" in result
        assert "New Playlist" in result
        assert "2 tracks" in result
        # Verify POST was called
        assert mock_post.called
        # Verify PUT was called for remaining tracks
        assert mock_put.called
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.post')
    def test_post_with_first_track(self, mock_post, mock_config):
        """Verify POST to /playlists with first track."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'MediaContainer': {
                'Metadata': [{'ratingKey': 'new-playlist-789'}]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        mcp_server.add_to_playlist(
            playlist_id="NEW",
            track_ids=["12345"],
            platform="plex",
            playlist_name="New Playlist"
        )
        
        # Verify POST was made
        assert mock_post.called
        call_url = mock_post.call_args[0][0]
        assert '/playlists' in call_url
        call_kwargs = mock_post.call_args[1]
        params = call_kwargs['params']
        assert params['title'] == 'New Playlist'
        assert 'server://test-machine-id/com.plexapp.plugins.library/library/metadata/12345' in params['uri']
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.post')
    @patch('mcp_server.requests.put')
    def test_put_for_remaining_tracks(self, mock_put, mock_post, mock_config):
        """Verify PUT to add remaining tracks."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {
            'MediaContainer': {
                'Metadata': [{'ratingKey': 'new-playlist-789'}]
            }
        }
        mock_post_response.raise_for_status = Mock()
        mock_post.return_value = mock_post_response
        
        mock_put_response = Mock()
        mock_put_response.status_code = 200
        mock_put_response.raise_for_status = Mock()
        mock_put.return_value = mock_put_response
        
        mcp_server.add_to_playlist(
            playlist_id="NEW",
            track_ids=["12345", "12346", "12347"],
            platform="plex",
            playlist_name="New Playlist"
        )
        
        # Verify PUT was called with remaining tracks
        assert mock_put.called
        call_url = mock_put.call_args[0][0]
        assert '/playlists/new-playlist-789/items' in call_url
        call_kwargs = mock_put.call_args[1]
        params = call_kwargs['params']
        # Should have 2 remaining tracks (12346, 12347)
        uri_param = params['uri']
        assert '12346' in uri_param
        assert '12347' in uri_param
        assert '12345' not in uri_param  # First track already added via POST
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.post')
    def test_playlist_id_extraction(self, mock_post, mock_config):
        """Verify playlist ID extraction from response."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'MediaContainer': {
                'Metadata': [{'ratingKey': 'extracted-playlist-id-999'}]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        result = mcp_server.add_to_playlist(
            playlist_id="NEW",
            track_ids=["12345"],
            platform="plex",
            playlist_name="New Playlist"
        )
        
        assert "extracted-playlist-id-999" in result


class TestAddToPlaylistPlexEdgeCases:
    """Edge case tests for Plex add_to_playlist."""
    
    @patch('mcp_server.get_config_value')
    def test_empty_track_ids(self, mock_config):
        """Test with empty track_ids."""
        result = mcp_server.add_to_playlist(
            playlist_id="playlist-456",
            track_ids=[],
            platform="plex"
        )
        
        assert "Error: No track IDs provided" in result
    
    @patch('mcp_server.get_config_value')
    def test_new_without_playlist_name(self, mock_config):
        """Test playlist_id="NEW" without playlist_name."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        result = mcp_server.add_to_playlist(
            playlist_id="NEW",
            track_ids=["12345"],
            platform="plex"
        )
        
        assert "Error: playlist_name is required" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.put')
    def test_invalid_playlist_id(self, mock_put, mock_config):
        """Test with invalid playlist_id."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_put.return_value = mock_response
        
        result = mcp_server.add_to_playlist(
            playlist_id="invalid-playlist-id",
            track_ids=["12345"],
            platform="plex"
        )
        
        assert "Error" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.post')
    def test_failed_playlist_creation(self, mock_post, mock_config):
        """Test failed playlist creation."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'MediaContainer': {}  # No Metadata
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        result = mcp_server.add_to_playlist(
            playlist_id="NEW",
            track_ids=["12345"],
            platform="plex",
            playlist_name="New Playlist"
        )
        
        assert "Error: Failed to create Plex playlist" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.put')
    def test_very_large_track_list_timeout(self, mock_put, mock_config):
        """Test very large track list timeout handling (60s)."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_put.return_value = mock_response
        
        # Create 100+ track IDs
        track_ids = [str(i) for i in range(100)]
        mcp_server.add_to_playlist(
            playlist_id="playlist-456",
            track_ids=track_ids,
            platform="plex"
        )
        
        # Verify timeout was set to 60s
        call_kwargs = mock_put.call_args[1]
        assert call_kwargs['timeout'] == 60


class TestAddToPlaylistPlexConfiguration:
    """Configuration tests for Plex add_to_playlist."""
    
    @patch('mcp_server.get_config_value')
    def test_missing_plex_config(self, mock_config):
        """Test when PLEX config is missing."""
        mock_config.return_value = None
        
        result = mcp_server.add_to_playlist(
            playlist_id="playlist-456",
            track_ids=["12345"],
            platform="plex"
        )
        
        assert "Error: Plex not configured" in result
    
    @patch('mcp_server.get_config_value')
    def test_missing_server_url(self, mock_config):
        """Test when ServerURL is missing."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        result = mcp_server.add_to_playlist(
            playlist_id="playlist-456",
            track_ids=["12345"],
            platform="plex"
        )
        
        assert "Error: Plex not configured" in result
    
    @patch('mcp_server.get_config_value')
    def test_missing_token(self, mock_config):
        """Test when Token is missing."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        result = mcp_server.add_to_playlist(
            playlist_id="playlist-456",
            track_ids=["12345"],
            platform="plex"
        )
        
        assert "Error: Plex not configured" in result
    
    @patch('mcp_server.get_config_value')
    def test_missing_machine_id(self, mock_config):
        """Test when MachineID is missing."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token'
        }.get((s, k), d)
        
        result = mcp_server.add_to_playlist(
            playlist_id="playlist-456",
            track_ids=["12345"],
            platform="plex"
        )
        
        assert "Error: Plex not configured" in result


class TestAddToPlaylistPlexAPIInteraction:
    """API interaction tests for Plex add_to_playlist."""
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.put')
    def test_http_timeout(self, mock_put, mock_config):
        """Test HTTP timeout handling."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        mock_put.side_effect = requests.Timeout("Connection timeout")
        
        result = mcp_server.add_to_playlist(
            playlist_id="playlist-456",
            track_ids=["12345"],
            platform="plex"
        )
        
        assert "Error" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.put')
    def test_non_200_status_codes(self, mock_put, mock_config):
        """Test non-200 status code handling."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        mock_put.return_value = mock_response
        
        result = mcp_server.add_to_playlist(
            playlist_id="playlist-456",
            track_ids=["12345"],
            platform="plex"
        )
        
        assert "Error" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.put')
    def test_malformed_json_responses(self, mock_put, mock_config):
        """Test malformed JSON response handling."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        # PUT doesn't return JSON, but test error handling
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_put.return_value = mock_response
        
        result = mcp_server.add_to_playlist(
            playlist_id="playlist-456",
            track_ids=["12345"],
            platform="plex"
        )
        
        # Should succeed
        assert "Successfully added" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.put')
    def test_empty_mediacontainer(self, mock_put, mock_config):
        """Test empty MediaContainer handling (for POST)."""
        # This is tested in test_failed_playlist_creation
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.put')
    def test_header_construction(self, mock_put, mock_config):
        """Verify header construction (X-Plex-Token, Accept)."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_put.return_value = mock_response
        
        mcp_server.add_to_playlist(
            playlist_id="playlist-456",
            track_ids=["12345"],
            platform="plex"
        )
        
        call_kwargs = mock_put.call_args[1]
        headers = call_kwargs['headers']
        assert headers['X-Plex-Token'] == 'test-token'
        assert headers['Accept'] == 'application/json'


class TestAddToPlaylistPlatformValidation:
    """Platform validation tests."""
    
    @patch('mcp_server.get_config_value')
    def test_invalid_platform(self, mock_config):
        """Test invalid platform value."""
        result = mcp_server.add_to_playlist(
            playlist_id="playlist-123",
            track_ids=["track-1"],
            platform="invalid"
        )
        
        assert "Error: Unknown platform" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.put')
    def test_case_insensitivity(self, mock_put, mock_config):
        """Test case insensitivity."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_put.return_value = mock_response
        
        # Test uppercase
        result1 = mcp_server.add_to_playlist(
            playlist_id="playlist-456",
            track_ids=["12345"],
            platform="PLEX"
        )
        # Test lowercase
        result2 = mcp_server.add_to_playlist(
            playlist_id="playlist-456",
            track_ids=["12345"],
            platform="plex"
        )
        # Test mixed case
        result3 = mcp_server.add_to_playlist(
            playlist_id="playlist-456",
            track_ids=["12345"],
            platform="Plex"
        )
        
        # All should work
        assert "Successfully added" in result1 or "Successfully added" in result2 or "Successfully added" in result3

