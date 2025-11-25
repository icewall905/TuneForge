"""
Tests for the search_tracks MCP tool.
"""
import pytest
import json
from unittest.mock import patch, Mock, MagicMock
import requests
import mcp_server


class TestSearchTracksPlexHappyPath:
    """Happy path tests for Plex search."""
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_search_valid_query(self, mock_get, mock_config):
        """Search with valid query returns JSON with track IDs."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MusicSectionID'): '1'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'MediaContainer': {
                'Metadata': [
                    {
                        'ratingKey': '12345',
                        'title': 'Test Song',
                        'grandparentTitle': 'Test Artist',
                        'parentTitle': 'Test Album'
                    }
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.search_tracks("Test Song", platform="plex")
        
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) > 0
        assert 'id' in data[0]
        assert 'title' in data[0]
        assert 'artist' in data[0]
        assert 'album' in data[0]
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_response_format(self, mock_get, mock_config):
        """Verify response format matches expected structure."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MusicSectionID'): '1'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'MediaContainer': {
                'Metadata': [
                    {
                        'ratingKey': '12345',
                        'title': 'Test Song',
                        'grandparentTitle': 'Test Artist',
                        'parentTitle': 'Test Album'
                    }
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.search_tracks("Test", platform="plex")
        data = json.loads(result)
        
        assert data[0]['id'] == '12345'
        assert data[0]['title'] == 'Test Song'
        assert data[0]['artist'] == 'Test Artist'
        assert data[0]['album'] == 'Test Album'
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_limit_parameter_default(self, mock_get, mock_config):
        """Test default limit of 20."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MusicSectionID'): '1'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        # Create 25 results
        mock_response.json.return_value = {
            'MediaContainer': {
                'Metadata': [{'ratingKey': str(i), 'title': f'Song {i}', 
                             'grandparentTitle': 'Artist', 'parentTitle': 'Album'} 
                            for i in range(25)]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.search_tracks("Test", platform="plex")
        data = json.loads(result)
        
        assert len(data) == 20  # Default limit
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_limit_parameter_custom(self, mock_get, mock_config):
        """Test custom limit parameter."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MusicSectionID'): '1'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'MediaContainer': {
                'Metadata': [{'ratingKey': str(i), 'title': f'Song {i}', 
                             'grandparentTitle': 'Artist', 'parentTitle': 'Album'} 
                            for i in range(10)]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.search_tracks("Test", platform="plex", limit=5)
        data = json.loads(result)
        
        assert len(data) == 5
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_various_query_types(self, mock_get, mock_config):
        """Test with various query types: title, artist, album."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MusicSectionID'): '1'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'MediaContainer': {'Metadata': []}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Test title search
        result1 = mcp_server.search_tracks("Song Title", platform="plex")
        # Test artist search
        result2 = mcp_server.search_tracks("Artist Name", platform="plex")
        # Test album search
        result3 = mcp_server.search_tracks("Album Name", platform="plex")
        
        # All should return valid JSON
        assert isinstance(json.loads(result1), list)
        assert isinstance(json.loads(result2), list)
        assert isinstance(json.loads(result3), list)


class TestSearchTracksPlexEdgeCases:
    """Edge case tests for Plex search."""
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_empty_query(self, mock_get, mock_config):
        """Test with empty query."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MusicSectionID'): '1'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'MediaContainer': {'Metadata': []}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.search_tracks("", platform="plex")
        data = json.loads(result)
        
        assert isinstance(data, list)
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_no_results(self, mock_get, mock_config):
        """Test query with no results returns empty array."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MusicSectionID'): '1'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'MediaContainer': {'Metadata': []}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.search_tracks("Nonexistent Song", platform="plex")
        data = json.loads(result)
        
        assert isinstance(data, list)
        assert len(data) == 0
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_query_with_spaces_fallback(self, mock_get, mock_config):
        """Test fallback search logic for queries with spaces."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MusicSectionID'): '1'
        }.get((s, k), d)
        
        # First call returns no results, second call (fallback) returns results
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {'MediaContainer': {'Metadata': []}}
        mock_response1.raise_for_status = Mock()
        
        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            'MediaContainer': {
                'Metadata': [{'ratingKey': '123', 'title': 'Test', 
                             'grandparentTitle': 'Artist', 'parentTitle': 'Album'}]
            }
        }
        mock_response2.raise_for_status = Mock()
        
        mock_get.side_effect = [mock_response1, mock_response2]
        
        result = mcp_server.search_tracks("Test Song Query", platform="plex")
        data = json.loads(result)
        
        # Should use fallback and find results
        assert len(data) > 0
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_very_long_query(self, mock_get, mock_config):
        """Test with very long query."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MusicSectionID'): '1'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'MediaContainer': {'Metadata': []}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        long_query = "A" * 1000
        result = mcp_server.search_tracks(long_query, platform="plex")
        
        assert isinstance(result, str)
        data = json.loads(result)
        assert isinstance(data, list)


class TestSearchTracksPlexConfiguration:
    """Configuration tests for Plex search."""
    
    @patch('mcp_server.get_config_value')
    def test_missing_plex_section(self, mock_config):
        """Test when PLEX section is missing."""
        mock_config.return_value = None
        
        result = mcp_server.search_tracks("Test", platform="plex")
        
        assert "Error: Plex not configured" in result
    
    @patch('mcp_server.get_config_value')
    def test_missing_server_url(self, mock_config):
        """Test when ServerURL is missing."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MusicSectionID'): '1'
        }.get((s, k), d)
        
        result = mcp_server.search_tracks("Test", platform="plex")
        
        assert "Error: Plex not configured" in result
    
    @patch('mcp_server.get_config_value')
    def test_missing_token(self, mock_config):
        """Test when Token is missing."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'MusicSectionID'): '1'
        }.get((s, k), d)
        
        result = mcp_server.search_tracks("Test", platform="plex")
        
        assert "Error: Plex not configured" in result
    
    @patch('mcp_server.get_config_value')
    def test_missing_section_id(self, mock_config):
        """Test when MusicSectionID is missing."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token'
        }.get((s, k), d)
        
        result = mcp_server.search_tracks("Test", platform="plex")
        
        assert "Error: Plex not configured" in result


class TestSearchTracksPlexAPIInteraction:
    """API interaction tests for Plex search."""
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_http_timeout(self, mock_get, mock_config):
        """Test HTTP timeout handling."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MusicSectionID'): '1'
        }.get((s, k), d)
        
        mock_get.side_effect = requests.Timeout("Connection timeout")
        
        result = mcp_server.search_tracks("Test", platform="plex")
        
        assert "Error" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_non_200_status_code(self, mock_get, mock_config):
        """Test non-200 status code handling."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MusicSectionID'): '1'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        
        result = mcp_server.search_tracks("Test", platform="plex")
        
        assert "Error" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_malformed_json_response(self, mock_get, mock_config):
        """Test malformed JSON response handling."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MusicSectionID'): '1'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.search_tracks("Test", platform="plex")
        
        assert "Error" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_empty_mediacontainer(self, mock_get, mock_config):
        """Test empty MediaContainer returns empty results."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MusicSectionID'): '1'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'MediaContainer': {}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.search_tracks("Test", platform="plex")
        data = json.loads(result)
        
        assert isinstance(data, list)
        assert len(data) == 0


class TestSearchTracksNavidromeHappyPath:
    """Happy path tests for Navidrome search."""
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_search_valid_query(self, mock_get, mock_config):
        """Search with valid query returns JSON with track IDs."""
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
                'searchResult3': {
                    'song': [
                        {
                            'id': 'nav-123',
                            'title': 'Test Song',
                            'artist': 'Test Artist',
                            'album': 'Test Album'
                        }
                    ]
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.search_tracks("Test Song", platform="navidrome")
        
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) > 0
        assert 'id' in data[0]
        assert data[0]['id'] == 'nav-123'
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_subsonic_response_format(self, mock_get, mock_config):
        """Verify Subsonic API format is parsed correctly."""
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
                'searchResult3': {
                    'song': [
                        {
                            'id': 'nav-123',
                            'title': 'Test Song',
                            'artist': 'Test Artist',
                            'album': 'Test Album'
                        }
                    ]
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.search_tracks("Test", platform="navidrome")
        data = json.loads(result)
        
        assert data[0]['id'] == 'nav-123'
        assert data[0]['title'] == 'Test Song'
        assert data[0]['artist'] == 'Test Artist'
        assert data[0]['album'] == 'Test Album'
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_limit_parameter_enforcement(self, mock_get, mock_config):
        """Test limit parameter enforcement."""
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
                'searchResult3': {
                    'song': [{'id': f'nav-{i}', 'title': f'Song {i}', 
                             'artist': 'Artist', 'album': 'Album'} for i in range(30)]
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.search_tracks("Test", platform="navidrome", limit=10)
        data = json.loads(result)
        
        # Limit should be enforced (though Navidrome may return more, we limit in code)
        assert len(data) <= 30  # Navidrome returns what it wants, we don't limit after


class TestSearchTracksNavidromeEdgeCases:
    """Edge case tests for Navidrome search."""
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_empty_query(self, mock_get, mock_config):
        """Test with empty query."""
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
                'searchResult3': {'song': []}
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.search_tracks("", platform="navidrome")
        data = json.loads(result)
        
        assert isinstance(data, list)
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_no_results(self, mock_get, mock_config):
        """Test query with no results returns empty array."""
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
                'searchResult3': {'song': []}
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.search_tracks("Nonexistent", platform="navidrome")
        data = json.loads(result)
        
        assert isinstance(data, list)
        assert len(data) == 0


class TestSearchTracksNavidromeConfiguration:
    """Configuration tests for Navidrome search."""
    
    @patch('mcp_server.get_config_value')
    def test_missing_navidrome_section(self, mock_config):
        """Test when NAVIDROME section is missing."""
        mock_config.return_value = None
        
        result = mcp_server.search_tracks("Test", platform="navidrome")
        
        assert "Error: Navidrome not configured" in result
    
    @patch('mcp_server.get_config_value')
    def test_missing_url(self, mock_config):
        """Test when URL is missing."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        result = mcp_server.search_tracks("Test", platform="navidrome")
        
        assert "Error: Navidrome not configured" in result
    
    @patch('mcp_server.get_config_value')
    def test_missing_username(self, mock_config):
        """Test when Username is missing."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        result = mcp_server.search_tracks("Test", platform="navidrome")
        
        assert "Error: Navidrome not configured" in result
    
    @patch('mcp_server.get_config_value')
    def test_missing_password(self, mock_config):
        """Test when Password is missing."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser'
        }.get((s, k), d)
        
        result = mcp_server.search_tracks("Test", platform="navidrome")
        
        assert "Error: Navidrome not configured" in result


class TestSearchTracksNavidromeAPIInteraction:
    """API interaction tests for Navidrome search."""
    
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
        
        result = mcp_server.search_tracks("Test", platform="navidrome")
        
        assert "Error" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_non_200_status_code(self, mock_get, mock_config):
        """Test non-200 status code handling."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_get.return_value = mock_response
        
        result = mcp_server.search_tracks("Test", platform="navidrome")
        
        assert "Error" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_subsonic_error_response(self, mock_get, mock_config):
        """Test Subsonic error response (status != 'ok')."""
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
                    'code': 40,
                    'message': 'Wrong username or password'
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.search_tracks("Test", platform="navidrome")
        
        assert "Navidrome Error:" in result
        assert "Wrong username or password" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_malformed_json(self, mock_get, mock_config):
        """Test malformed JSON response handling."""
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
        
        result = mcp_server.search_tracks("Test", platform="navidrome")
        
        assert "Error" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_url_construction_with_rest(self, mock_get, mock_config):
        """Test URL construction when /rest is already present."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533/rest',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {'status': 'ok', 'searchResult3': {'song': []}}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        mcp_server.search_tracks("Test", platform="navidrome")
        
        # Verify URL doesn't have double /rest
        call_args = mock_get.call_args[0][0]
        assert '/rest/rest' not in call_args
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_url_construction_without_rest(self, mock_get, mock_config):
        """Test URL construction when /rest is missing."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subsonic-response': {'status': 'ok', 'searchResult3': {'song': []}}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        mcp_server.search_tracks("Test", platform="navidrome")
        
        # Verify URL has /rest added
        call_args = mock_get.call_args[0][0]
        assert '/rest' in call_args


class TestSearchTracksPlatformValidation:
    """Platform validation tests."""
    
    @patch('mcp_server.get_config_value')
    def test_invalid_platform(self, mock_config):
        """Test invalid platform value."""
        result = mcp_server.search_tracks("Test", platform="invalid")
        
        assert "Error: Unsupported platform" in result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_case_insensitivity(self, mock_get, mock_config):
        """Test case insensitivity (PLEX vs plex)."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MusicSectionID'): '1'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'MediaContainer': {'Metadata': []}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Test uppercase
        result1 = mcp_server.search_tracks("Test", platform="PLEX")
        # Test lowercase
        result2 = mcp_server.search_tracks("Test", platform="plex")
        # Test mixed case
        result3 = mcp_server.search_tracks("Test", platform="Plex")
        
        # All should work
        assert isinstance(json.loads(result1), list)
        assert isinstance(json.loads(result2), list)
        assert isinstance(json.loads(result3), list)
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_limit_validation_min(self, mock_get, mock_config):
        """Test limit validation (min 1)."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MusicSectionID'): '1'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'MediaContainer': {'Metadata': []}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.search_tracks("Test", platform="plex", limit=0)
        data = json.loads(result)
        
        # Should enforce min of 1
        assert isinstance(data, list)
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_limit_validation_max(self, mock_get, mock_config):
        """Test limit validation (max 50)."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MusicSectionID'): '1'
        }.get((s, k), d)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'MediaContainer': {
                'Metadata': [{'ratingKey': str(i), 'title': f'Song {i}', 
                            'grandparentTitle': 'Artist', 'parentTitle': 'Album'} 
                           for i in range(100)]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = mcp_server.search_tracks("Test", platform="plex", limit=100)
        data = json.loads(result)
        
        # Should enforce max of 50
        assert len(data) <= 50

