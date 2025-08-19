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
- **Sonic Traveller** - AI-powered playlist generation system
  - Background processing with progress tracking
  - Local library search and seed track selection
  - Audio feature-based similarity matching
  - Export to JSON and M3U formats
  - Performance optimized with database indexes and caching

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

## Sonic Traveller Endpoints
- **GET** `/new-generator` - Main Sonic Traveller interface
- **POST** `/api/sonic/start` - Start background generation job
- **GET** `/api/sonic/status` - Get job progress and status
- **POST** `/api/sonic/stop` - Stop running generation job
- **POST** `/api/sonic/cleanup` - Clean up completed jobs
- **GET** `/api/sonic/export-json` - Export results as JSON
- **GET** `/api/sonic/export-m3u` - Export results as M3U playlist
- **GET** `/api/sonic/seed-info` - Get seed track features and schema info
- **GET** `/api/local-search` - Search local music library

## Next Steps for Development
1. ✅ **COMPLETED**: Sonic Traveller implementation with background processing
2. Playlist generator: match Ollama suggestions against local library (no Navidrome search)
3. Begin Phase 4 (Recommendation Engine): similarity calc, weighting, endpoints
4. Test Navidrome/Plex connectivity
5. Add comprehensive error handling and retries across services
6. Optimize DB queries for large library (100k+)

## Troubleshooting
- If port conflicts occur, check `lsof -i :5395`
- Use `debug_scripts/test_app.py` for debugging
- Check `logs/tuneforge_app.log` for errors
- Sonic Traveller jobs are stored in memory; restart clears all jobs
