import os
import sqlite3
import time
from math import sqrt
from typing import Dict, Tuple, List, Optional

# Fixed feature order used for vectors
FEATURE_ORDER: List[str] = [
    'energy',
    'valence',
    'danceability',
    'tempo',
    'acousticness',
    'instrumentalness',
    'loudness',
    'speechiness',
]

# Default weights per feature (sum not required)
DEFAULT_WEIGHTS: Dict[str, float] = {
    'energy': 1.0,
    'valence': 1.0,
    'danceability': 1.0,
    'tempo': 0.5,
    'acousticness': 0.5,
    'instrumentalness': 0.3,
    'loudness': 0.3,
    'speechiness': 0.2,
}

_STATS_CACHE: Dict[str, Tuple[float, float]] = {}
_STATS_CACHE_TS: float = 0.0
_STATS_TTL_SECS: int = 300

# Vector cache for expensive computations
_VECTOR_CACHE: Dict[str, List[float]] = {}
_VECTOR_CACHE_MAX_SIZE: int = 1000


def _min_max(conn: sqlite3.Connection, col: str) -> Tuple[float, float]:
    cur = conn.cursor()
    cur.execute(f'SELECT MIN({col}), MAX({col}) FROM audio_features')
    row = cur.fetchone() or (None, None)
    return (row[0], row[1])


def get_feature_stats(db_path: str) -> Dict[str, Tuple[float, float]]:
    global _STATS_CACHE, _STATS_CACHE_TS
    now = time.time()
    if _STATS_CACHE and (now - _STATS_CACHE_TS) < _STATS_TTL_SECS:
        return _STATS_CACHE

    if not os.path.exists(db_path):
        return {}

    conn = sqlite3.connect(db_path)
    try:
        stats: Dict[str, Tuple[float, float]] = {}
        for col in FEATURE_ORDER:
            mn, mx = _min_max(conn, col)
            stats[col] = (mn, mx)
        _STATS_CACHE = stats
        _STATS_CACHE_TS = now
        return stats
    finally:
        conn.close()


def _normalize(value: float, mn: float, mx: float) -> float:
    if value is None or mn is None or mx is None:
        return 0.0
    if mx == mn:
        return 0.5  # neutral if no range
    # Clamp then scale 0..1
    if value < mn: value = mn
    if value > mx: value = mx
    return (value - mn) / (mx - mn)


def build_vector(features_row: Dict[str, float], stats: Dict[str, Tuple[float, float]]) -> List[float]:
    # Create cache key from features hash
    features_str = str(sorted(features_row.items()))
    stats_str = str(sorted(stats.items()))
    cache_key = f"{hash(features_str)}_{hash(stats_str)}"
    
    if cache_key in _VECTOR_CACHE:
        return _VECTOR_CACHE[cache_key]
    
    vec: List[float] = []
    for col in FEATURE_ORDER:
        val = features_row.get(col)
        mn, mx = stats.get(col, (None, None))
        vec.append(_normalize(val, mn, mx))
    
    # Cache the result
    if len(_VECTOR_CACHE) >= _VECTOR_CACHE_MAX_SIZE:
        # Simple LRU: remove oldest entries
        oldest_keys = list(_VECTOR_CACHE.keys())[:100]
        for key in oldest_keys:
            del _VECTOR_CACHE[key]
    
    _VECTOR_CACHE[cache_key] = vec
    return vec


def compute_distance(seed_vec: List[float], cand_vec: List[float], weights: Dict[str, float] = None) -> float:
    if weights is None:
        weights = DEFAULT_WEIGHTS
    # Weighted Euclidean distance
    s = 0.0
    for i, col in enumerate(FEATURE_ORDER):
        w = weights.get(col, 1.0)
        d = (seed_vec[i] - cand_vec[i])
        s += w * (d * d)
    return sqrt(s)


def compute_batch_distances(seed_vec: List[float], candidate_vectors: List[List[float]], 
                           weights: Dict[str, float] = None) -> List[float]:
    """Compute distances for multiple candidates at once (more efficient)"""
    if weights is None:
        weights = DEFAULT_WEIGHTS
    
    distances = []
    for cand_vec in candidate_vectors:
        s = 0.0
        for i, col in enumerate(FEATURE_ORDER):
            w = weights.get(col, 1.0)
            d = (seed_vec[i] - cand_vec[i])
            s += w * (d * d)
        distances.append(sqrt(s))
    
    return distances


def ensure_database_indexes(db_path: str) -> bool:
    """Ensure optimal database indexes exist for Sonic Traveller performance"""
    if not os.path.exists(db_path):
        return False
    
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        
        # Check if indexes exist
        cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'sonic_%'")
        existing_indexes = {row[0] for row in cur.fetchall()}
        
        indexes_to_create = []
        
        # Index for tracks table lookups
        if 'sonic_tracks_title_artist' not in existing_indexes:
            indexes_to_create.append(
                "CREATE INDEX sonic_tracks_title_artist ON tracks(title, artist)"
            )
        
        # Index for audio features lookups
        if 'sonic_audio_features_track_id' not in existing_indexes:
            indexes_to_create.append(
                "CREATE INDEX sonic_audio_features_track_id ON audio_features(track_id)"
            )
        
        # Index for combined lookups
        if 'sonic_tracks_id_title_artist' not in existing_indexes:
            indexes_to_create.append(
                "CREATE INDEX sonic_tracks_id_title_artist ON tracks(id, title, artist)"
            )
        
        # Create missing indexes
        for index_sql in indexes_to_create:
            try:
                cur.execute(index_sql)
                conn.commit()
            except Exception as e:
                print(f"Failed to create index: {e}")
                continue
        
        return True
        
    except Exception as e:
        print(f"Error ensuring database indexes: {e}")
        return False
    finally:
        conn.close()


def clear_caches():
    """Clear all caches (useful for testing or memory management)"""
    global _STATS_CACHE, _STATS_CACHE_TS, _VECTOR_CACHE
    _STATS_CACHE.clear()
    _STATS_CACHE_TS = 0.0
    _VECTOR_CACHE.clear()


