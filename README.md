# Ollama Playlist Generator

This repository contains a Flask-based application that generates playlists using the Ollama language model. The app interacts with Ollama's API and Navidrome to generate and create playlists based on user-defined criteria.

Repository: [https://github.com/icewall905/ollama-playlist-generator](https://github.com/icewall905/ollama-playlist-generator)

## Features

- **Interactive Web Interface**: Use an intuitive web form to generate playlists.
- **Ollama Integration**: Leverages the Ollama language model (e.g. `deepseek-r1:8b`) to generate song suggestions.
- **Navidrome Integration**: Searches for tracks using the Navidrome API.
- **Dynamic Configuration**: Update configuration (such as API URLs, model, context window, maximum retry attempts) via the web interface. Changes are saved immediately and re-read on every generate request.

## Requirements

- Python 3.x
- Flask
- Requests

**Also**:

- A running Ollama server. (And some model to suggest tracks.)
- A running Navidrome server.

## Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/icewall905/ollama-playlist-generator.git
   cd ollama-playlist-generator

2. **Create a virtual evt**:
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

3. **Install reqs as needed**:
pip install -r requirements.txt

4. **Configure settings**:
   - Edit `setup.conf` to set up Ollama and Navidrome endpoints, credentials, and retry attempts. (Or set it up in the webui after next step)

5. **Run**:
To run directly in console:
python3 ollama_playlist_generator.py

To start webui:
python3 ollama_playlist_generator.py web (You can reach it at http://127.0.0.1:5555)



5. Open the web interface at:
    ```
    http://127.0.0.1:5555
    ```

## Usage Guide

### Generating a Playlist
1. Open the web interface.
2. Enter a **playlist name** and **description**.
3. Fill in **likes, dislikes, and favorite artists**.
4. Click `Generate Playlist`.
5. The generated playlist will appear in the console output.

### Saving Configuration
1. Adjust settings in the web interface.
2. Click `Save Settings` to persist changes to `setup.conf`.

## Running in Production
To run the server persistently, consider using:
```sh
nohup python3 generator.py web &
```
Or run it with a process manager like `systemd` or `supervisord`.

Example systemd:
'''
[Unit]
Description=Playlist Generator Web Service
After=network.target

[Service]
User=root
WorkingDirectory=/opt/playlistgenerator
ExecStart=/usr/bin/python3 playlist-generator.py web 5555
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
'''

## Troubleshooting
- If the server fails to start, ensure `setup.conf` is correctly configured.
- If playlists are not being generated, check that Ollama is running and accessible.
- Increase `max_attempts` in `setup.conf` if you receive too few tracks.
- Enable "DEBUG_OLLAMA_RESPONSE" to get extra output in console.

## License
This project is licensed under the MIT License.
