"""
Shared pytest fixtures for TuneForge MCP server tests.
"""
import pytest
import sqlite3
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock
import configparser


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database with sample tracks and audio_features."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tracks table
    cursor.execute('''
        CREATE TABLE tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            artist TEXT,
            album TEXT,
            file_path TEXT UNIQUE,
            genre TEXT,
            duration REAL,
            file_size INTEGER,
            last_modified INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create audio_features table
    cursor.execute('''
        CREATE TABLE audio_features (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER NOT NULL,
            tempo REAL,
            key TEXT,
            mode TEXT,
            energy REAL,
            danceability REAL,
            valence REAL,
            acousticness REAL,
            instrumentalness REAL,
            loudness REAL,
            speechiness REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE
        )
    ''')
    
    # Insert sample tracks (20 tracks)
    sample_tracks = [
        (1, "Bohemian Rhapsody", "Queen", "A Night at the Opera", "/music/queen/bohemian.mp3", "Rock", 355.0, 5000000, 1000000),
        (2, "Stairway to Heaven", "Led Zeppelin", "Led Zeppelin IV", "/music/zeppelin/stairway.mp3", "Rock", 482.0, 6000000, 1000001),
        (3, "Hotel California", "Eagles", "Hotel California", "/music/eagles/hotel.mp3", "Rock", 391.0, 5500000, 1000002),
        (4, "Sweet Child O' Mine", "Guns N' Roses", "Appetite for Destruction", "/music/gnr/sweet.mp3", "Rock", 356.0, 5200000, 1000003),
        (5, "Comfortably Numb", "Pink Floyd", "The Wall", "/music/pinkfloyd/comfortably.mp3", "Progressive Rock", 384.0, 5800000, 1000004),
        (6, "Thunderstruck", "AC/DC", "The Razors Edge", "/music/acdc/thunder.mp3", "Rock", 292.0, 4500000, 1000005),
        (7, "Back in Black", "AC/DC", "Back in Black", "/music/acdc/back.mp3", "Rock", 255.0, 4000000, 1000006),
        (8, "Smells Like Teen Spirit", "Nirvana", "Nevermind", "/music/nirvana/teen.mp3", "Grunge", 301.0, 4800000, 1000007),
        (9, "Wonderwall", "Oasis", "What's the Story Morning Glory", "/music/oasis/wonderwall.mp3", "Britpop", 258.0, 4200000, 1000008),
        (10, "Don't Stop Believin'", "Journey", "Escape", "/music/journey/believin.mp3", "Rock", 251.0, 4100000, 1000009),
        (11, "Bohemian Rhapsody", "Queen", "Greatest Hits", "/music/queen/bohemian2.mp3", "Rock", 355.0, 5000000, 1000010),  # Duplicate title
        (12, "Another One Bites the Dust", "Queen", "The Game", "/music/queen/dust.mp3", "Rock", 215.0, 3500000, 1000011),
        (13, "We Will Rock You", "Queen", "News of the World", "/music/queen/rockyou.mp3", "Rock", 122.0, 2000000, 1000012),
        (14, "Radio Ga Ga", "Queen", "The Works", "/music/queen/radio.mp3", "Pop Rock", 345.0, 5100000, 1000013),
        (15, "Under Pressure", "Queen & David Bowie", "Hot Space", "/music/queen/pressure.mp3", "Rock", 248.0, 4000000, 1000014),
        (16, "No Features Track", "Unknown Artist", "Unknown Album", "/music/unknown/nofeatures.mp3", "Unknown", 200.0, 3000000, 1000015),
        (17, "Test Song", "Test Artist", "Test Album", "/music/test/test.mp3", "Test", 180.0, 2500000, 1000016),
        (18, "Another Test", "Test Artist", "Test Album 2", "/music/test/another.mp3", "Test", 195.0, 2600000, 1000017),
        (19, "Special Chars: 'Test' & \"More\"", "Artist & Co.", "Album (2024)", "/music/special/chars.mp3", "Special", 220.0, 2800000, 1000018),
        (20, "Very Long Title That Goes On And On And On And On And On", "Very Long Artist Name That Also Goes On", "Very Long Album Name", "/music/long/long.mp3", "Long", 300.0, 4500000, 1000019),
    ]
    
    cursor.executemany('''
        INSERT INTO tracks (id, title, artist, album, file_path, genre, duration, file_size, last_modified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_tracks)
    
    # Insert audio_features for 15 tracks (leaving 5 without features)
    sample_features = [
        (1, 1, 120.0, "C", "major", 0.85, 0.75, 0.65, 0.25, 0.05, -5.2, 0.08),  # Bohemian Rhapsody
        (2, 2, 72.0, "A", "minor", 0.45, 0.35, 0.40, 0.80, 0.10, -8.5, 0.03),  # Stairway to Heaven
        (3, 3, 75.0, "B", "minor", 0.60, 0.55, 0.50, 0.60, 0.15, -6.8, 0.05),  # Hotel California
        (4, 4, 125.0, "D", "major", 0.90, 0.85, 0.80, 0.15, 0.02, -4.5, 0.12),  # Sweet Child O' Mine
        (5, 5, 65.0, "B", "minor", 0.40, 0.30, 0.35, 0.85, 0.20, -9.2, 0.02),  # Comfortably Numb
        (6, 6, 135.0, "E", "major", 0.95, 0.90, 0.85, 0.10, 0.01, -3.8, 0.15),  # Thunderstruck
        (7, 7, 120.0, "A", "minor", 0.88, 0.80, 0.75, 0.20, 0.03, -4.2, 0.10),  # Back in Black
        (8, 8, 117.0, "F", "minor", 0.92, 0.88, 0.70, 0.12, 0.05, -3.5, 0.18),  # Smells Like Teen Spirit
        (9, 9, 87.0, "F#", "major", 0.55, 0.60, 0.75, 0.50, 0.08, -7.2, 0.06),  # Wonderwall
        (10, 10, 122.0, "E", "major", 0.75, 0.70, 0.80, 0.30, 0.04, -5.8, 0.09),  # Don't Stop Believin'
        (11, 11, 120.0, "C", "major", 0.85, 0.75, 0.65, 0.25, 0.05, -5.2, 0.08),  # Duplicate Bohemian Rhapsody
        (12, 12, 110.0, "D", "minor", 0.80, 0.85, 0.60, 0.18, 0.02, -4.8, 0.11),  # Another One Bites the Dust
        (13, 13, 81.0, "G", "major", 0.70, 0.65, 0.70, 0.22, 0.03, -6.0, 0.07),  # We Will Rock You
        (14, 14, 115.0, "C#", "major", 0.78, 0.72, 0.68, 0.28, 0.06, -5.5, 0.08),  # Radio Ga Ga
        (15, 15, 113.0, "D", "major", 0.82, 0.78, 0.72, 0.20, 0.04, -5.0, 0.10),  # Under Pressure
    ]
    
    cursor.executemany('''
        INSERT INTO audio_features (id, track_id, tempo, key, mode, energy, danceability, valence, acousticness, instrumentalness, loudness, speechiness)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_features)
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def mock_config_valid():
    """Mock config.ini with valid Plex and Navidrome settings."""
    config = configparser.ConfigParser()
    config['PLEX'] = {
        'ServerURL': 'http://localhost:32400',
        'Token': 'test-plex-token',
        'MachineID': 'test-machine-id',
        'MusicSectionID': '1'
    }
    config['NAVIDROME'] = {
        'URL': 'http://localhost:4533',
        'Username': 'testuser',
        'Password': 'testpass'
    }
    return config


@pytest.fixture
def mock_config_missing_plex():
    """Mock config.ini with missing Plex section."""
    config = configparser.ConfigParser()
    config['NAVIDROME'] = {
        'URL': 'http://localhost:4533',
        'Username': 'testuser',
        'Password': 'testpass'
    }
    return config


@pytest.fixture
def mock_config_missing_navidrome():
    """Mock config.ini with missing Navidrome section."""
    config = configparser.ConfigParser()
    config['PLEX'] = {
        'ServerURL': 'http://localhost:32400',
        'Token': 'test-plex-token',
        'MachineID': 'test-machine-id',
        'MusicSectionID': '1'
    }
    return config


@pytest.fixture
def mock_config_empty():
    """Mock empty config.ini."""
    return configparser.ConfigParser()


@pytest.fixture
def mock_plex_search_response():
    """Mock successful Plex search response."""
    return {
        'MediaContainer': {
            'Metadata': [
                {
                    'ratingKey': '12345',
                    'title': 'Test Song',
                    'grandparentTitle': 'Test Artist',
                    'parentTitle': 'Test Album'
                },
                {
                    'ratingKey': '12346',
                    'title': 'Another Song',
                    'grandparentTitle': 'Test Artist',
                    'parentTitle': 'Test Album'
                }
            ]
        }
    }


@pytest.fixture
def mock_plex_empty_response():
    """Mock empty Plex search response."""
    return {
        'MediaContainer': {
            'Metadata': []
        }
    }


@pytest.fixture
def mock_navidrome_search_response():
    """Mock successful Navidrome/Subsonic search response."""
    return {
        'subsonic-response': {
            'status': 'ok',
            'searchResult3': {
                'song': [
                    {
                        'id': 'nav-123',
                        'title': 'Test Song',
                        'artist': 'Test Artist',
                        'album': 'Test Album'
                    },
                    {
                        'id': 'nav-124',
                        'title': 'Another Song',
                        'artist': 'Test Artist',
                        'album': 'Test Album'
                    }
                ]
            }
        }
    }


@pytest.fixture
def mock_navidrome_error_response():
    """Mock Navidrome error response."""
    return {
        'subsonic-response': {
            'status': 'failed',
            'error': {
                'code': 40,
                'message': 'Wrong username or password'
            }
        }
    }


@pytest.fixture
def mock_navidrome_create_playlist_response():
    """Mock successful Navidrome playlist creation response."""
    return {
        'subsonic-response': {
            'status': 'ok',
            'playlist': {
                'id': 'playlist-123',
                'name': 'Test Playlist'
            }
        }
    }


@pytest.fixture
def mock_plex_create_playlist_response():
    """Mock successful Plex playlist creation response."""
    return {
        'MediaContainer': {
            'Metadata': [
                {
                    'ratingKey': 'playlist-456',
                    'title': 'Test Playlist'
                }
            ]
        }
    }


@pytest.fixture
def sample_track_ids():
    """Sample track IDs for testing."""
    return ['12345', '12346', '12347']


@pytest.fixture
def sample_audio_features():
    """Sample audio features data."""
    return {
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


@pytest.fixture
def mock_requests_get(monkeypatch):
    """Mock requests.get for HTTP calls."""
    def _mock_get(*args, **kwargs):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        return mock_response
    
    monkeypatch.setattr('mcp_server.requests.get', _mock_get)
    return _mock_get


@pytest.fixture
def mock_requests_post(monkeypatch):
    """Mock requests.post for HTTP calls."""
    def _mock_post(*args, **kwargs):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        return mock_response
    
    monkeypatch.setattr('mcp_server.requests.post', _mock_post)
    return _mock_post


@pytest.fixture
def mock_requests_put(monkeypatch):
    """Mock requests.put for HTTP calls."""
    def _mock_put(*args, **kwargs):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        return mock_response
    
    monkeypatch.setattr('mcp_server.requests.put', _mock_put)
    return _mock_put


@pytest.fixture
def patch_db_path(monkeypatch, temp_db):
    """Patch DB_PATH in mcp_server to use temp database."""
    monkeypatch.setattr('mcp_server.DB_PATH', temp_db)
    return temp_db


@pytest.fixture
def patch_get_config_value(monkeypatch):
    """Patch get_config_value to return test values."""
    def _get_config_value(section, key, default=None):
        configs = {
            ('PLEX', 'ServerURL'): 'http://localhost:32400',
            ('PLEX', 'Token'): 'test-token',
            ('PLEX', 'MachineID'): 'test-machine-id',
            ('PLEX', 'MusicSectionID'): '1',
            ('NAVIDROME', 'URL'): 'http://localhost:4533',
            ('NAVIDROME', 'Username'): 'testuser',
            ('NAVIDROME', 'Password'): 'testpass',
        }
        return configs.get((section, key), default)
    
    monkeypatch.setattr('mcp_server.get_config_value', _get_config_value)

