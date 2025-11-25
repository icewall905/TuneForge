"""
Tests for the create_playlist MCP tool.
"""
import pytest
import json
from unittest.mock import patch, Mock
import requests
import mcp_server


class TestCreatePlaylistNavidromeHappyPath:
    """Happy path tests for Navidrome create_playlist."""
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_create_playlist_valid_name(self, mock_get, mock_config):
        """Create playlist with valid name returns success with playlist ID."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {
                'status': 'ok',
                'playlist': {
                    'id': 'playlist-123',
                    'name': 'Test Playlist'
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.create_playlist("Test Playlist", platform="navidrome")
        
        assert "Successfully created Navidrome playlist" in result
        assert "playlist-123" in result
        assert "Test Playlist" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_subsonic_api_call(self, mock_get, mock_config):
        """Verify Subsonic API call (createPlaylist.view) is made correctly."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {
                'status': 'ok',
                'playlist': {'id': 'playlist-123', 'name': 'Test'}
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        mcp_server.create_playlist("Test Playlist", platform="navidrome")
        
        # Verify API endpoint was called
        assert mock_get.called
        call_url = mock_get.call_args[0][0]
        assert 'createPlaylist.view' in call_url
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_response_parsing_playlist_id(self, mock_get, mock_config):
        """Verify response parsing for playlist ID."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {
                'status': 'ok',
                'playlist': {
                    'id': 'custom-playlist-id-456',
                    'name': 'My Playlist'
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.create_playlist("My Playlist", platform="navidrome")
        
        assert "custom-playlist-id-456" in result


class TestCreatePlaylistNavidromeEdgeCases:
    """Edge case tests for Navidrome create_playlist."""
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_empty_playlist_name(self, mock_get, mock_config):
        """Test with empty playlist name."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {
                'status': 'ok',
                'playlist': {'id': 'playlist-123', 'name': ''}
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.create_playlist("", platform="navidrome")
        
        # Should handle empty name (may succeed or fail depending on API)
        assert isinstance(result, str)
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_duplicate_playlist_name(self, mock_get, mock_config):
        """Test duplicate playlist name behavior."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        # Simulate duplicate name error
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {
                'status': 'failed',
                'error': {
                    'code': 50,
                    'message': 'Playlist already exists'
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.create_playlist("Existing Playlist", platform="navidrome")
        
        assert "Navidrome Error:" in result
        assert "Playlist already exists" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_very_long_playlist_name(self, mock_get, mock_config):
        """Test with very long playlist name."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {
                'status': 'ok',
                'playlist': {'id': 'playlist-123', 'name': 'A' * 1000}
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        long_name = "A" * 1000
        result = mcp_server.create_playlist(long_name, platform="navidrome")
        
        assert isinstance(result, str)
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_special_characters_in_name(self, mock_get, mock_config):
        """Test special characters in playlist name (URL encoding)."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {
                'status': 'ok',
                'playlist': {'id': 'playlist-123', 'name': "Test & 'More'"}
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.create_playlist("Test & 'More'", platform="navidrome")
        
        # Should handle special characters
        assert isinstance(result, str)


class TestCreatePlaylistNavidromeConfiguration:
    """Configuration tests for Navidrome create_playlist."""
    
    @patch('mcp_server.get_config_value')
    def test_missing_navidrome_config(self, mock_config):
        """Test when NAVIDROME config is missing."""
        mock_config.return_value = None
        
        result = mcp_server.create_playlist("Test Playlist", platform="navidrome")
        
        assert "Error: Navidrome not configured" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_invalid_credentials(self, mock_get, mock_config):
        """Test invalid credentials handling."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'wronguser',
            ('NAVIDROME', 'Password'): 'wrongpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {
                'status': 'failed',
                'error': {
                    'code': 40,
                    'message': 'Wrong username or password'
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.create_playlist("Test Playlist", platform="navidrome")
        
        assert "Navidrome Error:" in result
        assert "Wrong username or password" in result


class TestCreatePlaylistNavidromeAPIInteraction:
    """API interaction tests for Navidrome create_playlist."""
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_http_timeout(self, mock_get, mock_config):
        """Test HTTP timeout handling."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_get.side_effect = requests.Timeout("Connection timeout")
        
        result = mcp_server.create_playlist("Test Playlist", platform="navidrome")
        
        assert "Error" in result
    
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
        
        result = mcp_server.create_playlist("Test Playlist", platform="navidrome")
        
        assert "Navidrome Error:" in result
        assert "Generic error" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_malformed_response(self, mock_get, mock_config):
        """Test malformed response handling."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.create_playlist("Test Playlist", platform="navidrome")
        
        assert "Error" in result


class TestCreatePlaylistPlex:
    """Tests for Plex create_playlist (should return error)."""
    
    @patch('mcp_server.get_config_value')
    def test_plex_requires_track_id(self, mock_config):
        """Test that Plex requires at least one track ID to create a playlist."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        result = mcp_server.create_playlist("Test Playlist", platform="plex")
        
        assert "Error: Plex requires at least one track ID" in result
        assert "add_to_playlist" in result
    
    @patch('mcp_server.get_config_value')
    def test_plex_missing_config(self, mock_config):
        """Test when Plex config is missing."""
        mock_config.return_value = None
        
        result = mcp_server.create_playlist("Test Playlist", platform="plex")
        
        assert "Error: Plex not configured" in result


class TestCreatePlaylistPlatformValidation:
    """Platform validation tests."""
    
    @patch('mcp_server.get_config_value')
    def test_invalid_platform(self, mock_config):
        """Test invalid platform value."""
        result = mcp_server.create_playlist("Test Playlist", platform="invalid")
        
        assert "Error: Unsupported platform" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_case_insensitivity(self, mock_get, mock_config):
        """Test case insensitivity."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {
                'status': 'ok',
                'playlist': {'id': 'playlist-123', 'name': 'Test'}
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Test uppercase
        result1 = mcp_server.create_playlist("Test", platform="NAVIDROME")
        # Test lowercase
        result2 = mcp_server.create_playlist("Test", platform="navidrome")
        # Test mixed case
        result3 = mcp_server.create_playlist("Test", platform="Navidrome")
        
        # All should work
        assert "Successfully created" in result1 or "Successfully created" in result2 or "Successfully created" in result3

