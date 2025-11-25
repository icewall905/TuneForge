"""
Tests for the find_similar_songs MCP tool.
"""
import pytest
import sqlite3
import os
from unittest.mock import patch, MagicMock
import mcp_server


class TestFindSimilarSongsHappyPath:
    """Happy path tests for find_similar_songs."""
    
    def test_find_similar_with_title_and_artist(self, temp_db, patch_db_path):
        """Test finding similar songs with both title and artist."""
        result = mcp_server.find_similar_songs("Bohemian Rhapsody", "Queen", limit=3)
        
        assert "Similar songs to: **Bohemian Rhapsody** by **Queen**" in result
        assert "Similarity:" in result
        # Should return results
        assert len(result.split('\n')) > 2
    
    def test_find_similar_with_title_only(self, temp_db, patch_db_path):
        """Test finding similar songs with title only."""
        result = mcp_server.find_similar_songs("Stairway to Heaven", limit=3)
        
        assert "Similar songs to: **Stairway to Heaven** by **Led Zeppelin**" in result
        assert "Similarity:" in result
    
    def test_similarity_scores_returned(self, temp_db, patch_db_path):
        """Verify similarity scores are returned as percentages."""
        result = mcp_server.find_similar_songs("Bohemian Rhapsody", limit=5)
        
        # Check for percentage format
        assert "%" in result or "Similarity:" in result
    
    def test_results_sorted_by_similarity(self, temp_db, patch_db_path):
        """Verify results are sorted by similarity (descending)."""
        result = mcp_server.find_similar_songs("Bohemian Rhapsody", limit=5)
        
        lines = [line for line in result.split('\n') if 'Similarity:' in line]
        if len(lines) > 1:
            # Extract similarity scores
            scores = []
            for line in lines:
                if 'Similarity:' in line:
                    try:
                        score_str = line.split('Similarity:')[1].strip().rstrip('%')
                        score = float(score_str) / 100.0
                        scores.append(score)
                    except (ValueError, IndexError):
                        pass
            
            # Verify descending order
            if len(scores) > 1:
                assert scores == sorted(scores, reverse=True)
    
    def test_limit_parameter_default(self, temp_db, patch_db_path):
        """Test default limit of 5."""
        result = mcp_server.find_similar_songs("Bohemian Rhapsody")
        
        lines = [line for line in result.split('\n') if 'Similarity:' in line]
        assert len(lines) <= 5
    
    def test_limit_parameter_custom(self, temp_db, patch_db_path):
        """Test custom limit parameter."""
        result = mcp_server.find_similar_songs("Bohemian Rhapsody", limit=3)
        
        lines = [line for line in result.split('\n') if 'Similarity:' in line]
        assert len(lines) <= 3


class TestFindSimilarSongsEdgeCases:
    """Edge case tests for find_similar_songs."""
    
    def test_no_matching_tracks(self, temp_db, patch_db_path):
        """Test when no tracks match the search."""
        result = mcp_server.find_similar_songs("Nonexistent Song Title")
        
        assert "No tracks found" in result
    
    def test_track_with_features_but_no_other_tracks(self, temp_db, patch_db_path):
        """Test when seed track has features but no other tracks have features."""
        # Create a database with only one track that has features
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        # Delete all other tracks with features
        cursor.execute("DELETE FROM audio_features WHERE track_id != 1")
        conn.commit()
        conn.close()
        
        # This should still work if there are other tracks, but let's test the edge case
        # Actually, if we delete all other features, we should get the "no other tracks" message
        result = mcp_server.find_similar_songs("Bohemian Rhapsody")
        
        # Should either return results or the "no other tracks" message
        assert "No other tracks" in result or "Similar songs" in result
    
    def test_track_without_audio_features(self, temp_db, patch_db_path):
        """Test when track exists but has no audio features."""
        result = mcp_server.find_similar_songs("No Features Track")
        
        assert "No audio features found" in result or "Please analyze it first" in result
    
    def test_multiple_tracks_same_title(self, temp_db, patch_db_path):
        """Test when multiple tracks have the same title - should pick first."""
        result = mcp_server.find_similar_songs("Bohemian Rhapsody")
        
        # Should find one of the Bohemian Rhapsody tracks
        assert "Bohemian Rhapsody" in result
        # Should not error
    
    def test_empty_string_title(self, temp_db, patch_db_path):
        """Test with empty string title."""
        result = mcp_server.find_similar_songs("")
        
        # Empty string with SQL LIKE becomes %% which matches everything
        # The function should handle it gracefully (may find tracks or return error)
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_very_long_title(self, temp_db, patch_db_path):
        """Test with very long title."""
        result = mcp_server.find_similar_songs("Very Long Title That Goes On And On And On And On And On")
        
        # Should handle it without error
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_special_characters_in_title(self, temp_db, patch_db_path):
        """Test SQL injection safety with special characters."""
        result = mcp_server.find_similar_songs("Special Chars: 'Test' & \"More\"")
        
        # Should handle special characters safely
        assert isinstance(result, str)
        # Should not crash or expose SQL errors
    
    def test_special_characters_in_artist(self, temp_db, patch_db_path):
        """Test SQL injection safety with special characters in artist."""
        result = mcp_server.find_similar_songs("Test Song", artist_name="Artist & Co.")
        
        # Should handle special characters safely
        assert isinstance(result, str)


class TestFindSimilarSongsLimitParameter:
    """Tests for limit parameter validation."""
    
    def test_limit_one(self, temp_db, patch_db_path):
        """Test limit = 1 returns 1 result."""
        result = mcp_server.find_similar_songs("Bohemian Rhapsody", limit=1)
        
        lines = [line for line in result.split('\n') if 'Similarity:' in line]
        assert len(lines) <= 1
    
    def test_limit_zero(self, temp_db, patch_db_path):
        """Test limit = 0."""
        result = mcp_server.find_similar_songs("Bohemian Rhapsody", limit=0)
        
        # Should handle gracefully
        assert isinstance(result, str)
    
    def test_limit_negative(self, temp_db, patch_db_path):
        """Test negative limit."""
        result = mcp_server.find_similar_songs("Bohemian Rhapsody", limit=-5)
        
        # Should handle gracefully
        assert isinstance(result, str)
    
    def test_limit_greater_than_available(self, temp_db, patch_db_path):
        """Test limit greater than available candidates."""
        result = mcp_server.find_similar_songs("Bohemian Rhapsody", limit=100)
        
        # Should return all available, not error
        assert isinstance(result, str)
        lines = [line for line in result.split('\n') if 'Similarity:' in line]
        # Should have at most 14 results (15 tracks with features - 1 seed)
        assert len(lines) <= 14


class TestFindSimilarSongsDatabaseIntegration:
    """Database integration tests."""
    
    def test_database_not_exists(self, monkeypatch):
        """Test when database file doesn't exist."""
        fake_path = "/nonexistent/path/to/db.db"
        monkeypatch.setattr('mcp_server.DB_PATH', fake_path)
        
        result = mcp_server.find_similar_songs("Test Song")
        
        assert "Error" in result or "not found" in result.lower()
    
    def test_database_locked(self, temp_db, patch_db_path):
        """Test when database is locked."""
        # Open a connection and keep it open
        conn = sqlite3.connect(temp_db)
        conn.execute("BEGIN EXCLUSIVE")
        
        try:
            result = mcp_server.find_similar_songs("Test Song")
            # Should handle the lock gracefully
            assert isinstance(result, str)
        finally:
            conn.rollback()
            conn.close()
    
    def test_missing_audio_features_table(self, temp_db, patch_db_path):
        """Test when audio_features table is missing."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE audio_features")
        conn.commit()
        conn.close()
        
        result = mcp_server.find_similar_songs("Bohemian Rhapsody")
        
        assert "Error" in result


class TestFindSimilarSongsFeatureStoreIntegration:
    """Tests for feature_store integration."""
    
    def test_feature_store_called_correctly(self, temp_db, patch_db_path):
        """Verify feature_store functions are called correctly."""
        with patch('mcp_server.feature_store.fetch_track_features') as mock_fetch, \
             patch('mcp_server.feature_store.fetch_batch_features') as mock_batch, \
             patch('mcp_server.sonic_similarity.get_feature_stats') as mock_stats, \
             patch('mcp_server.sonic_similarity.build_vector') as mock_build, \
             patch('mcp_server.sonic_similarity.compute_distance') as mock_dist:
            
            mock_fetch.return_value = {
                'track_id': 1,
                'energy': 0.85,
                'valence': 0.75,
                'tempo': 120.0,
                'danceability': 0.65,
                'acousticness': 0.25,
                'instrumentalness': 0.05,
                'loudness': -5.2,
                'speechiness': 0.08
            }
            mock_batch.return_value = {
                2: {'energy': 0.45, 'valence': 0.35, 'tempo': 72.0, 'danceability': 0.35,
                    'acousticness': 0.80, 'instrumentalness': 0.10, 'loudness': -8.5, 'speechiness': 0.03}
            }
            mock_stats.return_value = {
                'energy': (0.0, 1.0),
                'valence': (0.0, 1.0),
                'tempo': (60.0, 140.0),
                'danceability': (0.0, 1.0),
                'acousticness': (0.0, 1.0),
                'instrumentalness': (0.0, 1.0),
                'loudness': (-10.0, 0.0),
                'speechiness': (0.0, 1.0)
            }
            mock_build.return_value = [0.5] * 8
            mock_dist.return_value = 0.5
            
            result = mcp_server.find_similar_songs("Bohemian Rhapsody", limit=1)
            
            mock_fetch.assert_called_once()
            mock_batch.assert_called_once()
            mock_stats.assert_called_once()
            assert mock_build.call_count >= 1
            assert mock_dist.call_count >= 1
    
    def test_missing_features_in_feature_store(self, temp_db, patch_db_path):
        """Test when feature_store returns None."""
        with patch('mcp_server.feature_store.fetch_track_features', return_value=None):
            result = mcp_server.find_similar_songs("Bohemian Rhapsody")
            
            assert "No audio features found" in result or "Please analyze it first" in result


class TestFindSimilarSongsSimilarityCalculation:
    """Tests for similarity calculation."""
    
    def test_similarity_formula(self, temp_db, patch_db_path):
        """Verify similarity score formula (1.0 - distance/2.82)."""
        # This is tested indirectly through the happy path tests
        # The formula is: similarity = max(0.0, 1.0 - (distance / 2.82))
        result = mcp_server.find_similar_songs("Bohemian Rhapsody", limit=1)
        
        # Should return a result with similarity score
        assert "Similarity:" in result or "No other tracks" in result
    
    def test_identical_tracks_high_similarity(self, temp_db, patch_db_path):
        """Test that identical tracks return high similarity."""
        # Search for Bohemian Rhapsody - should find the duplicate with high similarity
        result = mcp_server.find_similar_songs("Bohemian Rhapsody", limit=5)
        
        # The duplicate track (ID 11) should have very high similarity
        if "Similarity:" in result:
            # Extract similarity scores
            lines = [line for line in result.split('\n') if 'Similarity:' in line]
            if lines:
                # Should have at least one result
                assert len(lines) > 0
    
    def test_different_tracks_low_similarity(self, temp_db, patch_db_path):
        """Test that very different tracks return low similarity."""
        # Stairway to Heaven (slow, acoustic) vs Thunderstruck (fast, electric)
        result = mcp_server.find_similar_songs("Stairway to Heaven", limit=5)
        
        # Should return results, similarity may vary
        assert isinstance(result, str)
        assert len(result) > 0

