# TuneForge MCP Server Tests

This directory contains comprehensive tests for the TuneForge MCP server.

## Test Structure

- `conftest.py` - Shared pytest fixtures for database, config, and API mocking
- `test_find_similar_songs.py` - Tests for the `find_similar_songs` tool
- `test_search_tracks.py` - Tests for the `search_tracks` tool (Plex and Navidrome)
- `test_create_playlist.py` - Tests for the `create_playlist` tool
- `test_add_to_playlist.py` - Tests for the `add_to_playlist` tool
- `test_integration.py` - End-to-end integration tests
- `test_config.py` - Configuration management tests

## Running Tests

### Run all tests:
```bash
pytest
```

### Run with coverage:
```bash
pytest --cov=mcp_server --cov-report=html
```

### Run specific test file:
```bash
pytest tests/test_find_similar_songs.py
```

### Run specific test:
```bash
pytest tests/test_find_similar_songs.py::TestFindSimilarSongsHappyPath::test_find_similar_with_title_and_artist
```

### Run with verbose output:
```bash
pytest -v
```

## Test Coverage

The test suite aims for 90%+ code coverage of `mcp_server.py`. Coverage reports are generated in HTML format in the `htmlcov/` directory.

## Test Categories

- **Unit Tests**: Mock all external dependencies (DB, APIs, config)
- **Integration Tests**: Use test database, mock APIs
- **E2E Tests**: Optional - require real Plex/Navidrome instances (marked as integration)

## Dependencies

Test dependencies are listed in `requirements.txt`:
- pytest
- pytest-cov
- pytest-mock
- responses

Install with:
```bash
pip install -r requirements.txt
```

## Test Fixtures

The `conftest.py` file provides several useful fixtures:

- `temp_db` - Temporary SQLite database with sample tracks and audio_features
- `mock_config_valid` - Mock config with valid Plex and Navidrome settings
- `mock_config_missing_plex` - Mock config missing Plex section
- `mock_config_missing_navidrome` - Mock config missing Navidrome section
- `mock_plex_search_response` - Mock Plex API search response
- `mock_navidrome_search_response` - Mock Navidrome API search response
- `patch_db_path` - Patch DB_PATH to use temp database
- `patch_get_config_value` - Patch get_config_value helper

## Notes

- All external API calls are mocked to avoid requiring real Plex/Navidrome instances
- Database operations use temporary databases that are cleaned up after tests
- Tests are isolated and can run in any order

