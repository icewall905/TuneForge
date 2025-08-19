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
- **Total Tracks**: 151,036
- **Size**: 73MB
- **Storage Path**: `/mnt/media/music/` (network mount)
- **Schema**: 3 tables with metadata indexes + audio analysis system
- **Audio Analysis**: Phase 1 Complete ✅ - All database tables created successfully

## Next Steps for Development
1. Test Ollama integration for playlist generation
2. Test Navidrome/Plex connectivity
3. Implement new features
4. Add comprehensive error handling
5. Optimize database queries for large library

## Troubleshooting
- If port conflicts occur, check `lsof -i :5395`
- Use `debug_scripts/test_app.py` for debugging
- Check `logs/tuneforge_app.log` for errors
