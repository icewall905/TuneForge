# Ollama Playlist Generator

A web application that uses Ollama's LLM capabilities to generate personalized music playlists that can be saved to Navidrome or Plex.

Repository: [https://github.com/icewall905/ollama-playlist-generator](https://github.com/icewall905/ollama-playlist-generator)

## Features

- Generate personalized playlists based on your music preferences
- Integration with Navidrome and Plex for music library access
- Track search and playlist creation in supported platforms
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
   git clone https://github.com/icewall905/ollama-playlist-generator.git
   cd ollama-playlist-generator
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
   - Edit `config.ini` with your Ollama, Navidrome, and/or Plex settings
   - You can also configure settings through the web interface

## Usage

1. **Start the web application**:
   ```bash
   python run.py
   ```

2. **Access the web interface**:
   ```
   http://localhost:5001
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
ollama-playlist-generator/
├── app/                     # Application package
│   ├── __init__.py          # Flask app initialization
│   └── routes.py            # Application routes and main logic
├── static/                  # Static assets
│   ├── css/                 # CSS stylesheets
│   │   ├── style.css        # Main stylesheet
│   │   └── custom.css       # Additional custom styles
│   ├── js/                  # JavaScript files
│   │   └── main.js          # Main JavaScript logic
│   └── images/              # Image assets
├── templates/               # Jinja2 templates
│   ├── layout.html          # Base template with sidebar layout
│   ├── index.html           # Playlist generation page
│   ├── history.html         # Playlist history page
│   └── settings.html        # Settings page
├── run.py                   # Application entry point
├── config.ini.example       # Example configuration file
└── requirements.txt         # Python dependencies
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
Description=Ollama Playlist Generator
After=network.target

[Service]
User=your_user
WorkingDirectory=/path/to/ollama-playlist-generator
ExecStart=/path/to/python /path/to/ollama-playlist-generator/run.py
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

## License
This project is licensed under the MIT License.
