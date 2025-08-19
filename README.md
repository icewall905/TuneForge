# TuneForge

A web application that uses Ollama's LLM capabilities to generate personalized music playlists that can be saved to Navidrome or Plex.

## 🎉 **NEW: Sonic Traveller is Fully Functional!** ✅

The Sonic Traveller AI-powered playlist generation system is now **production-ready** and successfully generates playlists using audio feature similarity analysis with an enhanced feedback loop system.

## Features

- Generate personalized playlists based on your music preferences
- **NEW**: Sonic Traveller - AI-powered playlist generation with audio feature analysis
- **NEW**: Enhanced feedback loop system for iterative quality improvement
- **NEW**: Local playlist history integration with rich metadata
- **NEW**: Real-time progress tracking and background processing
- Rate your generated playlists
- Save playlists to Navidrome or Plex
- Local music library management
- Audio analysis and feature extraction
- **NEW**: Audio feature similarity matching with weighted Euclidean distance
- **NEW**: Export to JSON and M3U formats

## Quick Start

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd TuneForge
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure**:
   - Copy `config.ini.example` to `config.ini`
   - Set your Ollama URL and model
   - Configure Navidrome/Plex if desired

3. **Ask a Friend (Generate a playlist)**:
   - Start the app: `source venv/bin/activate && python run.py`
   - Open http://localhost:5395
   - Enter your music preferences
   - Click "Ask a Friend"

4. **NEW: Sonic Traveller**:
   - Navigate to "Sonic Traveller" in the menu
   - Select a seed track from your local library
   - Set similarity threshold (0.5-2.0 recommended)
   - Click "Ask a Friend" to start AI-powered generation
   - Watch real-time progress and feedback loop improvements
   - Export results as JSON or M3U playlist

## 🚀 **Sonic Traveller Features**

### **AI-Powered Generation**
- Uses Ollama LLM to suggest similar tracks
- Random seed integration prevents stale results
- Adaptive prompting based on successful candidates

### **Audio Feature Analysis**
- **8 audio features**: energy, valence, tempo, danceability, acousticness, instrumentalness, loudness, speechiness
- **Normalized similarity**: Features scaled to [0,1] range for consistent comparison
- **Weighted distance**: Euclidean distance with feature-specific weights

### **Enhanced Feedback Loop**
- Learns from accepted/rejected tracks across iterations
- Improves suggestion quality with each batch
- Maintains generation history and metadata

### **Real-Time Processing**
- Background job management with progress tracking
- Live updates via Server-Sent Events
- Non-blocking playlist generation

### **Export & History**
- JSON export with full metadata
- M3U playlist export
- Local history integration with rich metadata

## Architecture

- **Frontend**: HTML/CSS/JavaScript with real-time updates
- **Backend**: Flask with background processing
- **Database**: SQLite with audio features and analysis queue
- **AI**: Ollama integration for track suggestions
- **Audio**: Librosa for feature extraction and analysis

## Configuration

- **Ollama**: Set URL and model in `config.ini`
- **Audio Analysis**: Enable/disable in `config.ini`
- **Port**: Default 5395 (configurable)

## Development

- **Virtual Environment**: `venv/`
- **Database**: `db/local_music.db`
- **Logs**: `logs/tuneforge_app.log`
- **Debug Scripts**: `debug_scripts/` folder

## 🎯 **Current Status**

✅ **Sonic Traveller**: Fully functional and production-ready
✅ **Ask a Friend**: Main playlist generator working
✅ **Audio Analysis**: Complete with floating progress indicator
✅ **Local Music**: Library management and search
✅ **History**: Playlist storage and management
✅ **Export**: Multiple format support

## 🔮 **Future Enhancements**

- Advanced candidate filtering (genre awareness, artist diversity)
- Prompt engineering optimization
- Enhanced audio feature extraction
- Large library optimization (100k+ tracks)

## Troubleshooting

- **Port conflicts**: Check `lsof -i :5395`
- **Ollama issues**: Verify Ollama is running and accessible
- **Audio analysis**: Check dependencies (librosa, numpy, scipy)
- **Database**: Verify `db/local_music.db` exists and is accessible

## License

[License information]
