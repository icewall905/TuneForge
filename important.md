# TuneForge - Critical Information

## Quick Start
- **Port**: 5395 (changed from 5001 to avoid conflicts)
- **URL**: http://localhost:5395
- **Start Command**: `source venv/bin/activate && python run.py`

## Project Status
✅ **FULLY FUNCTIONAL** - All tests passed, application working correctly

## Key Components Working
- Flask application startup and routing
- Template rendering (index, history, settings pages)
- Configuration loading and management
- Static file serving (CSS, JS, images)
- Logging system
- Audio analysis system with floating progress indicator
- Global status management for background processes
  - Debounced updates (500ms) with 1s minimum interval
  - Stable progress (no 0% regressions), cached last-good value
  - Scoped page selectors prevent sidebar interference
  - Status polling consolidated; stop clears promptly

## Configuration
- Uses `config.ini` (copied from `config.ini.example`)
- Supports Ollama, Navidrome, and Plex integration
- All required sections present and functional

## Dependencies
- Python 3.12.3 (compatible with 3.7+ requirement)
- Flask 2.3.3, Requests 2.31.0, Werkzeug 2.3.7
- Virtual environment: `venv/`

## Testing Results
- ✅ Import tests passed
- ✅ App creation successful
- ✅ Template rendering working
- ✅ Configuration loading functional
- ✅ HTTP endpoints responding (200 status)
- ✅ Content rendering correctly

## Database Information
- **Database**: `db/local_music.db` (SQLite)
- **Total Tracks**: 381 (local test library)
- **Size**: ~73MB (full library)
- **Storage Path**: `/mnt/media/music/` (network mount) + `/home/hnyg/Music/` (local test)
- **Schema**: 3 tables with metadata indexes + audio analysis system
- **Audio Analysis**: Phase 1 Complete ✅ - All database tables created successfully
- **Audio Analysis**: Phase 2 Complete ✅ - Core engine, dependencies, and performance optimization
- **Audio Analysis**: Phase 3 Complete ✅ - Database integration, batch processing, and web interface with floating progress indicator

## Next Steps for Development
1. Playlist generator: match Ollama suggestions against local library (no Navidrome search)
2. Begin Phase 4 (Recommendation Engine): similarity calc, weighting, endpoints
3. Test Navidrome/Plex connectivity
4. Add comprehensive error handling and retries across services
5. Optimize DB queries for large library (100k+)

## Troubleshooting
- If port conflicts occur, check `lsof -i :5395`
- Use `debug_scripts/test_app.py` for debugging
- Check `logs/tuneforge_app.log` for errors
