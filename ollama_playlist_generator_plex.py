import configparser
import json
import random
import re
import requests
from flask import Flask, request, render_template_string, jsonify, Response
import xml.etree.ElementTree as ET
import os
import datetime
import time

# --- Global Debug Flag ---
DEBUG_OLLAMA_RESPONSE = False  # Set to True to print prompt and raw responses from Ollama

# --- Define Templates at the Top ---
HOME_TEMPLATE = """
<!doctype html>
<html data-bs-theme="light">
<head>
  <title>Playlist Generator v0.9 by HNB (20.02.2025)</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    #artist_list { list-style-type: none; padding: 0; }
    #artist_list li { padding: 4px 0; }
    #console_output {
      height: 400px;
      overflow-y: scroll;
      border: 1px solid #ccc;
      padding: 10px;
      background-color: var(--bs-tertiary-bg);
      font-family: monospace;
    }
    .theme-toggle {
      position: fixed;
      top: 10px;
      right: 10px;
      z-index: 1000;
    }
  </style>
</head>
<body>
  <div class="theme-toggle">
    <button class="btn btn-sm" id="theme-toggle-btn">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-moon-stars" viewBox="0 0 16 16" id="dark-icon">
        <path d="M6 .278a.768.768 0 0 1 .08.858 7.208 7.208 0 0 0-.878 3.46c0 4.021 3.278 7.277 7.318 7.277.527 0 1.04-.055 1.533-.16a.787.787 0 0 1 .81.316.733.733 0 0 1-.031.893A8.349 8.349 0 0 1 8.344 16C3.734 16 0 12.286 0 7.71 0 4.266 2.114 1.312 5.124.06A.752.752 0 0 1 6 .278zM4.858 1.311A7.269 7.269 0 0 0 1.025 7.71c0 4.02 3.279 7.276 7.319 7.276a7.316 7.316 0 0 0 5.205-2.162c-.337.042-.68.063-1.029.063-4.61 0-8.343-3.714-8.343-8.29 0-1.167.242-2.278.681-3.286z"/>
        <path d="M10.794 3.148a.217.217 0 0 1 .412 0l.387 1.162c.173.518.579.924 1.097 1.097l1.162.387a.217.217 0 0 1 0 .412l-1.162.387a1.734 1.734 0 0 0-1.097 1.097l-.387 1.162a.217.217 0 0 1-.412 0l-.387-1.162A1.734 1.734 0 0 0 9.31 6.593l-1.162-.387a.217.217 0 0 1 0-.412l1.162-.387a1.734 1.734 0 0 0 1.097-1.097l.387-1.162z"/>
      </svg>
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-sun" viewBox="0 0 16 16" id="light-icon" style="display:none;">
        <path d="M8 11a3 3 0 1 1 0-6 3 3 0 0 1 0 6zm0 1a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM8 0a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 0zm0 13a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 13zm8-5a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2a.5.5 0 0 1 .5.5zM3 8a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2A.5.5 0 0 1 3 8zm10.657-5.657a.5.5 0 0 1 0 .707l-1.414 1.415a.5.5 0 1 1-.707-.708l1.414-1.414a.5.5 0 0 1 .707 0zm-9.193 9.193a.5.5 0 0 1 0 .707L3.05 13.657a.5.5 0 0 1-.707-.707l1.414-1.414a.5.5 0 0 1 .707 0zm9.193 2.121a.5.5 0 0 1-.707 0l-1.414-1.414a.5.5 0 0 1 .707-.707l1.414 1.414a.5.5 0 0 1 0 .707zM4.464 4.465a.5.5 0 0 1-.707 0L2.343 3.05a.5.5 0 1 1 .707-.707l1.414 1.414a.5.5 0 0 1 0 .708z"/>
      </svg>
    </button>
  </div>
  <div class="container my-5">
    <h1 class="mb-4">Playlist Generator v0.9 by HNB (20.02.2025)</h1>
    <div class="mb-3 text-end">
      <a href="/history" class="btn btn-outline-primary">View Playlist History</a>
    </div>
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
            <!-- Existing settings for Ollama, Navidrome, etc. -->
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
            <!-- New Platforms settings -->
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
            <!-- Plex-specific settings -->
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
            <div class="mb-3">
              <label for="plex_music_section_id" class="form-label">Plex Music Library Section ID:</label>
              <input type="text" class="form-control" id="plex_music_section_id" name="plex_music_section_id" value="{{ plex_music_section_id }}">
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
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    // Dark mode toggle functionality
    document.addEventListener('DOMContentLoaded', function() {
      const themeToggleBtn = document.getElementById('theme-toggle-btn');
      const darkIcon = document.getElementById('dark-icon');
      const lightIcon = document.getElementById('light-icon');
      const htmlElement = document.documentElement;
      
      // Check for saved theme preference or use system preference
      const savedTheme = localStorage.getItem('theme');
      if (savedTheme) {
        htmlElement.setAttribute('data-bs-theme', savedTheme);
        updateIcon(savedTheme);
      } else {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const theme = prefersDark ? 'dark' : 'light';
        htmlElement.setAttribute('data-bs-theme', theme);
        updateIcon(theme);
      }
      
      // Toggle theme when button is clicked
      themeToggleBtn.addEventListener('click', function() {
        const currentTheme = htmlElement.getAttribute('data-bs-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        htmlElement.setAttribute('data-bs-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateIcon(newTheme);
      });
      
      function updateIcon(theme) {
        if (theme === 'dark') {
          darkIcon.style.display = 'none';
          lightIcon.style.display = 'block';
          themeToggleBtn.classList.remove('btn-dark');
          themeToggleBtn.classList.add('btn-light');
        } else {
          darkIcon.style.display = 'block';
          lightIcon.style.display = 'none';
          themeToggleBtn.classList.remove('btn-light');
          themeToggleBtn.classList.add('btn-dark');
        }
      }
    });
    
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

# Add this new route to view playlist history

HISTORY_TEMPLATE = """
<!doctype html>
<html data-bs-theme="light">
<head>
  <title>Playlist Generator - History</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    .theme-toggle {
      position: fixed;
      top: 10px;
      right: 10px;
      z-index: 1000;
    }
  </style>
</head>
<body>
  <div class="theme-toggle">
    <button class="btn btn-sm" id="theme-toggle-btn">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-moon-stars" viewBox="0 0 16 16" id="dark-icon">
        <path d="M6 .278a.768.768 0 0 1 .08.858 7.208 7.208 0 0 0-.878 3.46c0 4.021 3.278 7.277 7.318 7.277.527 0 1.04-.055 1.533-.16a.787.787 0 0 1 .81.316.733.733 0 0 1-.031.893A8.349 8.349 0 0 1 8.344 16C3.734 16 0 12.286 0 7.71 0 4.266 2.114 1.312 5.124.06A.752.752 0 0 1 6 .278zM4.858 1.311A7.269 7.269 0 0 0 1.025 7.71c0 4.02 3.279 7.276 7.319 7.276a7.316 7.316 0 0 0 5.205-2.162c-.337.042-.68.063-1.029.063-4.61 0-8.343-3.714-8.343-8.29 0-1.167.242-2.278.681-3.286z"/>
        <path d="M10.794 3.148a.217.217 0 0 1 .412 0l.387 1.162c.173.518.579.924 1.097 1.097l1.162.387a.217.217 0 0 1 0 .412l-1.162.387a1.734 1.734 0 0 0-1.097 1.097l-.387 1.162a.217.217 0 0 1-.412 0l-.387-1.162A1.734 1.734 0 0 0 9.31 6.593l-1.162-.387a.217.217 0 0 1 0-.412l1.162-.387a1.734 1.734 0 0 0 1.097-1.097l.387-1.162z"/>
      </svg>
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-sun" viewBox="0 0 16 16" id="light-icon" style="display:none;">
        <path d="M8 11a3 3 0 1 1 0-6 3 3 0 0 1 0 6zm0 1a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM8 0a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 0zm0 13a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 13zm8-5a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2a.5.5 0 0 1 .5.5zM3 8a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2A.5.5 0 0 1 3 8zm10.657-5.657a.5.5 0 0 1 0 .707l-1.414 1.415a.5.5 0 1 1-.707-.708l1.414-1.414a.5.5 0 0 1 .707 0zm-9.193 9.193a.5.5 0 0 1 0 .707L3.05 13.657a.5.5 0 0 1-.707-.707l1.414-1.414a.5.5 0 0 1 .707 0zm9.193 2.121a.5.5 0 0 1-.707 0l-1.414-1.414a.5.5 0 0 1 .707-.707l1.414 1.414a.5.5 0 0 1 0 .707zM4.464 4.465a.5.5 0 0 1-.707 0L2.343 3.05a.5.5 0 1 1 .707-.707l1.414 1.414a.5.5 0 0 1 0 .708z"/>
      </svg>
    </button>
  </div>
  <div class="container my-5">
    <h1 class="mb-4">Your Playlist History</h1>
    <a href="/" class="btn btn-primary mb-3">Back to Generator</a>
    
    <div class="row">
      {% for playlist in playlists %}
      <div class="col-md-6 mb-3">
        <div class="card">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0">{{ playlist.name }}</h5>
            <div class="rating">
              {% for i in range(5) %}
                <button class="btn btn-sm {% if playlist.rating == i+1 %}btn-warning{% else %}btn-outline-warning{% endif %}" 
                  onclick="ratePlaylist({{ playlist.id }}, {{ i+1 }})">{{ i+1 }}</button>
              {% endfor %}
            </div>
          </div>
          <div class="card-body">
            <p class="small">Created: {{ playlist.created }}</p>
            {% if playlist.navidrome_id %}
              <p>Navidrome ID: {{ playlist.navidrome_id }}</p>
            {% endif %}
            {% if playlist.plex_id %}
              <p>Plex ID: {{ playlist.plex_id }}</p>
            {% endif %}
            <div class="accordion" id="tracks{{ playlist.id }}">
              <div class="accordion-item">
                <h2 class="accordion-header" id="heading{{ playlist.id }}">
                  <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse{{ playlist.id }}">
                    View Tracks ({{ playlist.tracks|length }})
                  </button>
                </h2>
                <div id="collapse{{ playlist.id }}" class="accordion-collapse collapse" data-bs-parent="#tracks{{ playlist.id }}">
                  <div class="accordion-body">
                    <ul class="list-group">
                      {% for track in playlist.tracks %}
                        <li class="list-group-item">{{ track.title }} by {{ track.artist }} ({{ track.album }})</li>
                      {% endfor %}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      {% endfor %}
    </div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    // Dark mode toggle functionality
    document.addEventListener('DOMContentLoaded', function() {
      const themeToggleBtn = document.getElementById('theme-toggle-btn');
      const darkIcon = document.getElementById('dark-icon');
      const lightIcon = document.getElementById('light-icon');
      const htmlElement = document.documentElement;
      
      // Check for saved theme preference or use system preference
      const savedTheme = localStorage.getItem('theme');
      if (savedTheme) {
        htmlElement.setAttribute('data-bs-theme', savedTheme);
        updateIcon(savedTheme);
      } else {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const theme = prefersDark ? 'dark' : 'light';
        htmlElement.setAttribute('data-bs-theme', theme);
        updateIcon(theme);
      }
      
      // Toggle theme when button is clicked
      themeToggleBtn.addEventListener('click', function() {
        const currentTheme = htmlElement.getAttribute('data-bs-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        htmlElement.setAttribute('data-bs-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateIcon(newTheme);
      });
      
      function updateIcon(theme) {
        if (theme === 'dark') {
          darkIcon.style.display = 'none';
          lightIcon.style.display = 'block';
          themeToggleBtn.classList.remove('btn-dark');
          themeToggleBtn.classList.add('btn-light');
        } else {
          darkIcon.style.display = 'block';
          lightIcon.style.display = 'none';
          themeToggleBtn.classList.remove('btn-light');
          themeToggleBtn.classList.add('btn-dark');
        }
      }
    });
    
    function ratePlaylist(playlistId, rating) {
      fetch('/rate_playlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ playlist_id: playlistId, rating: rating })
      }).then(response => {
        if (response.ok) {
          window.location.reload();
        }
      });
    }
  </script>
</body>
</html>
"""

# --- Load configuration initially ---
config = configparser.ConfigParser()
config.read('setup.conf')

def remove_think_tags(text):
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

def get_config_value(section, key, default=""):
    """Retrieve configuration value from environment variables first, then config file"""
    env_key = f"PLAYLIST_GEN_{section.upper()}_{key.upper()}"
    env_value = os.environ.get(env_key)
    if env_value is not None:
        return env_value
    
    if config.has_section(section) and config.has_option(section, key):
        return config.get(section, key, fallback=default)
    return default

def update_globals():
    global ollama_url_default, ollama_model_default, navidrome_url_default, navidrome_username_default
    global navidrome_password_default, context_window_default, max_attempts_default, user_likes_default
    global user_dislikes_default, favorite_artists_default, enable_navidrome, enable_plex, plex_server_url
    global plex_token, plex_machine_id, plex_playlist_type, plex_music_section_id

    config.read('setup.conf')
    # Use Ollama's default URL if not explicitly set
    ollama_url_default = get_config_value('Ollama', 'url', "http://localhost:11434/api/generate")
    
    # Use Ollama's model defaults with fallback to phi4:latest
    ollama_model_default = get_config_value('Ollama', 'model', "phi4:latest")
    
    # Check if we need to ping Ollama to get available models
    if ollama_model_default == "auto" or not ollama_model_default:
        try:
            # Try to get models from Ollama API
            ollama_base_url = ollama_url_default.split('/api/')[0]
            models_url = f"{ollama_base_url}/api/tags"
            response = requests.get(models_url, timeout=5)
            if response.status_code == 200:
                models_data = response.json()
                available_models = [model.get('name') for model in models_data.get('models', [])]
                # Prioritize specific models if available
                preferred_models = ["phi4", "phi3", "llama3", "mixtral", "gemma"]
                for preferred in preferred_models:
                    for model in available_models:
                        if preferred in model.lower():
                            ollama_model_default = model
                            break
                    if ollama_model_default != "auto" and ollama_model_default:
                        break
                        
                # If no preferred model found, use the first available one
                if ollama_model_default == "auto" or not ollama_model_default:
                    if available_models:
                        ollama_model_default = available_models[0]
                    else:
                        ollama_model_default = "phi4:latest"  # Default fallback
            else:
                ollama_model_default = "phi4:latest"  # Default fallback
        except Exception as e:
            print(f"Error getting Ollama models: {e}")
            ollama_model_default = "phi4:latest"  # Default fallback
    
    navidrome_url_default = get_config_value('Navidrome', 'url', "http://localhost:4533/rest")
    navidrome_username_default = get_config_value('Navidrome', 'username', "ice")
    navidrome_password_default = get_config_value('Navidrome', 'password', "!")
    context_window_default = get_config_value('General', 'context_window', "8192")
    max_attempts_default = get_config_value('General', 'max_attempts', "10")
    user_likes_default = get_config_value('User', 'likes', "")
    user_dislikes_default = get_config_value('User', 'dislikes', "")
    favorite_artists_default = get_config_value('User', 'favorite_artists', "")

    enable_navidrome = get_config_value('Platforms', 'enable_navidrome', 'yes').lower() == 'yes'
    enable_plex = get_config_value('Platforms', 'enable_plex', 'no').lower() == 'yes'

    plex_server_url = get_config_value('Plex', 'server_url', "http://localhost:32400")
    plex_token = get_config_value('Plex', 'plex_token', "")
    plex_machine_id = get_config_value('Plex', 'machine_id', "")
    plex_playlist_type = get_config_value('Plex', 'playlist_type', "audio")
    plex_music_section_id = get_config_value('Plex', 'music_section_id', "1")

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
            songs = result["subsonic-response"]["searchResult2"].get("song", [])
            # Make sure `songs` is a list
            if isinstance(songs, dict):
                songs = [songs]  # If only one result was returned as a dict

            if not songs:
                return None

            # Filter out any songs with "live" in title or album (case-insensitive).
            filtered = [
                s for s in songs 
                if "live" not in s["title"].lower() 
                and "live" not in s["album"].lower()
            ]

            if filtered:
                return filtered[0]["id"]
            else:
                # Fallback to the very first item if all are "live" or no filter match
                return songs[0]["id"]
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
                print("Error parsing Navidrome playlist creation response:", e)
                return None
        else:
            print("Navidrome playlist created successfully (no response body).")
            return "unknown"
    else:
        print("Navidrome createPlaylist error:", response.status_code, response.text)
        return None

# --- PLEX FUNCTIONS ---
def search_track_in_plex(title, artist):
    if not enable_plex:
        return None
        
    # Use cache for Plex searches
    cache_key = f"{title}|{artist}"
    cached_result = plex_cache.get(cache_key)
    if cached_result is not None:
        return cached_result
        
    query_string = f"{artist} {title}"
    encoded_query = requests.utils.quote(query_string)
    url = f"{plex_server_url}/hubs/search/?X-Plex-Token={plex_token}&query={encoded_query}&sectionId={plex_music_section_id}&limit=10"
    print("Plex search URL:", url)
    try:
        resp = requests.get(url, timeout=10)
        print("Plex search response code:", resp.status_code)
        print("Plex search response text:", resp.text)
        if resp.status_code == 200:
            root = ET.fromstring(resp.text)
            for hub in root.findall(".//Hub"):
                if hub.attrib.get("type") == "track":
                    # Gather all track elements
                    track_candidates = hub.findall("./Track")
                    
                    # Filter them to exclude "live" in track or album
                    filtered_tracks = []
                    for track_el in track_candidates:
                        track_title = track_el.attrib.get("title", "").lower()
                        album_title = track_el.attrib.get("parentTitle", "").lower()
                        if "live" not in track_title and "live" not in album_title:
                            filtered_tracks.append(track_el)

                    preferred_list = filtered_tracks if filtered_tracks else track_candidates

                    for track_el in preferred_list:
                        rating_key = track_el.attrib.get("ratingKey")
                        library_section_id = track_el.attrib.get("librarySectionID")
                        if rating_key and library_section_id:
                            result = {"ratingKey": rating_key, "librarySectionID": library_section_id}
                            plex_cache.set(cache_key, result)
                            print(f"Found Plex track ratingKey: {rating_key} for '{title}' by '{artist}', librarySectionID={library_section_id}")
                            return result
        else:
            print(f"Plex API error: {resp.status_code} - {resp.text}")
            plex_cache.set(cache_key, None)
            return None
    except requests.exceptions.Timeout:
        print(f"Timeout when searching for '{title}' by '{artist}' in Plex")
        plex_cache.set(cache_key, None)
        return None
    except requests.exceptions.ConnectionError:
        print(f"Connection error to Plex server when searching for '{title}' by '{artist}'")
        plex_cache.set(cache_key, None)
        return None
    except ET.ParseError as e:
        print(f"XML parse error in Plex response: {e}")
        plex_cache.set(cache_key, None)
        return None
    except Exception as e:
        print(f"Unexpected error searching for track in Plex: {e}")
        plex_cache.set(cache_key, None)
        return None
    
    plex_cache.set(cache_key, None)
    return None


def create_playlist_in_plex(name, library_ids):
    if not enable_plex:
        return None
    if not library_ids:
        print("No Plex tracks found to create a playlist.")
        return None
    first_id = library_ids[0]
    # Build the base URI for the first track
    base_uri = f"server://{plex_machine_id}/com.plexapp.plugins.library/library/metadata/{first_id}"
    encoded_base_uri = requests.utils.quote(base_uri, safe='/:')
    create_params = (
        f"?type={plex_playlist_type}"
        f"&title={requests.utils.quote(name)}"
        f"&smart=0"
        f"&uri={encoded_base_uri}"
        f"&X-Plex-Token={plex_token}"
    )
    url = f"{plex_server_url}/playlists{create_params}"
    print("Plex create URL:", url)
    try:
        resp = requests.post(url, timeout=10)
        print("Plex create playlist response code:", resp.status_code)
        print("Plex create playlist response text:", resp.text)
        if resp.status_code != 200:
            print("Plex create playlist error:", resp.status_code, resp.text)
            return None
        root = ET.fromstring(resp.text)
        playlist_elem = root.find(".//Playlist")
        if playlist_elem is None:
            print("Could not find <Playlist> in Plex response.")
            return None
        new_playlist_key = playlist_elem.attrib.get("ratingKey", None)
        if not new_playlist_key:
            print("Could not get the new playlist ratingKey from Plex.")
            return None

        print(f"Plex playlist '{name}' created with ratingKey = {new_playlist_key}")

        # If additional tracks exist, add them in one call.
        if len(library_ids) > 1:
            additional_ids = library_ids[1:]
            joined_ids = ','.join(additional_ids)
            track_uri = f"server://{plex_machine_id}/com.plexapp.plugins.library/library/metadata/{joined_ids}"
            encoded_track_uri = requests.utils.quote(track_uri, safe='/:')
            add_url = f"{plex_server_url}/playlists/{new_playlist_key}/items?uri={encoded_track_uri}&X-Plex-Token={plex_token}"
            print("Adding additional tracks with URL:")
            print(add_url)
            add_resp = requests.put(add_url, timeout=10)
            print("Add tracks response code:", add_resp.status_code)
            print("Add tracks response text:", add_resp.text)
        else:
            print("Only one track provided; no additional tracks to add.")
        return new_playlist_key
    except Exception as e:
        print("Exception creating Plex playlist:", e)
        return None

# -------------------- GENERATION FUNCTIONS --------------------
def generate_playlist_core(playlist_name, prompt, output_callback=None):
    """Core playlist generation functionality used by both standard and streaming modes
    
    Args:
        playlist_name: Name of the playlist to create
        prompt: Prompt to send to Ollama
        output_callback: Optional function to call with status messages (for streaming)
    
    Returns:
        tuple: ((navidrome_id, plex_id), status_message)
    """
    update_globals()
    
    def emit_message(msg):
        if output_callback:
            output_callback(msg)
        print(msg)
    
    emit_message(f"Starting playlist generation for '{playlist_name}'...")
    collected_tracks = []
    attempts = 0
    base_prompt = prompt
    max_attempts = int(max_attempts_default)
    required_tracks = 45
    navidrome_song_ids = []
    plex_ratingkeys = []
    base_section_id = None

    while len(collected_tracks) < required_tracks and attempts < max_attempts:
        tracks = get_playlist_from_ollama(base_prompt)
        emit_message(f"Ollama suggested {len(tracks)} tracks.")
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
                plex_res = search_track_in_plex(track["title"], track["artist"])
                if plex_res:
                    if base_section_id is None:
                        base_section_id = plex_res["librarySectionID"]
                    if plex_res["librarySectionID"] == base_section_id:
                        plex_ratingkeys.append(plex_res["ratingKey"])
                        found_any = True
                    else:
                        emit_message(f"Skipping track '{track['title']}' from section {plex_res['librarySectionID']} (base={base_section_id}).")
            if found_any:
                collected_tracks.append(track)
                emit_message(f"Found: {track['title']} by {track['artist']}")
        
        if len(collected_tracks) < required_tracks:
            missing = required_tracks - len(collected_tracks)
            last_suggestions = collected_tracks[-10:]
            context_lines = [f"{t['title']} by {t['artist']}" for t in last_suggestions]
            context_str = ", ".join(context_lines)
            base_prompt = (
                f"{base_prompt}\nPreviously suggested (latest 10): {context_str}.\n"
                f"Provide {missing} additional tracks, distinct from both the seed songs and any previously returned tracks, "
                "that fit the refined criteria. Return only the JSON object. Do not include any introductory text or explanations."
            )
            attempts += 1
            emit_message(f"Attempt {attempts}: Not enough tracks found. Updating prompt and retrying...")
    
    emit_message(f"Collected {len(collected_tracks)} tracks total.")
    if not collected_tracks:
        emit_message("No tracks found. Exiting.")
        return (None, None), "No tracks found. Exiting."
    
    random.shuffle(navidrome_song_ids)
    random.shuffle(plex_ratingkeys)
    
    nd_playlist_id = None
    plex_playlist_id = None
    
    if enable_navidrome and navidrome_song_ids:
        nd_playlist_id = create_playlist_in_navidrome(playlist_name, navidrome_song_ids)
        emit_message(f"Navidrome playlist created with ID: {nd_playlist_id}")
    
    if enable_plex and plex_ratingkeys:
        plex_playlist_id = create_playlist_in_plex(playlist_name, plex_ratingkeys)
        emit_message(f"Plex playlist created with ratingKey: {plex_playlist_id}")
    
    # Save playlist history
    save_playlist_history(playlist_name, collected_tracks, nd_playlist_id, plex_playlist_id)
    
    message = f"Playlist '{playlist_name}' created."
    if nd_playlist_id:
        message += f" Navidrome ID: {nd_playlist_id}."
    if plex_playlist_id:
        message += f" Plex ratingKey: {plex_playlist_id}."
    
    emit_message("Generation complete.")
    return (nd_playlist_id, plex_playlist_id), message

# Replace the generate_playlist function
def generate_playlist(playlist_name, prompt):
    return generate_playlist_core(playlist_name, prompt)

# Replace the generate_playlist_stream function
def generate_playlist_stream(playlist_name, prompt):
    def streamer(message):
        yield f"<p>{message}</p>\n"
    
    def wrapper(msg):
        return f"<p>{msg}</p>\n"
    
    for chunk in generate_playlist_core(playlist_name, prompt, wrapper):
        yield chunk

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
                                  enable_navidrome="yes" if enable_navidrome else "no",
                                  enable_plex="yes" if enable_plex else "no",
                                  plex_server_url=plex_server_url,
                                  plex_token=plex_token,
                                  plex_machine_id=plex_machine_id,
                                  plex_playlist_type=plex_playlist_type,
                                  plex_music_section_id=plex_music_section_id)

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
            enable_navidrome_field = request.form.get("enable_navidrome")
            enable_plex_field = request.form.get("enable_plex")
            plex_server_url_field = request.form.get("plex_server_url")
            plex_token_field = request.form.get("plex_token")
            plex_machine_id_field = request.form.get("plex_machine_id")
            plex_playlist_type_field = request.form.get("plex_playlist_type")
            plex_music_section_id_field = request.form.get("plex_music_section_id")
            
            if not all([likes, dislikes, favorite_artists,
                        ollama_url, ollama_model, navidrome_url, navidrome_username, navidrome_password, context_window, max_attempts,
                        enable_navidrome_field, enable_plex_field, plex_server_url_field, plex_token_field, plex_machine_id_field, plex_playlist_type_field, plex_music_section_id_field]):
                return jsonify({"success": False, "message": "Missing one or more required configuration fields."}), 400
            
            if enable_plex_field.lower() == "yes" and not all([plex_server_url_field, plex_token_field, plex_machine_id_field, plex_playlist_type_field, plex_music_section_id_field]):
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
            config.set('Plex', 'music_section_id', plex_music_section_id_field)
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
            enable_navidrome_field = request.form.get("enable_navidrome")
            enable_plex_field = request.form.get("enable_plex")
            plex_server_url_field = request.form.get("plex_server_url")
            plex_token_field = request.form.get("plex_token")
            plex_machine_id_field = request.form.get("plex_machine_id")
            plex_playlist_type_field = request.form.get("plex_playlist_type")
            plex_music_section_id_field = request.form.get("plex_music_section_id")
            
            if not all([playlist_name, playlist_description, likes, dislikes, favorite_artists,
                        ollama_url, ollama_model, navidrome_url, navidrome_username, navidrome_password, context_window, max_attempts,
                        enable_navidrome_field, enable_plex_field, plex_server_url_field, plex_token_field, plex_machine_id_field, plex_playlist_type_field, plex_music_section_id_field]):
                return jsonify({"success": False, "message": "Missing one or more required fields for generation."}), 400
            
            if enable_plex_field.lower() == "yes" and not all([plex_server_url_field, plex_token_field, plex_machine_id_field, plex_playlist_type_field, plex_music_section_id_field]):
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
            config.set('Plex', 'music_section_id', plex_music_section_id_field)
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
                def generator():
                    for line in generate_playlist_stream(playlist_name, full_prompt):
                        yield line
                    yield "<p>Generation complete.</p>\n"
                return Response(generator(), mimetype='text/html')
            else:
                def generator():
                    yield "<html><head><title>Generating Playlist</title>"
                    yield """<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />"""
                    yield "</head><body>"
                    for line in generate_playlist_stream(playlist_name, full_prompt):
                        yield line
                    yield "<p><a href='/'>Back to Home</a></p>"
                    yield "</body></html>"
                return Response(generator(), mimetype='text/html')
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
                                      max_attempts=max_attempts_default)

@app.route("/history")
def history():
    playlists = get_playlist_history()
    # Format dates for display
    for p in playlists:
        try:
            created_date = datetime.datetime.fromisoformat(p['created'])
            p['created'] = created_date.strftime("%B %d, %Y at %H:%M")
        except ValueError:
            pass
    return render_template_string(HISTORY_TEMPLATE, playlists=playlists)

@app.route("/rate_playlist", methods=["POST"])
def rate_playlist_route():
    data = request.json
    playlist_id = data.get('playlist_id')
    rating = data.get('rating')
    
    if not playlist_id or not rating:
        return jsonify({"success": False, "message": "Missing playlist_id or rating"}), 400
    
    success = rate_playlist(playlist_id, rating)
    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "Failed to save rating"}), 500

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
    playlist_id, message = generate_playlist(playlist_name, full_prompt)
    print(message)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "web":
        app.run(host="0.0.0.0", port=5555, debug=True, use_reloader=False)
    else:
        main()

# Add the SearchCache class if not already present
class SearchCache:
    def __init__(self, max_size=1000, ttl=3600):  # TTL in seconds (1 hour)
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl
    
    def get(self, key):
        if key in self.cache:
            timestamp, value = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                # Expired
                del self.cache[key]
        return None
    
    def set(self, key, value):
        # Ensure cache doesn't grow too large
        if len(self.cache) >= self.max_size:
            # Remove oldest items
            oldest_keys = sorted(self.cache, key=lambda k: self.cache[k][0])[:len(self.cache) // 10]  # Remove 10% oldest
            for old_key in oldest_keys:
                del self.cache[old_key]
        
        self.cache[key] = (time.time(), value)

# Create cache instances
navidrome_cache = SearchCache()
plex_cache = SearchCache()

# Add these functions for playlist history management
def save_playlist_history(playlist_name, tracks, navidrome_id=None, plex_id=None):
    """Save playlist details to history file"""
    history_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'playlist_history')
    os.makedirs(history_dir, exist_ok=True)
    
    history_file = os.path.join(history_dir, 'playlist_history.json')
    
    # Load existing history or create new
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
        except json.JSONDecodeError:
            history = []
    else:
        history = []
    
    # Create new entry
    new_entry = {
        'id': len(history) + 1,
        'name': playlist_name,
        'created': datetime.datetime.now().isoformat(),
        'navidrome_id': navidrome_id,
        'plex_id': plex_id,
        'tracks': tracks,
        'rating': None  # To be filled later by user
    }
    
    history.append(new_entry)
    
    # Save updated history
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)
    
    return new_entry['id']

def get_playlist_history():
    """Retrieve saved playlist history"""
    history_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'playlist_history')
    history_file = os.path.join(history_dir, 'playlist_history.json')
    
    if not os.path.exists(history_file):
        return []
    
    try:
        with open(history_file, 'r') as f:
            history = json.load(f)
        return history
    except (json.JSONDecodeError, IOError):
        return []

def rate_playlist(playlist_id, rating):
    """Save user rating for a playlist"""
    history_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'playlist_history')
    history_file = os.path.join(history_dir, 'playlist_history.json')
    
    if not os.path.exists(history_file):
        return False
    
    try:
        with open(history_file, 'r') as f:
            history = json.load(f)
        
        # Find and update the playlist
        for playlist in history:
            if playlist['id'] == playlist_id:
                playlist['rating'] = rating
                break
        else:
            return False  # Playlist not found
        
        # Save updated history
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        return True
    except (json.JSONDecodeError, IOError):
        return False
