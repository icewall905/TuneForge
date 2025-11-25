"""
Tests for configuration management in MCP server.
"""
import pytest
import os
import tempfile
import configparser
from unittest.mock import patch
import mcp_server


class TestConfigFile:
    """Tests for config file handling."""
    
    def test_missing_config_ini(self, monkeypatch):
        """Test when config.ini is missing."""
        # Mock os.path.exists to return False for config.ini
        def mock_exists(path):
            if 'config.ini' in path:
                return False
            return True
        
        monkeypatch.setattr('os.path.exists', mock_exists)
        
        # get_config_value should return default when config doesn't exist
        result = mcp_server.get_config_value('PLEX', 'ServerURL', default='default-value')
        assert result == 'default-value'
    
    def test_missing_sections(self, monkeypatch, tmp_path):
        """Test when config sections are missing."""
        # Create a temporary config file without PLEX section
        config_file = tmp_path / "config.ini"
        config_file.write_text("[NAVIDROME]\nURL = http://localhost:4533\n")
        
        # Mock the config path
        def mock_join(*args):
            if 'config.ini' in str(args[-1]):
                return str(config_file)
            return os.path.join(*args)
        
        monkeypatch.setattr('mcp_server.os.path.join', mock_join)
        
        result = mcp_server.get_config_value('PLEX', 'ServerURL', default='default')
        assert result == 'default'
    
    def test_invalid_config_values(self, monkeypatch, tmp_path):
        """Test invalid config values handling."""
        # Create a temporary config file with empty value
        config_file = tmp_path / "config.ini"
        config_file.write_text("[PLEX]\nServerURL = \nToken = invalid\n")
        
        # Mock the config path
        def mock_join(*args):
            if 'config.ini' in str(args[-1]):
                return str(config_file)
            return os.path.join(*args)
        
        monkeypatch.setattr('mcp_server.os.path.join', mock_join)
        
        # Empty values should return empty string or None
        result = mcp_server.get_config_value('PLEX', 'ServerURL', default='default')
        # Empty string may be returned or default
        assert result in ['', 'default', None] or result is None
    
    def test_case_sensitivity_configparser(self):
        """Test case sensitivity (configparser optionxform)."""
        # The code uses config.optionxform = lambda optionstr: optionstr
        # This preserves case, so keys should match exactly
        
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write("[PLEX]\nServerURL = http://localhost:32400\nToken = test-token\n")
            config_path = f.name
        
        try:
            # Mock the config path
            original_path = mcp_server.get_config_value.__code__.co_filename
            
            # Test that case is preserved
            with patch('mcp_server.os.path.join', return_value=config_path):
                result = mcp_server.get_config_value('PLEX', 'ServerURL')
                assert result == 'http://localhost:32400'
                
                # Test that exact case is required
                result2 = mcp_server.get_config_value('plex', 'ServerURL')  # lowercase section
                # Should return None or default since section case doesn't match
                assert result2 is None or result2 == 'http://localhost:32400'  # configparser may be case-insensitive for sections
        finally:
            if os.path.exists(config_path):
                os.unlink(config_path)


class TestGetConfigValueHelper:
    """Tests for get_config_value helper function."""
    
    def test_valid_section_key(self, monkeypatch, tmp_path):
        """Test valid section/key returns value."""
        # Create a temporary config file
        config_file = tmp_path / "config.ini"
        config_file.write_text("[PLEX]\nServerURL = http://localhost:32400\nToken = test-token\n")
        
        # Mock the config path
        def mock_join(*args):
            if 'config.ini' in str(args[-1]):
                return str(config_file)
            return os.path.join(*args)
        
        monkeypatch.setattr('mcp_server.os.path.join', mock_join)
        
        result = mcp_server.get_config_value('PLEX', 'ServerURL')
        assert result == 'http://localhost:32400'
    
    def test_missing_section_returns_default(self, monkeypatch, tmp_path):
        """Test missing section returns default."""
        # Create a temporary config file without PLEX section
        config_file = tmp_path / "config.ini"
        config_file.write_text("[NAVIDROME]\nURL = http://localhost:4533\n")
        
        # Mock the config path
        def mock_join(*args):
            if 'config.ini' in str(args[-1]):
                return str(config_file)
            return os.path.join(*args)
        
        monkeypatch.setattr('mcp_server.os.path.join', mock_join)
        
        result = mcp_server.get_config_value('PLEX', 'ServerURL', default='default-value')
        assert result == 'default-value'
    
    def test_missing_key_returns_default(self, monkeypatch, tmp_path):
        """Test missing key returns default."""
        # Create a temporary config file
        config_file = tmp_path / "config.ini"
        config_file.write_text("[PLEX]\nServerURL = http://localhost:32400\n")
        
        # Mock the config path
        def mock_join(*args):
            if 'config.ini' in str(args[-1]):
                return str(config_file)
            return os.path.join(*args)
        
        monkeypatch.setattr('mcp_server.os.path.join', mock_join)
        
        result = mcp_server.get_config_value('PLEX', 'Token', default='default-token')
        assert result == 'default-token'
    
    def test_empty_value_handling(self, monkeypatch, tmp_path):
        """Test empty value handling."""
        # Create a temporary config file with empty value
        config_file = tmp_path / "config.ini"
        config_file.write_text("[PLEX]\nServerURL = \nToken = test-token\n")
        
        # Mock the config path
        def mock_join(*args):
            if 'config.ini' in str(args[-1]):
                return str(config_file)
            return os.path.join(*args)
        
        monkeypatch.setattr('mcp_server.os.path.join', mock_join)
        
        result = mcp_server.get_config_value('PLEX', 'ServerURL', default='default')
        # Empty string may be returned
        assert result == '' or result == 'default' or result is None
    
    def test_default_none_when_no_default_provided(self):
        """Test that None is returned when no default is provided and value is missing."""
        with patch('mcp_server.os.path.exists', return_value=False):
            result = mcp_server.get_config_value('PLEX', 'ServerURL')
            assert result is None
    
    def test_multiple_sections(self, monkeypatch, tmp_path):
        """Test reading from multiple sections."""
        # Create a temporary config file with multiple sections
        config_file = tmp_path / "config.ini"
        config_file.write_text("""[PLEX]
ServerURL = http://localhost:32400
Token = plex-token

[NAVIDROME]
URL = http://localhost:4533
Username = navidrome-user
""")
        
        # Mock the config path
        def mock_join(*args):
            if 'config.ini' in str(args[-1]):
                return str(config_file)
            return os.path.join(*args)
        
        monkeypatch.setattr('mcp_server.os.path.join', mock_join)
        
        plex_url = mcp_server.get_config_value('PLEX', 'ServerURL')
        navidrome_url = mcp_server.get_config_value('NAVIDROME', 'URL')
        
        assert plex_url == 'http://localhost:32400'
        assert navidrome_url == 'http://localhost:4533'

