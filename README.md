# TuneForge

<img src="static/images/logo_big.jpeg" alt="TuneForge Logo" width="50%">

A web application that uses Ollama's LLM capabilities to generate personalized music playlists that can be saved to Navidrome or Plex.

Repository: [https://github.com/icewall905/TuneForge](https://github.com/icewall905/TuneForge)

## Features

- Generate personalized playlists based on your music preferences
- Integration with Navidrome and Plex for music library access
- Track search and playlist creation in supported platforms
- Selectable number of tracks for playlists (up to 100)
- Save and view playlist history
- Rate your generated playlists
- Modern dark-mode UI with responsive design

## Requirements

- Python 3.7+
- Flask
- Requests
- Ollama running locally or on a remote server
- (Optional) Navidrome or Plex Media Server for playlist integration

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/icewall905/TuneForge.git
   cd TuneForge
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure settings**:
   - Copy the example configuration file:
     ```bash
     cp config.ini.example config.ini
     ```
   - Edit `config.ini` with your Ollama, Navidrome, and/or Plex settings.
   - You can also configure settings through the web interface.

## Usage

1. **Start the web application**:
   Using the helper script (recommended for development):
   ```bash
   sh start_app.sh 
   ```
   Or manually:
   ```bash
   python run.py
   ```

2. **Access the web interface**:
   Open your browser and go to:
   ```
   http://localhost:5395
   ```

3. **Generate a playlist**:
   - Enter a playlist name and description
   - Fill in your musical likes, dislikes, and favorite artists
   - Click "Generate Playlist"
   - The app will generate suggestions and search for them in your configured music platforms
   - Results will appear in real-time in the console output
   - Playlists can be saved to your history and rated

## Project Structure

```
TuneForge/
├── app/                     # Application package
│   ├── __init__.py          # Flask app initialization
│   └── routes.py            # Application routes and main logic
├── static/                  # Static assets
│   ├── css/                 # CSS stylesheets
│   ├── js/                  # JavaScript files
│   └── images/              # Image assets (including logo_small.jpeg, logo_big.jpeg)
├── templates/               # Jinja2 templates
│   ├── layout.html          # Base template with sidebar layout
│   ├── index.html           # Playlist generation page
│   ├── history.html         # Playlist history page
│   └── settings.html        # Settings page
├── run.py                   # Application entry point
├── start_app.sh             # Helper script to setup environment and run the app
├── config.ini.example       # Example configuration file
├── config.ini               # User configuration file (created from example)
├── requirements.txt         # Python dependencies
├── playlist_history.json    # Stores history of generated playlists
└── README.md                # This file
```

## Running in Production

For production deployment, consider:

```bash
# Using nohup
nohup python run.py &

# Or using a process manager like systemd
```

Example systemd service file:
```ini
[Unit]
Description=TuneForge
After=network.target

[Service]
User=your_user
WorkingDirectory=/path/to/TuneForge
ExecStart=/path/to/venv/bin/python /path/to/TuneForge/run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Troubleshooting

- If the server fails to start, ensure `config.ini` is correctly configured
- If playlists are not being generated, check that Ollama is running and accessible
- Adjust the `max_attempts` in settings if you receive too few tracks
- Enable "DEBUG_OLLAMA_RESPONSE" in the code for more detailed output

## License

This project is licensed under the MIT License - see the LICENSE file for details.
