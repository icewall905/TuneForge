import os
import sqlite3
from typing import Dict, List, Tuple, Optional


REQUIRED_FEATURE_COLUMNS: List[str] = [
    'track_id',
    'energy',
    'valence',
    'tempo',
    'danceability',
    'acousticness',
    'instrumentalness',
    'loudness',
    'speechiness',
]


def check_audio_feature_schema(db_path: str) -> Tuple[bool, List[str]]:
    """Return (ok, missing_columns) for audio_features table."""
    if not os.path.exists(db_path):
        return False, REQUIRED_FEATURE_COLUMNS.copy()
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute('PRAGMA table_info(audio_features)')
        rows = cur.fetchall() or []
        existing = {r[1] for r in rows}
        missing = [c for c in REQUIRED_FEATURE_COLUMNS if c not in existing]
        return len(missing) == 0, missing
    finally:
        conn.close()


def fetch_track_features(db_path: str, track_id: int) -> Optional[Dict[str, float]]:
    """Fetch features for a single track_id; returns None if missing."""
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM audio_features WHERE track_id = ?', (track_id,))
        col_names = [d[1] for d in cur.description] if cur.description else []
        row = cur.fetchone()
        if not row:
            return None
        data = {col_names[i]: row[i] for i in range(len(row))}
        return data
    finally:
        conn.close()


def fetch_batch_features(db_path: str, track_ids: List[int]) -> Dict[int, Dict[str, float]]:
    """Fetch features for a batch of track_ids; returns mapping only for those found."""
    if not os.path.exists(db_path) or not track_ids:
        return {}
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        q_marks = ','.join('?' for _ in track_ids)
        cur.execute(f'SELECT * FROM audio_features WHERE track_id IN ({q_marks})', track_ids)
        col_names = [d[1] for d in cur.description] if cur.description else []
        result: Dict[int, Dict[str, float]] = {}
        for row in cur.fetchall() or []:
            data = {col_names[i]: row[i] for i in range(len(row))}
            tid = int(data.get('track_id')) if data.get('track_id') is not None else None
            if tid is not None:
                result[tid] = data
        return result
    finally:
        conn.close()


