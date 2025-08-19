#!/usr/bin/env python3
"""
Audio Analysis Service for TuneForge

This module provides database integration for the audio analysis system.
It handles storing extracted features, managing analysis status, and
processing the analysis queue.
"""

import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioAnalysisService:
    """
    Service class for managing audio analysis database operations.
    
    This class handles:
    - Storing extracted audio features
    - Updating analysis status in tracks table
    - Managing the analysis queue
    - Retrieving analysis results
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize the AudioAnalysisService.
        
        Args:
            db_path: Path to the SQLite database (defaults to local_music.db)
        """
        if db_path is None:
            # Use the same database as the main application
            db_path = os.path.join(os.path.dirname(__file__), 'db', 'local_music.db')

        # Ensure base DB and tracks table exist before altering columns
        try:
            from app.routes import init_local_music_db
            init_local_music_db()
        except Exception:
            # If import fails outside app context, fallback to creating minimal tracks table
            try:
                os.makedirs(os.path.join(os.path.dirname(__file__), 'db'), exist_ok=True)
                with sqlite3.connect(db_path) as conn:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS tracks (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            file_path TEXT UNIQUE NOT NULL,
                            title TEXT,
                            artist TEXT,
                            album TEXT,
                            genre TEXT,
                            year INTEGER,
                            track_number INTEGER,
                            duration REAL,
                            file_size INTEGER,
                            last_modified REAL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    conn.commit()
            except Exception as _:
                pass
        
        self.db_path = db_path
        self._ensure_database_structure()
        logger.info(f"AudioAnalysisService initialized with database: {db_path}")
    
    def _ensure_database_structure(self):
        """Ensure all required tables exist with proper structure."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                
                # Check if audio_features table exists
                cursor = conn.execute("PRAGMA table_info(audio_features)")
                if not cursor.fetchall():
                    logger.info("Creating audio_features table...")
                    conn.execute("""
                        CREATE TABLE audio_features (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            track_id INTEGER NOT NULL,
                            tempo REAL,
                            key TEXT,
                            mode TEXT,
                            energy REAL,
                            danceability REAL,
                            valence REAL,
                            acousticness REAL,
                            instrumentalness REAL,
                            loudness REAL,
                            speechiness REAL,
                            spectral_centroid REAL,
                            spectral_rolloff REAL,
                            spectral_bandwidth REAL,
                            duration REAL,
                            sample_rate INTEGER,
                            num_samples INTEGER,
                            analysis_version TEXT DEFAULT '1.0',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE
                        )
                    """)
                    
                    # Create indexes for performance
                    conn.execute("CREATE INDEX idx_audio_features_track_id ON audio_features(track_id)")
                    conn.execute("CREATE INDEX idx_audio_features_tempo ON audio_features(tempo)")
                    conn.execute("CREATE INDEX idx_audio_features_key ON audio_features(key)")
                    conn.execute("CREATE INDEX idx_audio_features_energy ON audio_features(energy)")
                    conn.execute("CREATE INDEX idx_audio_features_danceability ON audio_features(danceability)")
                    
                    logger.info("audio_features table created successfully")
                
                # Check if analysis_queue table exists
                cursor = conn.execute("PRAGMA table_info(analysis_queue)")
                if not cursor.fetchall():
                    logger.info("Creating analysis_queue table...")
                    conn.execute("""
                        CREATE TABLE analysis_queue (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            track_id INTEGER NOT NULL,
                            priority INTEGER DEFAULT 3,
                            status TEXT DEFAULT 'queued',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            started_at TIMESTAMP,
                            completed_at TIMESTAMP,
                            error_message TEXT,
                            retry_count INTEGER DEFAULT 0,
                            max_retries INTEGER DEFAULT 3,
                            FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE
                        )
                    """)
                    
                    # Create indexes for performance
                    conn.execute("CREATE INDEX idx_analysis_queue_status ON analysis_queue(status)")
                    conn.execute("CREATE INDEX idx_analysis_queue_priority ON analysis_queue(priority)")
                    conn.execute("CREATE INDEX idx_analysis_queue_track_id ON analysis_queue(track_id)")
                    
                    logger.info("analysis_queue table created successfully")
                
                # Check if tracks table has analysis columns
                cursor = conn.execute("PRAGMA table_info(tracks)")
                columns = {row[1] for row in cursor.fetchall()}
                
                if 'analysis_status' not in columns:
                    logger.info("Adding analysis_status column to tracks table...")
                    conn.execute("ALTER TABLE tracks ADD COLUMN analysis_status TEXT DEFAULT 'pending'")
                
                if 'analysis_date' not in columns:
                    logger.info("Adding analysis_date column to tracks table...")
                    conn.execute("ALTER TABLE tracks ADD COLUMN analysis_date TIMESTAMP")
                
                if 'analysis_error' not in columns:
                    logger.info("Adding analysis_error column to tracks table...")
                    conn.execute("ALTER TABLE tracks ADD COLUMN analysis_error TEXT")
                
                conn.commit()
                logger.info("Database structure verification completed")
                
        except Exception as e:
            logger.error(f"Error ensuring database structure: {e}")
            raise
    
    def store_audio_features(self, track_id: int, features: Dict[str, Any]) -> bool:
        """
        Store extracted audio features for a track.
        
        Args:
            track_id: ID of the track in the tracks table
            features: Dictionary of extracted features
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                
                # Check if features already exist for this track
                cursor = conn.execute("SELECT id FROM audio_features WHERE track_id = ?", (track_id,))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing features
                    conn.execute("""
                        UPDATE audio_features SET
                            tempo = ?, key = ?, mode = ?, energy = ?, danceability = ?,
                            valence = ?, acousticness = ?, instrumentalness = ?, loudness = ?, speechiness = ?,
                            spectral_centroid = ?, spectral_rolloff = ?, spectral_bandwidth = ?,
                            duration = ?, sample_rate = ?, num_samples = ?, 
                            analysis_version = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE track_id = ?
                    """, (
                        features.get('tempo'), features.get('key'), features.get('mode'),
                        features.get('energy'), features.get('danceability'), features.get('valence'),
                        features.get('acousticness'), features.get('instrumentalness'), features.get('loudness'),
                        features.get('speechiness'), features.get('spectral_centroid'), features.get('spectral_rolloff'),
                        features.get('spectral_bandwidth'), features.get('duration'), features.get('sample_rate'),
                        features.get('num_samples'), features.get('analysis_version', '1.0'), track_id
                    ))
                    logger.info(f"Updated audio features for track {track_id}")
                else:
                    # Insert new features
                    conn.execute("""
                        INSERT INTO audio_features (
                            track_id, tempo, key, mode, energy, danceability, valence,
                            acousticness, instrumentalness, loudness, speechiness,
                            spectral_centroid, spectral_rolloff, spectral_bandwidth,
                            duration, sample_rate, num_samples, analysis_version
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        track_id, features.get('tempo'), features.get('key'), features.get('mode'),
                        features.get('energy'), features.get('danceability'), features.get('valence'),
                        features.get('acousticness'), features.get('instrumentalness'), features.get('loudness'),
                        features.get('speechiness'), features.get('spectral_centroid'), features.get('spectral_rolloff'),
                        features.get('spectral_bandwidth'), features.get('duration'), features.get('sample_rate'),
                        features.get('num_samples'), features.get('analysis_version', '1.0')
                    ))
                    logger.info(f"Inserted audio features for track {track_id}")
                
                # Update tracks table analysis status
                conn.execute("""
                    UPDATE tracks SET 
                        analysis_status = 'analyzed',
                        analysis_date = CURRENT_TIMESTAMP,
                        analysis_error = NULL
                    WHERE id = ?
                """, (track_id,))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error storing audio features for track {track_id}: {e}")
            return False
    
    def update_analysis_status(self, track_id: int, status: str, error_message: str = None) -> bool:
        """
        Update the analysis status of a track.
        
        Args:
            track_id: ID of the track
            status: New status ('pending', 'analyzing', 'analyzed', 'error')
            error_message: Error message if status is 'error'
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                if status == 'error':
                    conn.execute("""
                        UPDATE tracks SET 
                            analysis_status = ?, 
                            analysis_error = ?,
                            analysis_date = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (status, error_message, track_id))
                else:
                    conn.execute("""
                        UPDATE tracks SET 
                            analysis_status = ?,
                            analysis_error = NULL
                        WHERE id = ?
                    """, (status, track_id))
                
                conn.commit()
                logger.info(f"Updated analysis status for track {track_id} to {status}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating analysis status for track {track_id}: {e}")
            return False
    
    def get_tracks_for_analysis(self, limit: int = 100, priority: int = 3) -> List[Dict[str, Any]]:
        """
        Get tracks that need audio analysis.
        
        Args:
            limit: Maximum number of tracks to return
            priority: Priority level (1=high, 5=low)
            
        Returns:
            List of track dictionaries with file paths
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT t.id, t.file_path, t.analysis_status, t.analysis_error
                    FROM tracks t
                    WHERE t.analysis_status IN ('pending', 'error')
                    AND t.file_path IS NOT NULL
                    AND t.file_path != ''
                    ORDER BY 
                        CASE 
                            WHEN t.analysis_status = 'error' THEN 1
                            ELSE 2
                        END,
                        t.id
                    LIMIT ?
                """, (limit,))
                
                tracks = []
                for row in cursor.fetchall():
                    tracks.append({
                        'id': row[0],
                        'file_path': row[1],
                        'analysis_status': row[2],
                        'analysis_error': row[3]
                    })
                
                logger.info(f"Found {len(tracks)} tracks for analysis")
                return tracks
                
        except Exception as e:
            logger.error(f"Error getting tracks for analysis: {e}")
            return []
    
    def get_analysis_progress(self) -> Dict[str, Any]:
        """
        Get overall analysis progress statistics.
        
        Returns:
            Dictionary with analysis statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT 
                        analysis_status,
                        COUNT(*) as count
                    FROM tracks 
                    GROUP BY analysis_status
                """)
                
                status_counts = dict(cursor.fetchall())
                
                # Calculate totals
                total_tracks = sum(status_counts.values())
                analyzed_tracks = status_counts.get('analyzed', 0)
                pending_tracks = status_counts.get('pending', 0)
                error_tracks = status_counts.get('error', 0)
                
                progress = {
                    'total_tracks': total_tracks,
                    'analyzed_tracks': analyzed_tracks,
                    'pending_tracks': pending_tracks,
                    'error_tracks': error_tracks,
                    'progress_percentage': round((analyzed_tracks / total_tracks * 100) if total_tracks > 0 else 0, 1),
                    'status_counts': status_counts
                }
                
                return progress
                
        except Exception as e:
            logger.error(f"Error getting analysis progress: {e}")
            return {
                'total_tracks': 0,
                'analyzed_tracks': 0,
                'pending_tracks': 0,
                'error_tracks': 0,
                'progress_percentage': 0,
                'status_counts': {}
            }
    
    def get_track_features(self, track_id: int) -> Optional[Dict[str, Any]]:
        """
        Get stored audio features for a specific track.
        
        Args:
            track_id: ID of the track
            
        Returns:
            Dictionary of features or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM audio_features WHERE track_id = ?
                """, (track_id,))
                
                row = cursor.fetchone()
                if row:
                    # Convert to dictionary
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting features for track {track_id}: {e}")
            return None
    
    def cleanup_old_analysis_data(self, days_old: int = 30) -> int:
        """
        Clean up old analysis data to save space.
        
        Args:
            days_old: Remove data older than this many days
            
        Returns:
            Number of records removed
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Remove old audio features
                cursor = conn.execute("""
                    DELETE FROM audio_features 
                    WHERE created_at < datetime('now', '-{} days')
                """.format(days_old))
                
                removed_features = cursor.rowcount
                
                # Remove old analysis queue entries
                cursor = conn.execute("""
                    DELETE FROM analysis_queue 
                    WHERE created_at < datetime('now', '-{} days')
                """.format(days_old))
                
                removed_queue = cursor.rowcount
                
                conn.commit()
                total_removed = removed_features + removed_queue
                
                logger.info(f"Cleaned up {total_removed} old analysis records ({removed_features} features, {removed_queue} queue)")
                return total_removed
                
        except Exception as e:
            logger.error(f"Error cleaning up old analysis data: {e}")
            return 0


def main():
    """Test function for the AudioAnalysisService"""
    print("🎵 TuneForge Audio Analysis Service Test")
    print("=" * 50)
    
    try:
        # Initialize service
        service = AudioAnalysisService()
        print("✅ AudioAnalysisService initialized successfully")
        
        # Test database structure
        print("\n🔍 Testing database structure...")
        progress = service.get_analysis_progress()
        print(f"📊 Analysis Progress:")
        print(f"   - Total tracks: {progress['total_tracks']}")
        print(f"   - Analyzed: {progress['analyzed_tracks']}")
        print(f"   - Pending: {progress['pending_tracks']}")
        print(f"   - Errors: {progress['error_tracks']}")
        print(f"   - Progress: {progress['progress_percentage']}%")
        
        # Test getting tracks for analysis
        print("\n🔍 Testing track retrieval...")
        tracks = service.get_tracks_for_analysis(limit=5)
        print(f"📁 Found {len(tracks)} tracks ready for analysis")
        
        if tracks:
            print("   Sample tracks:")
            for track in tracks[:3]:
                print(f"   - ID: {track['id']}, Status: {track['analysis_status']}")
        
        print("\n🚀 Audio Analysis Service is ready for Phase 3, Task 3.1!")
        print("📊 Ready to integrate with AudioAnalyzer for feature storage")
        
    except Exception as e:
        print(f"❌ Service test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
