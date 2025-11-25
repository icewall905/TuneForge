"""
Integration tests for TuneForge MCP server tools.
"""
import pytest
import json
from unittest.mock import patch, Mock
import mcp_server


class TestEndToEndWorkflows:
    """End-to-end workflow tests."""
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    @patch('mcp_server.requests.put')
    def test_search_create_add_navidrome(self, mock_put, mock_get, mock_config):
        """Search tracks → Create playlist → Add tracks (Navidrome)."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        # Mock search response
        mock_search_response = Mock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = {
            'subsonic-response': {
                'status': 'ok',
                'searchResult3': {
                    'song': [
                        {'id': 'nav-1', 'title': 'Song 1', 'artist': 'Artist', 'album': 'Album'},
                        {'id': 'nav-2', 'title': 'Song 2', 'artist': 'Artist', 'album': 'Album'}
                    ]
                }
            }
        }
        mock_search_response.raise_for_status = Mock()
        
        # Mock create playlist response
        mock_create_response = Mock()
        mock_create_response.status_code = 200
        mock_create_response.json.return_value = {
            'subsonic-response': {
                'status': 'ok',
                'playlist': {'id': 'playlist-123', 'name': 'Test Playlist'}
            }
        }
        mock_create_response.raise_for_status = Mock()
        
        # Mock add to playlist response
        mock_add_response = Mock()
        mock_add_response.status_code = 200
        mock_add_response.json.return_value = {
            'subsonic-response': {'status': 'ok'}
        }
        mock_add_response.raise_for_status = Mock()
        
        mock_get.side_effect = [mock_search_response, mock_create_response, mock_add_response]
        
        # Step 1: Search tracks
        search_result = mcp_server.search_tracks("Song", platform="navidrome")
        search_data = json.loads(search_result)
        assert len(search_data) > 0
        track_ids = [track['id'] for track in search_data[:2]]
        
        # Step 2: Create playlist
        create_result = mcp_server.create_playlist("Test Playlist", platform="navidrome")
        assert "Successfully created" in create_result
        playlist_id = "playlist-123"  # From mock
        
        # Step 3: Add tracks
        add_result = mcp_server.add_to_playlist(
            playlist_id=playlist_id,
            track_ids=track_ids,
            platform="navidrome"
        )
        assert "Successfully added" in add_result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    @patch('mcp_server.requests.post')
    @patch('mcp_server.requests.put')
    def test_search_add_new_plex(self, mock_put, mock_post, mock_get, mock_config):
        """Search tracks → Add to new playlist (Plex)."""
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MusicSectionID'): '1',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        # Mock search response
        mock_search_response = Mock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = {
            'MediaContainer': {
                'Metadata': [
                    {'ratingKey': '12345', 'title': 'Song 1', 'grandparentTitle': 'Artist', 'parentTitle': 'Album'},
                    {'ratingKey': '12346', 'title': 'Song 2', 'grandparentTitle': 'Artist', 'parentTitle': 'Album'}
                ]
            }
        }
        mock_search_response.raise_for_status = Mock()
        mock_get.return_value = mock_search_response
        
        # Mock create playlist response
        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {
            'MediaContainer': {
                'Metadata': [{'ratingKey': 'playlist-789'}]
            }
        }
        mock_post_response.raise_for_status = Mock()
        mock_post.return_value = mock_post_response
        
        # Mock add tracks response
        mock_put_response = Mock()
        mock_put_response.status_code = 200
        mock_put_response.raise_for_status = Mock()
        mock_put.return_value = mock_put_response
        
        # Step 1: Search tracks
        search_result = mcp_server.search_tracks("Song", platform="plex")
        search_data = json.loads(search_result)
        assert len(search_data) > 0
        track_ids = [track['id'] for track in search_data[:2]]
        
        # Step 2: Add to new playlist
        add_result = mcp_server.add_to_playlist(
            playlist_id="NEW",
            track_ids=track_ids,
            platform="plex",
            playlist_name="New Playlist"
        )
        assert "Successfully created Plex playlist" in add_result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    @patch('mcp_server.requests.put')
    def test_find_similar_search_add(self, mock_put, mock_get, mock_config, temp_db, patch_db_path):
        """Find similar songs → Search for those songs → Add to playlist."""
        # This is a simplified test - in reality we'd need to mock the search to return
        # tracks that match the similar songs found
        
        # First, find similar songs
        similar_result = mcp_server.find_similar_songs("Bohemian Rhapsody", limit=3)
        assert "Similar songs" in similar_result or "No other tracks" in similar_result
        
        # Then search for tracks (mocked)
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MusicSectionID'): '1',
            ('PLEX', 'MachineID'): 'test-machine-id'
        }.get((s, k), d)
        
        mock_search_response = Mock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = {
            'MediaContainer': {
                'Metadata': [
                    {'ratingKey': '12345', 'title': 'Similar Song', 'grandparentTitle': 'Artist', 'parentTitle': 'Album'}
                ]
            }
        }
        mock_search_response.raise_for_status = Mock()
        mock_get.return_value = mock_search_response
        
        search_result = mcp_server.search_tracks("Similar Song", platform="plex")
        search_data = json.loads(search_result)
        
        if len(search_data) > 0:
            track_ids = [track['id'] for track in search_data]
            
            # Add to playlist
            mock_put_response = Mock()
            mock_put_response.status_code = 200
            mock_put_response.raise_for_status = Mock()
            mock_put.return_value = mock_put_response
            
            add_result = mcp_server.add_to_playlist(
                playlist_id="playlist-456",
                track_ids=track_ids,
                platform="plex"
            )
            assert "Successfully added" in add_result
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    def test_multiple_platform_operations(self, mock_get, mock_config):
        """Test multiple platform operations in sequence."""
        # Test Plex search
        mock_config.side_effect = lambda s, k, d=None: {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MusicSectionID'): '1',
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass'
        }.get((s, k), d)
        
        mock_plex_response = Mock()
        mock_plex_response.status_code = 200
        mock_plex_response.json.return_value = {
            'MediaContainer': {'Metadata': []}
        }
        mock_plex_response.raise_for_status = Mock()
        
        mock_navidrome_response = Mock()
        mock_navidrome_response.status_code = 200
        mock_navidrome_response.json.return_value = {
            'subsonic-response': {
                'status': 'ok',
                'searchResult3': {'song': []}
            }
        }
        mock_navidrome_response.raise_for_status = Mock()
        
        mock_get.side_effect = [mock_plex_response, mock_navidrome_response]
        
        # Search on Plex
        result1 = mcp_server.search_tracks("Test", platform="plex")
        assert isinstance(json.loads(result1), list)
        
        # Search on Navidrome
        result2 = mcp_server.search_tracks("Test", platform="navidrome")
        assert isinstance(json.loads(result2), list)


class TestDatabaseAPIIntegration:
    """Database + API integration tests."""
    
    @patch('mcp_server.get_config_value')
    @patch('mcp_server.requests.get')
    @patch('mcp_server.requests.put')
    def test_find_similar_search_add_workflow(self, mock_put, mock_get, mock_config, temp_db, patch_db_path):
        """find_similar_songs with real database → search_tracks → add_to_playlist."""
        # Find similar songs using test database
        similar_result = mcp_server.find_similar_songs("Bohemian Rhapsody", limit=2)
        
        # If we got results, try to search for them
        if "Similar songs" in similar_result and "Similarity:" in similar_result:
            # Mock search to return some tracks
            mock_config.side_effect = lambda s, k, d=None: {
                ('PLEX', 'ServerURL'): 'http://localhost:32400',
                ('PLEX', 'Token'): 'test-token',
                ('PLEX', 'MusicSectionID'): '1',
                ('PLEX', 'MachineID'): 'test-machine-id'
            }.get((s, k), d)
            
            mock_search_response = Mock()
            mock_search_response.status_code = 200
            mock_search_response.json.return_value = {
                'MediaContainer': {
                    'Metadata': [
                        {'ratingKey': '12345', 'title': 'Stairway to Heaven', 
                         'grandparentTitle': 'Led Zeppelin', 'parentTitle': 'Album'}
                    ]
                }
            }
            mock_search_response.raise_for_status = Mock()
            mock_get.return_value = mock_search_response
            
            # Search for one of the similar songs
            search_result = mcp_server.search_tracks("Stairway", platform="plex")
            search_data = json.loads(search_result)
            
            if len(search_data) > 0:
                track_ids = [search_data[0]['id']]
                
                # Add to playlist
                mock_put_response = Mock()
                mock_put_response.status_code = 200
                mock_put_response.raise_for_status = Mock()
                mock_put.return_value = mock_put_response
                
                add_result = mcp_server.add_to_playlist(
                    playlist_id="playlist-456",
                    track_ids=track_ids,
                    platform="plex"
                )
                assert "Successfully added" in add_result
    
    def test_data_consistency_across_operations(self, temp_db, patch_db_path):
        """Verify data consistency across operations."""
        # Find similar songs
        result1 = mcp_server.find_similar_songs("Bohemian Rhapsody", limit=1)
        
        # Find similar songs again - should be consistent
        result2 = mcp_server.find_similar_songs("Bohemian Rhapsody", limit=1)
        
        # Results should be similar (may vary slightly due to stats caching)
        assert isinstance(result1, str)
        assert isinstance(result2, str)
        # Both should either have results or the same error message
        assert ("Similar songs" in result1 and "Similar songs" in result2) or \
               ("No other tracks" in result1 and "No other tracks" in result2) or \
               ("No audio features" in result1 and "No audio features" in result2)

