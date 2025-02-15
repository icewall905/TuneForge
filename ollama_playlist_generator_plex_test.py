import configparser
import json
import random
import re
import requests
from flask import Flask, request, render_template_string, jsonify, Response
import xml.etree.ElementTree as ET

# --- Global Debug Flag ---
DEBUG_OLLAMA_RESPONSE = False  # Set to True to print prompt and raw responses from Ollama

# --- Define Templates at the Top ---
HOME_TEMPLATE = """
<!doctype html>
<html>
<head>
  <title>Playlist Generator v0.9 by HNB (15.02.2025)</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    #artist_list { list-style-type: none; padding: 0; }
    #artist_list li { padding: 4px 0; }
    #console_output {
      height: 400px;
      overflow-y: scroll;
      border: 1px solid #ccc;
      padding: 10px;
      background-color: #f9f9f9;
      font-family: monospace;
    }
  </style>
</head>
<body>
  <div class="container my-5">
    <h1 class="mb-4">Playlist Generator v0.9 by HNB (15.02.2025)</h1>
    <form id="playlistForm">
      <div class="mb-3">
        <label for="playlist_name" class="form-label">Playlist Name:</label>
        <input type="text" class="form-control" id="playlist_name" name="playlist_name">
      </div>
      <div class="mb-3">
        <label for="playlist_description" class="form-label">Playlist Description:</label>
        <textarea class="form-control" id="playlist_description" name="playlist_description" rows="3"></textarea>
      </div>
      <div class="row">
        <div class="col-md-6">
          <div class="mb-3">
            <label for="likes" class="form-label">My Likes:</label>
            <textarea class="form-control" id="likes" name="likes" rows="3" required>{{ likes }}</textarea>
          </div>
          <div class="mb-3">
            <label for="dislikes" class="form-label">My Dislikes:</label>
            <textarea class="form-control" id="dislikes" name="dislikes" rows="3" required>{{ dislikes }}</textarea>
          </div>
          <div class="mb-3">
            <label for="artist_input" class="form-label">Add Favorite Artist:</label>
            <div class="input-group">
              <input type="text" class="form-control" id="artist_input" placeholder="Enter artist name">
              <button type="button" class="btn btn-outline-secondary" id="add_artist">Add</button>
            </div>
          </div>
          <input type="hidden" id="favorite_artists" name="favorite_artists" value="{{ favorite_artists }}">
          <div class="mb-3">
            <button type="submit" name="action" value="generate" class="btn btn-primary">Generate Playlist</button>
          </div>
        </div>
        <div class="col-md-6">
          <div class="mb-3">
            <label class="form-label">Console Output:</label>
            <div id="console_output" class="border p-2"></div>
          </div>
          <div class="mb-3">
            <label class="form-label">Favorite Artists:</label>
            <ul id="artist_list" class="list-group"></ul>
          </div>
        </div>
      </div>
      <div class="row mt-4">
        <div class="col-12">
          <a class="btn btn-link" data-bs-toggle="collapse" href="#configSettings" role="button" aria-expanded="false" aria-controls="configSettings">
            Show/Hide Configuration Settings
          </a>
          <div class="collapse" id="configSettings">
            <h4>Configuration Settings</h4>
            <div class="mb-3">
              <label for="ollama_url" class="form-label">Ollama URL:</label>
              <input type="text" class="form-control" id="ollama_url" name="ollama_url" value="{{ ollama_url }}">
            </div>
            <div class="mb-3">
              <label for="ollama_model" class="form-label">Ollama Model:</label>
              <input type="text" class="form-control" id="ollama_model" name="ollama_model" value="{{ ollama_model }}">
            </div>
            <div class="mb-3">
              <label for="navidrome_url" class="form-label">Navidrome URL:</label>
              <input type="text" class="form-control" id="navidrome_url" name="navidrome_url" value="{{ navidrome_url }}">
            </div>
            <div class="mb-3">
              <label for="navidrome_username" class="form-label">Navidrome Username:</label>
              <input type="text" class="form-control" id="navidrome_username" name="navidrome_username" value="{{ navidrome_username }}">
            </div>
            <div class="mb-3">
              <label for="navidrome_password" class="form-label">Navidrome Password:</label>
              <input type="password" class="form-control" id="navidrome_password" name="navidrome_password" value="{{ navidrome_password }}">
            </div>
            <div class="mb-3">
              <label for="context_window" class="form-label">Context Window:</label>
              <input type="number" class="form-control" id="context_window" name="context_window" value="{{ context_window }}">
            </div>
            <div class="mb-3">
              <label for="max_attempts" class="form-label">Max Retry Attempts:</label>
              <input type="number" class="form-control" id="max_attempts" name="max_attempts" value="{{ max_attempts }}">
            </div>
            <hr>
            <div class="mb-3">
              <label for="enable_navidrome" class="form-label">Enable Navidrome:</label>
              <select class="form-select" id="enable_navidrome" name="enable_navidrome">
                <option value="yes" {% if enable_navidrome == "yes" %}selected{% endif %}>Yes</option>
                <option value="no" {% if enable_navidrome == "no" %}selected{% endif %}>No</option>
              </select>
            </div>
            <div class="mb-3">
              <label for="enable_plex" class="form-label">Enable Plex:</label>
              <select class="form-select" id="enable_plex" name="enable_plex">
                <option value="yes" {% if enable_plex == "yes" %}selected{% endif %}>Yes</option>
                <option value="no" {% if enable_plex == "no" %}selected{% endif %}>No</option>
              </select>
            </div>
            <hr>
            <h4>Plex Settings</h4>
            <div class="mb-3">
              <label for="plex_server_url" class="form-label">Plex Server URL:</label>
              <input type="text" class="form-control" id="plex_server_url" name="plex_server_url" value="{{ plex_server_url }}">
            </div>
            <div class="mb-3">
              <label for="plex_token" class="form-label">Plex Token:</label>
              <input type="text" class="form-control" id="plex_token" name="plex_token" value="{{ plex_token }}">
            </div>
            <div class="mb-3">
              <label for="plex_machine_id" class="form-label">Plex Machine ID:</label>
              <input type="text" class="form-control" id="plex_machine_id" name="plex_machine_id" value="{{ plex_machine_id }}">
            </div>
            <div class="mb-3">
              <label for="plex_playlist_type" class="form-label">Plex Playlist Type:</label>
              <input type="text" class="form-control" id="plex_playlist_type" name="plex_playlist_type" value="{{ plex_playlist_type }}">
            </div>
            <div class="mb-3 text-end">
              <button type="submit" name="action" value="save" class="btn btn-secondary">Save Settings</button>
            </div>
          </div>
        </div>
      </div>
    </form>
    <div id="loading" class="mb-3" style="display:none;">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <span> Please wait...</span>
    </div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.0/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    function updateHiddenInput() {
      var listItems = document.querySelectorAll('#artist_list li span.artistName');
      var artists = [];
      listItems.forEach(function(item) { artists.push(item.textContent); });
      document.getElementById('favorite_artists').value = artists.join(', ');
    }
    function addArtist() {
      var input = document.getElementById('artist_input');
      var artistName = input.value.trim();
      if (artistName === '') return;
      var li = document.createElement('li');
      li.className = "list-group-item d-flex justify-content-between align-items-center";
      var span = document.createElement('span');
      span.className = 'artistName';
      span.textContent = artistName;
      li.appendChild(span);
      var removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.className = "btn btn-sm btn-danger";
      removeBtn.textContent = 'Remove';
      removeBtn.onclick = function() { li.parentNode.removeChild(li); updateHiddenInput(); };
      li.appendChild(removeBtn);
      document.getElementById('artist_list').appendChild(li);
      input.value = '';
      updateHiddenInput();
    }
    document.getElementById('add_artist').addEventListener('click', addArtist);
    window.onload = function() {
      var hiddenInput = document.getElementById('favorite_artists');
      var existing = hiddenInput.value;
      if (existing.trim() !== '') {
        var artists = existing.split(',').map(function(a) { return a.trim(); });
        artists.forEach(function(artist) {
          if (artist !== '') {
            var li = document.createElement('li');
            li.className = "list-group-item d-flex justify-content-between align-items-center";
            var span = document.createElement('span');
            span.className = 'artistName';
            span.textContent = artist;
            li.appendChild(span);
            var removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = "btn btn-sm btn-danger";
            removeBtn.textContent = 'Remove';
            removeBtn.onclick = function() { li.parentNode.removeChild(li); updateHiddenInput(); };
            li.appendChild(removeBtn);
            document.getElementById('artist_list').appendChild(li);
          }
        });
      }
    };
    document.getElementById("playlistForm").addEventListener("submit", function(e) {
      e.preventDefault();
      document.getElementById("loading").style.display = "block";
      var output = document.getElementById("console_output");
      output.innerHTML = "";
      var submitter = e.submitter;
      var action = submitter ? submitter.value : "";
      var formData = new FormData(this);
      if (submitter && !formData.has(submitter.name)) {
          formData.append(submitter.name, submitter.value);
      }
      if (action === "save") {
        fetch("/generate", { method: "POST", headers: { "X-Requested-With": "XMLHttpRequest" }, body: formData })
        .then(function(response) { return response.json(); })
        .then(function(data) {
          document.getElementById("loading").style.display = "none";
          output.innerHTML = data.success ? "<p>" + data.message + "</p>" : "<p style='color:red;'>Error: " + data.message + "</p>";
        })
        .catch(function(error) {
          console.error("Error:", error);
          document.getElementById("loading").style.display = "none";
          output.innerHTML = "<p style='color:red;'>Error: " + error + "</p>";
        });
      } else if (action === "generate") {
        fetch("/generate", { method: "POST", headers: { "X-Requested-With": "XMLHttpRequest" }, body: formData })
        .then(function(response) {
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          function read() {
            return reader.read().then(({done, value}) => {
              if (done) { document.getElementById("loading").style.display = "none"; return; }
              var text = decoder.decode(value, {stream: true});
              output.innerHTML += text;
              output.scrollTop = output.scrollHeight;
              return read();
            });
          }
          return read();
        })
        .catch(function(error) {
          console.error("Error:", error);
          document.getElementById("loading").style.display = "none";
          output.innerHTML = "<p style='color:red;'>Error: " + error + "</p>";
        });
      } else {
        document.getElementById("loading").style.display = "none";
        output.innerHTML = "<p style='color:red;'>Error: Unknown action</p>";
      }
    });
  </script>
</body>
</html>
"""

RESULT_TEMPLATE = """
<!doctype html>
<html>
<head>
  <title>Playlist Generator Result</title>
</head>
<body>
  <h1>{{ message }}</h1>
  <a href="/">Generate another playlist</a>
</body>
</html>
"""

# --- Load configuration initially ---
config = configparser.ConfigParser()
config.read('setup.conf')

def remove_think_tags(text):
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

def update_globals():
    global ollama_url_default, ollama_model_default, navidrome_url_default, navidrome_username_default, navidrome_password_default
    global context_window_default, max_attempts_default, user_likes_default, user_dislikes_default, favorite_artists_default
    global enable_navidrome, enable_plex, plex_server_url, plex_token, plex_machine_id, plex_playlist_type

    config.read('setup.conf')
    ollama_url_default = config.get('Ollama', 'url', fallback="http://localhost:11434/api/generate")
    ollama_model_default = config.get('Ollama', 'model', fallback="phi4:latest")
    navidrome_url_default = config.get('Navidrome', 'url', fallback="http://localhost:4533/rest")
    navidrome_username_default = config.get('Navidrome', 'username', fallback="ice")
    navidrome_password_default = config.get('Navidrome', 'password', fallback="!")
    context_window_default = config.get('General', 'context_window', fallback="8192")
    max_attempts_default = config.get('General', 'max_attempts', fallback="10")
    user_likes_default = config.get('User', 'likes', fallback="")
    user_dislikes_default = config.get('User', 'dislikes', fallback="")
    favorite_artists_default = config.get('User', 'favorite_artists', fallback="")

    enable_navidrome = config.get('Platforms', 'enable_navidrome', fallback='yes').lower() == 'yes'
    enable_plex = config.get('Platforms', 'enable_plex', fallback='no').lower() == 'yes'

    plex_server_url = config.get('Plex', 'server_url', fallback='http://localhost:32400')
    plex_token = config.get('Plex', 'plex_token', fallback='')
    plex_machine_id = config.get('Plex', 'machine_id', fallback='')
    plex_playlist_type = config.get('Plex', 'playlist_type', fallback='audio')

def get_playlist_from_ollama(prompt):
    if DEBUG_OLLAMA_RESPONSE:
        print("Using model:", ollama_model_default)
        print("Prompt sent to Ollama:")
        print(prompt)
    payload = {
        "model": ollama_model_default,
        "prompt": prompt,
        "format": {
            "type": "object",
            "properties": {
                "tracks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "artist": {"type": "string"},
                            "album": {"type": "string"}
                        },
                        "required": ["title", "artist", "album"]
                    }
                }
            },
            "required": ["tracks"]
        },
        "stream": False
    }
    try:
        response = requests.post(ollama_url_default, json=payload, timeout=300)
    except requests.exceptions.Timeout:
        print("Request to Ollama timed out")
        return []
    if response.status_code == 200:
        result = response.json()
        try:
            raw_response = result["response"]
            if DEBUG_OLLAMA_RESPONSE:
                print("Raw Ollama response (with COT):")
                print(raw_response)
            cleaned_response = remove_think_tags(raw_response).strip()
            if DEBUG_OLLAMA_RESPONSE:
                print("Cleaned Ollama response (COT removed):")
                print(cleaned_response)
            track_data = json.loads(cleaned_response)
            return track_data.get("tracks", [])
        except json.JSONDecodeError as e:
            print("Error decoding Ollama output:", e)
            return []
    else:
        print("Ollama API error:", response.status_code, response.text)
        return []

def search_track_in_navidrome(title, artist):
    query = f"{title} {artist}"
    params = {
        "query": query,
        "f": "json",
        "u": navidrome_username_default,
        "p": navidrome_password_default,
        "v": "1.16.1",
        "c": "python_script"
    }
    search_url = f"{navidrome_url_default}/search2"
    response = requests.get(search_url, params=params)
    if response.status_code == 200:
        try:
            result = response.json()
            songs = result["subsonic-response"]["searchResult2"]["song"]
            if isinstance(songs, list) and songs:
                return songs[0]["id"]
            elif isinstance(songs, dict):
                return songs.get("id")
            else:
                return None
        except KeyError:
            return None
    else:
        print("Navidrome search error:", response.status_code, response.text)
        return None

def create_playlist_in_navidrome(name, song_ids):
    params = {
        "u": navidrome_username_default,
        "p": navidrome_password_default,
        "v": "1.16.1",
        "c": "python_script",
        "name": name,
        "f": "json"
    }
    for song_id in song_ids:
        params.setdefault("songId", []).append(song_id)
    url = f"{navidrome_url_default}/createPlaylist"
    response = requests.get(url, params=params)
    if response.status_code == 200:
        if response.text.strip():
            try:
                data = response.json()
                return data["subsonic-response"]["playlist"].get("id")
            except (KeyError, json.JSONDecodeError) as e:
                print("Error parsing playlist creation response:", e)
                return None
        else:
            print("Playlist created successfully (no response body).")
            return "unknown"
    else:
        print("Navidrome createPlaylist error:", response.status_code, response.text)
        return None

def search_track_in_plex(title, artist):
    if not enable_plex:
        return None
    query_string = f"{title} {artist}"
    encoded_query = requests.utils.quote(query_string)
    url = f"{plex_server_url}/search?query={encoded_query}&type=10&X-Plex-Token={plex_token}"
    print("Plex search URL:", url)
    try:
        resp = requests.get(url, timeout=10)
        print("Plex search response code:", resp.status_code)
        if resp.status_code == 200:
            root = ET.fromstring(resp.text)
            for child in root.findall(".//Track"):
                rating_key = child.attrib.get("ratingKey")
                if rating_key:
                    print(f"Found Plex track ratingKey: {rating_key} for '{title}' by '{artist}'")
                    return rating_key
        else:
            print("Plex search error:", resp.status_code, resp.text)
    except Exception as e:
        print("Plex search exception:", e)
    return None

def create_playlist_in_plex(playlist_name, library_ids):
    if not enable_plex:
        return None
    if not library_ids:
        print("No Plex tracks found to create a playlist.")
        return None
    first_id = library_ids[0]
    create_url = (
        f"{plex_server_url}/playlists"
        f"?type={plex_playlist_type}"
        f"&title={requests.utils.quote(playlist_name)}"
        f"&smart=0"
        f"&uri=server://{plex_machine_id}/com.plexapp.plugins.library/{first_id}"
        f"?X-Plex-Token={plex_token}"
    )
    print("Plex create URL:", create_url)
    try:
        resp = requests.post(create_url, timeout=10)
        print("Plex create playlist response code:", resp.status_code)
        print("Plex create playlist response text:", resp.text)
        if resp.status_code != 200:
            print("Plex create playlist error:", resp.status_code, resp.text)
            return None
        root = ET.fromstring(resp.text)
        playlist_elem = root.find(".//Playlist")
        if not playlist_elem:
            print("Could not find <Playlist> in Plex response.")
            return None
        new_playlist_key = playlist_elem.attrib.get("ratingKey", None)
        if not new_playlist_key:
            print("Could not get the new playlist ratingKey from Plex.")
            return None
        for lib_id in library_ids[1:]:
            add_item_url = (
                f"{plex_server_url}/playlists/{new_playlist_key}/items"
                f"?uri=server://{plex_machine_id}/com.plexapp.plugins.library/{lib_id}"
                f"?X-Plex-Token={plex_token}"
            )
            print("Adding track with URL:", add_item_url)
            add_resp = requests.post(add_item_url, timeout=10)
            print("Add track response code:", add_resp.status_code)
            print("Add track response text:", add_resp.text)
            if add_resp.status_code != 200:
                print("Error adding track to Plex playlist:", add_resp.status_code, add_resp.text)
        print(f"Plex playlist '{playlist_name}' created with ratingKey = {new_playlist_key}")
        return new_playlist_key
    except Exception as e:
        print("Exception creating Plex playlist:", e)
        return None

def generate_playlist(playlist_name, prompt):
    update_globals()
    collected_tracks = []
    attempts = 0
    base_prompt = prompt
    max_attempts = int(max_attempts_default)
    required_tracks = 45
    navidrome_song_ids = []
    plex_library_ids = []
    
    while len(collected_tracks) < required_tracks and attempts < max_attempts:
        tracks = get_playlist_from_ollama(prompt)
        print(f"Ollama suggested {len(tracks)} tracks.")
        for track in tracks:
            if len(collected_tracks) >= required_tracks:
                break
            if any(t.get("title") == track["title"] and t.get("artist") == track["artist"] for t in collected_tracks):
                continue
            found_any = False
            if enable_navidrome:
                nd_id = search_track_in_navidrome(track["title"], track["artist"])
                if nd_id:
                    navidrome_song_ids.append(nd_id)
                    found_any = True
            if enable_plex:
                plex_id = search_track_in_plex(track["title"], track["artist"])
                if plex_id:
                    plex_library_ids.append(plex_id)
                    found_any = True
            if found_any:
                collected_tracks.append(track)
                print(f"Found: {track['title']} by {track['artist']}")
        if len(collected_tracks) < required_tracks:
            missing = required_tracks - len(collected_tracks)
            last_suggestions = collected_tracks[-10:]
            context_lines = [f"{t['title']} by {t['artist']}" for t in last_suggestions]
            context_str = ", ".join(context_lines)
            prompt = (
                f"{base_prompt}\n"
                f"Previously suggested (latest 10): {context_str}.\n"
                f"Provide {missing} additional tracks, distinct from both the seed songs and any previously returned tracks, "
                "that fit the refined criteria. Return only the JSON object. Do not include any introductory text or explanations."
            )
            attempts += 1
            print(f"Attempt {attempts}: Not enough tracks, updating prompt and retrying.")
    print(f"Collected {len(collected_tracks)} tracks.")
    if not collected_tracks:
        return None, "No tracks found. Exiting."
    random.shuffle(navidrome_song_ids)
    random.shuffle(plex_library_ids)
    nd_playlist_id = None
    plex_playlist_id = None
    if enable_navidrome:
        nd_playlist_id = create_playlist_in_navidrome(playlist_name, navidrome_song_ids)
    if enable_plex:
        plex_playlist_id = create_playlist_in_plex(playlist_name, plex_library_ids)
    message = f"Playlist '{playlist_name}' created."
    if nd_playlist_id:
        message += f" Navidrome ID: {nd_playlist_id}."
    if plex_playlist_id:
        message += f" Plex ratingKey: {plex_playlist_id}."
    return (nd_playlist_id, plex_playlist_id), message

def generate_playlist_stream(playlist_name, prompt):
    update_globals()
    yield f"<p>Starting playlist generation for '{playlist_name}'...</p>\n"
    collected_tracks = []
    attempts = 0
    base_prompt = prompt
    max_attempts = int(max_attempts_default)
    required_tracks = 45
    navidrome_song_ids = []
    plex_library_ids = []
    
    while len(collected_tracks) < required_tracks and attempts < max_attempts:
        tracks = get_playlist_from_ollama(prompt)
        yield f"<p>Ollama suggested {len(tracks)} tracks.</p>\n"
        for track in tracks:
            if len(collected_tracks) >= required_tracks:
                break
            if any(t.get("title") == track["title"] and t.get("artist") == track["artist"] for t in collected_tracks):
                continue
            found_any = False
            if enable_navidrome:
                nd_id = search_track_in_navidrome(track["title"], track["artist"])
                if nd_id:
                    navidrome_song_ids.append(nd_id)
                    found_any = True
            if enable_plex:
                plex_id = search_track_in_plex(track["title"], track["artist"])
                if plex_id:
                    plex_library_ids.append(plex_id)
                    found_any = True
            if found_any:
                collected_tracks.append(track)
                yield f"<p>Found: {track['title']} by {track['artist']}</p>\n"
        if len(collected_tracks) < required_tracks:
            missing = required_tracks - len(collected_tracks)
            last_suggestions = collected_tracks[-10:]
            context_lines = [f"{t['title']} by {t['artist']}" for t in last_suggestions]
            context_str = ", ".join(context_lines)
            prompt = (
                f"{base_prompt}\n"
                f"Previously suggested (latest 10): {context_str}.\n"
                f"Provide {missing} additional tracks, distinct from both the seed songs and any previously returned tracks, "
                "that fit the refined criteria. Return only the JSON object. Do not include any introductory text or explanations."
            )
            attempts += 1
            yield f"<p>Attempt {attempts}: Not enough tracks found. Updating prompt and retrying...</p>\n"
    yield f"<p>Collected {len(collected_tracks)} tracks total.</p>\n"
    if not collected_tracks:
        yield "<p>No tracks found. Exiting.</p>\n"
        return
    random.shuffle(navidrome_song_ids)
    random.shuffle(plex_library_ids)
    if enable_navidrome:
        nd_playlist_id = create_playlist_in_navidrome(playlist_name, navidrome_song_ids)
        yield f"<p>Navidrome playlist created with ID: {nd_playlist_id}</p>\n"
    if enable_plex:
        plex_playlist_id = create_playlist_in_plex(playlist_name, plex_library_ids)
        yield f"<p>Plex playlist created with ratingKey: {plex_playlist_id}</p>\n"
    yield "<p>Generation complete.</p>\n"

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    update_globals()
    return render_template_string(HOME_TEMPLATE,
                                  likes=user_likes_default,
                                  dislikes=user_dislikes_default,
                                  favorite_artists=favorite_artists_default,
                                  ollama_url=ollama_url_default,
                                  ollama_model=ollama_model_default,
                                  navidrome_url=navidrome_url_default,
                                  navidrome_username=navidrome_username_default,
                                  navidrome_password=navidrome_password_default,
                                  context_window=context_window_default,
                                  max_attempts=max_attempts_default,
                                  enable_navidrome = "yes" if enable_navidrome else "no",
                                  enable_plex = "yes" if enable_plex else "no",
                                  plex_server_url = plex_server_url,
                                  plex_token = plex_token,
                                  plex_machine_id = plex_machine_id,
                                  plex_playlist_type = plex_playlist_type)

@app.route("/generate", methods=["GET", "POST"])
def generate_route():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "save":
            likes = request.form.get("likes")
            dislikes = request.form.get("dislikes")
            favorite_artists = request.form.get("favorite_artists")
            ollama_url = request.form.get("ollama_url")
            ollama_model = request.form.get("ollama_model")
            navidrome_url = request.form.get("navidrome_url")
            navidrome_username = request.form.get("navidrome_username")
            navidrome_password = request.form.get("navidrome_password")
            context_window = request.form.get("context_window")
            max_attempts = request.form.get("max_attempts")
            # New fields for Platforms and Plex
            enable_navidrome_field = request.form.get("enable_navidrome")
            enable_plex_field = request.form.get("enable_plex")
            plex_server_url_field = request.form.get("plex_server_url")
            plex_token_field = request.form.get("plex_token")
            plex_machine_id_field = request.form.get("plex_machine_id")
            plex_playlist_type_field = request.form.get("plex_playlist_type")
            
            if not all([likes, dislikes, favorite_artists,
                        ollama_url, ollama_model, navidrome_url, navidrome_username, navidrome_password, context_window, max_attempts,
                        enable_navidrome_field, enable_plex_field, plex_server_url_field, plex_token_field, plex_machine_id_field, plex_playlist_type_field]):
                return jsonify({"success": False, "message": "Missing one or more required configuration fields."}), 400
            
            if enable_plex_field.lower() == "yes" and not all([plex_server_url_field, plex_token_field, plex_machine_id_field, plex_playlist_type_field]):
                return jsonify({"success": False, "message": "Missing Plex configuration fields."}), 400
            
            if not config.has_section('User'):
                config.add_section('User')
            config.set('User', 'likes', likes)
            config.set('User', 'dislikes', dislikes)
            config.set('User', 'favorite_artists', favorite_artists)
            if not config.has_section('Ollama'):
                config.add_section('Ollama')
            config.set('Ollama', 'url', ollama_url)
            config.set('Ollama', 'model', ollama_model)
            if not config.has_section('Navidrome'):
                config.add_section('Navidrome')
            config.set('Navidrome', 'url', navidrome_url)
            config.set('Navidrome', 'username', navidrome_username)
            config.set('Navidrome', 'password', navidrome_password)
            if not config.has_section('General'):
                config.add_section('General')
            config.set('General', 'context_window', context_window)
            config.set('General', 'max_attempts', max_attempts)
            if not config.has_section('Platforms'):
                config.add_section('Platforms')
            config.set('Platforms', 'enable_navidrome', enable_navidrome_field)
            config.set('Platforms', 'enable_plex', enable_plex_field)
            if not config.has_section('Plex'):
                config.add_section('Plex')
            config.set('Plex', 'server_url', plex_server_url_field)
            config.set('Plex', 'plex_token', plex_token_field)
            config.set('Plex', 'machine_id', plex_machine_id_field)
            config.set('Plex', 'playlist_type', plex_playlist_type_field)
            try:
                with open('setup.conf', 'w') as configfile:
                    config.write(configfile)
                return jsonify({"success": True, "message": "Configuration saved successfully."})
            except Exception as e:
                return jsonify({"success": False, "message": f"Failed to save configuration: {e}"}), 500
        
        elif action == "generate":
            update_globals()
            playlist_name = request.form.get("playlist_name")
            playlist_description = request.form.get("playlist_description")
            likes = request.form.get("likes")
            dislikes = request.form.get("dislikes")
            favorite_artists = request.form.get("favorite_artists")
            ollama_url = request.form.get("ollama_url")
            ollama_model = request.form.get("ollama_model")
            navidrome_url = request.form.get("navidrome_url")
            navidrome_username = request.form.get("navidrome_username")
            navidrome_password = request.form.get("navidrome_password")
            context_window = request.form.get("context_window")
            max_attempts = request.form.get("max_attempts")
            # New fields for Platforms and Plex
            enable_navidrome_field = request.form.get("enable_navidrome")
            enable_plex_field = request.form.get("enable_plex")
            plex_server_url_field = request.form.get("plex_server_url")
            plex_token_field = request.form.get("plex_token")
            plex_machine_id_field = request.form.get("plex_machine_id")
            plex_playlist_type_field = request.form.get("plex_playlist_type")
            
            if not all([playlist_name, playlist_description, likes, dislikes, favorite_artists,
                        ollama_url, ollama_model, navidrome_url, navidrome_username, navidrome_password, context_window, max_attempts,
                        enable_navidrome_field, enable_plex_field, plex_server_url_field, plex_token_field, plex_machine_id_field, plex_playlist_type_field]):
                return jsonify({"success": False, "message": "Missing one or more required fields for generation."}), 400
            
            if enable_plex_field.lower() == "yes" and not all([plex_server_url_field, plex_token_field, plex_machine_id_field, plex_playlist_type_field]):
                return jsonify({"success": False, "message": "Missing Plex configuration fields."}), 400

            if not config.has_section('User'):
                config.add_section('User')
            config.set('User', 'likes', likes)
            config.set('User', 'dislikes', dislikes)
            config.set('User', 'favorite_artists', favorite_artists)
            if not config.has_section('Ollama'):
                config.add_section('Ollama')
            config.set('Ollama', 'url', ollama_url)
            config.set('Ollama', 'model', ollama_model)
            if not config.has_section('Navidrome'):
                config.add_section('Navidrome')
            config.set('Navidrome', 'url', navidrome_url)
            config.set('Navidrome', 'username', navidrome_username)
            config.set('Navidrome', 'password', navidrome_password)
            if not config.has_section('General'):
                config.add_section('General')
            config.set('General', 'context_window', context_window)
            config.set('General', 'max_attempts', max_attempts)
            if not config.has_section('Platforms'):
                config.add_section('Platforms')
            config.set('Platforms', 'enable_navidrome', enable_navidrome_field)
            config.set('Platforms', 'enable_plex', enable_plex_field)
            if not config.has_section('Plex'):
                config.add_section('Plex')
            config.set('Plex', 'server_url', plex_server_url_field)
            config.set('Plex', 'plex_token', plex_token_field)
            config.set('Plex', 'machine_id', plex_machine_id_field)
            config.set('Plex', 'playlist_type', plex_playlist_type_field)
            try:
                with open('setup.conf', 'w') as configfile:
                    config.write(configfile)
            except Exception as e:
                return jsonify({"success": False, "message": f"Failed to save configuration: {e}"}), 500
            
            full_prompt = (
                f"Generate a JSON object with a single key, 'tracks'. The value of 'tracks' should be an array of 45 song objects. Each song object should have the following keys: 'title', 'artist', and 'album'.\n\n"
                f"The playlist is inspired by the name \"{playlist_name}\" and should be {playlist_description}.\n\n"
                f"Do your very best to include (or find songs resembling) {likes}.\n\n"
                f"Make sure you completely avoid {dislikes}.\n\n"
                f"Provide 45 additional tracks, distinct from both the seed songs and any previously returned tracks, that fit this refined criteria. Return only the JSON object. Do not include any introductory text or explanations."
            )
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                def generate():
                    for line in generate_playlist_stream(playlist_name, full_prompt):
                        yield line
                    yield "<p>Generation complete.</p>\n"
                return Response(generate(), mimetype='text/html')
            else:
                def generate():
                    yield "<html><head><title>Generating Playlist</title>"
                    yield """<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />"""
                    yield "</head><body>"
                    for line in generate_playlist_stream(playlist_name, full_prompt):
                        yield line
                    yield "<p><a href='/'>Back to Home</a></p>"
                    yield "</body></html>"
                return Response(generate(), mimetype='text/html')
        else:
            return jsonify({"success": False, "message": "Unknown action"}), 400
    else:
        update_globals()
        return render_template_string(HOME_TEMPLATE,
                                      likes=user_likes_default,
                                      dislikes=user_dislikes_default,
                                      favorite_artists=favorite_artists_default,
                                      ollama_url=ollama_url_default,
                                      ollama_model=ollama_model_default,
                                      navidrome_url=navidrome_url_default,
                                      navidrome_username=navidrome_username_default,
                                      navidrome_password=navidrome_password_default,
                                      context_window=context_window_default,
                                      max_attempts=max_attempts_default,
                                      enable_navidrome = "yes" if enable_navidrome else "no",
                                      enable_plex = "yes" if enable_plex else "no",
                                      plex_server_url = plex_server_url,
                                      plex_token = plex_token,
                                      plex_machine_id = plex_machine_id,
                                      plex_playlist_type = plex_playlist_type)

def main():
    playlist_name = input("Enter the playlist name: ")
    playlist_description = input("Enter the playlist description: ")
    likes = input("Enter your likes: ")
    dislikes = input("Enter your dislikes: ")
    favorite_artists = input("Enter your favorite artists (comma-separated): ")
    ollama_url = input("Enter the Ollama URL: ")
    ollama_model = input("Enter the Ollama Model: ")
    navidrome_url = input("Enter the Navidrome URL: ")
    navidrome_username = input("Enter the Navidrome Username: ")
    navidrome_password = input("Enter the Navidrome Password: ")
    context_window = input("Enter the Context Window: ")
    max_attempts = input("Enter the Max Retry Attempts: ")
    
    if not config.has_section('User'):
        config.add_section('User')
    config.set('User', 'likes', likes)
    config.set('User', 'dislikes', dislikes)
    config.set('User', 'favorite_artists', favorite_artists)
    if not config.has_section('Ollama'):
        config.add_section('Ollama')
    config.set('Ollama', 'url', ollama_url)
    config.set('Ollama', 'model', ollama_model)
    if not config.has_section('Navidrome'):
        config.add_section('Navidrome')
    config.set('Navidrome', 'url', navidrome_url)
    config.set('Navidrome', 'username', navidrome_username)
    config.set('Navidrome', 'password', navidrome_password)
    if not config.has_section('General'):
        config.add_section('General')
    config.set('General', 'context_window', context_window)
    config.set('General', 'max_attempts', max_attempts)
    with open('setup.conf', 'w') as configfile:
        config.write(configfile)
    
    full_prompt = (
        f"Generate a JSON object with a single key, 'tracks'. The value of 'tracks' should be an array of 45 song objects. Each song object should have the following keys: 'title', 'artist', and 'album'.\n\n"
        f"The playlist is inspired by the name \"{playlist_name}\" and should be {playlist_description}.\n\n"
        f"Do your very best to include (or find songs resembling) {likes}.\n\n"
        f"Make sure you completely avoid {dislikes}.\n\n"
        f"Provide 45 additional tracks, distinct from both the seed songs and any previously returned tracks, that fit this refined criteria. Return only the JSON object. Do not include any introductory text or explanations."
    )
    playlist_ids, message = generate_playlist(playlist_name, full_prompt)
    print(message)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "web":
        app.run(host="0.0.0.0", port=5555, debug=True, use_reloader=False)
    else:
        main()
