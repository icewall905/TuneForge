# TuneForge

![TuneForge Logo](https://raw.githubusercontent.com/icewall905/tuneforge/main/static/images/logo_big.jpeg)

**TuneForge is a smart, local-first music playlist generator that uses AI to create personalized playlists from your own music library.** It connects to your Navidrome or Plex server, learns your tastes, and builds playlists for any mood or occasion.

---

## ✨ Key Features

-   **🤖 AI-Powered Playlist Generation**: Two distinct modes for creating the perfect playlist:
    -   **Ask a Friend**: Simply describe the kind of playlist you want in plain English (e.g., "a playlist for a rainy afternoon" or "upbeat 80s rock tracks"). TuneForge's LLM will understand and build it for you.
    -   **Sonic Traveller**: Pick a "seed" track from your library and let the AI find other songs that share similar audio characteristics like tempo, energy, danceability, and more. It's music discovery, powered by your own collection.
-   **🎵 Deep Audio Analysis**: TuneForge automatically scans your music library, extracting 8 different audio features to enable intelligent, similarity-based playlist creation.
-   **📺 Seamless Integration**: Directly connect to and save playlists on your **Navidrome** or **Plex** server.
-   **📂 Local First**: Your music and data stay with you. TuneForge runs on your own machine.
-   **📤 Export Options**: Save any created playlist as a standard `.m3u` or `.json` file for maximum compatibility.
-   **📈 Real-Time UI**: Watch as playlists are generated in real-time and see the AI's feedback loop improve suggestions.

---

## 🚀 Getting Started

### Prerequisites

1.  **Python 3.8+**
2.  **Ollama**: You need a running instance of [Ollama](https://ollama.com/) with a model pulled (e.g., `ollama run llama3`).

### Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/icewall905/tuneforge.git](https://github.com/icewall905/tuneforge.git)
    cd tuneforge
    ```

2.  **Set Up a Virtual Environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the Application**
    -   Copy `config.ini.example` to `config.ini`.
    -   Open `config.ini` and fill in the required details:
        -   Under `[OLLAMA]`, set `url` to your Ollama API endpoint and specify the `model`.
        -   Under `[MUSIC]`, set `library_path` to the location of your music files.
        -   (Optional) Configure the `[NAVIDROME]` and `[PLEX]` sections if you wish to save playlists there.

5.  **Run the Application**
    ```bash
    python run.py
    ```
    TuneForge will now be running at `http://localhost:5395`.

---

## 🎧 Usage

### 1. Index Your Music Library

-   The first time you run TuneForge, it will begin indexing your music library as defined in `config.ini`.
-   You can monitor the progress of the audio analysis from the "Audio Analysis" page in the web UI. This process only needs to be done once per track.

### 2. Create a Playlist with "Ask a Friend"

-   Navigate to the homepage.
-   In the text box, describe the playlist you want. Be creative!
-   Click "Ask a Friend" and watch the playlist get generated.

### 3. Discover Music with "Sonic Traveller"

-   Go to the "Sonic Traveller" page.
-   Use the search bar to find and select a "seed" track from your library.
-   Adjust the similarity threshold (a lower value means more similar tracks).
-   Click "Ask a Friend" to start the generation process based on the seed track's audio features.

### 4. Save Your Playlist

-   Once a playlist is generated, you will see options to save it to Navidrome or Plex (if configured) or export it as an `.m3u` or `.json` file.

---

## 🛠️ Architecture

-   **Backend**: Flask (Python)
-   **AI**: Ollama for Large Language Model integration.
-   **Audio Analysis**: `librosa` for feature extraction.
-   **Database**: SQLite for storing track metadata and audio features.
-   **Frontend**: Standard HTML, CSS, and JavaScript for a real-time, responsive UI.

---

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
