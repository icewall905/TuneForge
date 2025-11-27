# TuneForge - Critical Information

## 🎯 **CURRENT STATUS: MUSIC CONCIERGE INTEGRATED** ✅

The "Music Concierge" chat interface has been added, allowing natural language interaction with an AI agent via n8n webhook integration.

## 🚀 **Core Features**

### **Ask a Friend (Main Playlist Generator)**
- Generate personalized playlists using Ollama LLM
- Save to Navidrome or Plex
- Progress tracking and real-time updates

### **Sonic Traveller (AI + Audio Analysis)**
- Enhanced iterative generation with feedback loop
- Random seed integration to prevent stale results
- Adaptive prompting using successful candidates as examples
- Local playlist history integration with metadata
- Audio feature similarity matching with weighted Euclidean distance
- Background processing with progress tracking
- Export to JSON and M3U formats
- Performance optimized with database indexes and caching

### **Music Concierge**
- **Chat Interface**: Modern, slick chat UI for conversational interaction.
- **n8n Integration**: Directly communicates with n8n webhook (`https://n8n.lan/webhook/...`) to process user requests.
- **Interactive**: Real-time "typing" feedback and JSON-based response handling.
- **Menu Integration**: Accessible directly from the sidebar under "Sonic Traveller".

### **Mobile PWA (NEW)**
- **URL**: `/musical-agent/mobile` - Standalone mobile-friendly interface
- **PWA Support**: "Add to Home Screen" for app-like experience on iOS/Android
- **Offline Ready**: Service worker caches static assets for offline access
- **Touch Optimized**: 44px+ tap targets, bottom input bar, swipe-friendly
- **Collapsible History**: Slide-in panel from left with session management
- **Dark Theme**: Modern dark UI with purple accents, safe area support for notches

## 🔧 **API Endpoints**

### **Sonic Traveller Endpoints**
- `POST /api/sonic/start` - Start playlist generation
- `GET /api/sonic/status?job_id=<id>` - Check generation status
- `POST /api/sonic/stop?job_id=<id>` - Stop generation
- `GET /api/sonic/export?job_id=<id>&format=<json|m3u>` - Export results

### **Local Search Endpoints**
- `GET /api/local-search?q=<query>&limit=<number>` - Search local music library

## 🎵 **Audio Features System**
- **8 audio features**: energy, valence, tempo, danceability, acousticness, instrumentalness, loudness, speechiness
- **Normalized vectors**: Features scaled to [0,1] range for consistent comparison
- **Weighted distance**: Euclidean distance with feature-specific weights
- **Database integration**: SQLite with optimized queries and indexing
- **⚠️ SQLite Limitation**: Database locks occur with multiple workers - use `MaxWorkers = 1` in `[AUDIO_ANALYSIS]` config

## 🗄️ **Database Structure**
- `tracks` table: Music metadata (id, title, artist, album, genre, path)
- `audio_features` table: Extracted audio features (track_id, energy, valence, etc.)
- `analysis_queue` table: Background processing queue management

## ⚙️ **Configuration**
- **Ollama**: Configure URL and model in config.ini
- **Audio Analysis**: Enable/disable in config.ini
- **Debug Mode**: Set in config.ini for detailed logging
- **Auto-Startup**: Configure automatic library scan and analysis on app start
- **Scanner Settings**: Configure file size limits, batch sizes, and performance options in [scanner] section

## 🐛 **Recent Bug Fixes**
- ✅ **Fixed MCP tool schema for n8n** - Array items must have BOTH `type` AND `inputType` (e.g., `"items": {"type": "string", "inputType": "text"}`). Error occurs when selecting tools if items schema is incomplete.
- ✅ **Fixed n8n Integer Type Issue** - n8n MCP client doesn't support `type: "integer"` (only `type: "number"`). Changed all `int` parameters to `float` to generate `type: "number"`. See GitHub issue #21569.
- ⚠️ **n8n Array in Required Bug** - Tools with array parameters in the `required` array fail. This is an n8n bug when processing required arrays containing array properties. Affects: `bulk_search_tracks`, `add_to_playlist`.
- ✅ **Fixed SQLite column name issues** in feature fetching functions
- ✅ **Resolved distance calculation problems** (now working correctly)
- ✅ **Enhanced UI** with improved threshold slider (0.5-2.0 range)
- ✅ **Better progress display** and feedback loop information

## 📊 **Performance**
- **Background processing**: Non-blocking playlist generation
- **Real-time updates**: Live progress tracking via Server-Sent Events
- **Caching**: Feature statistics and computed vectors cached in memory
- **Database optimization**: Indexes on track_id and search fields

## 🎉 **Success Metrics**
- **Playlist generation**: Working end-to-end with audio similarity matching
- **Feedback loop**: Successfully improves suggestions across iterations
- **Local history**: Generated playlists saved with rich metadata
- **User experience**: Intuitive interface with clear progress indication

## 🚀 **Auto-Startup System**
- **Library Scan**: Automatically scan music folder on app start
- **Audio Analysis**: Automatically start analysis processing on app start (with intelligent status checking)
- **Sequential Processing**: Library scan completes before audio analysis starts (prevents database locking)
- **Configurable Delay**: Set startup delay (10-300 seconds) to ensure app is ready
- **Background Processing**: All auto-startup processes run in background threads
- **Full Monitoring**: Auto-recovery and health monitoring for background processes
- **Enhanced Recovery**: Stuck file detection and automatic recovery mechanisms
- **Smart Detection**: Recognizes when tracks are already analyzed vs. truly pending
- **Database Safety**: Waits for database to be ready before starting analysis

## 🔧 **Advanced Scanner Improvements** (NEW)
- **Database Query Optimization**: Batch existence checks reduce database queries by 50x
- **Critical Database Indexes**: Added composite indexes for 10-100x faster queries on large libraries
- **File Size Validation**: Configurable limits prevent memory exhaustion (default: 500MB max, 1KB min)
- **Incremental Scanning**: Skip unchanged files for 90%+ faster subsequent scans
- **Path Validation**: Unicode normalization and length limits prevent edge case failures
- **Configurable Settings**: All scanner options tunable via config.ini [scanner] section
- **Enhanced Error Handling**: Differentiated error types (permission, corruption, timeout)
- **Thread Safety**: Progress tracker protected with locks
- **Graceful Cancellation**: Users can cancel long-running scans
- **Timeout Protection**: Mutagen operations protected with 15-second timeouts

## 🔮 **Future Enhancements** (Optional)
- Advanced candidate filtering (genre awareness, artist diversity)
- Prompt engineering optimization (dynamic prompting, failure analysis)
- Enhanced audio feature extraction and analysis
