#!/usr/bin/env python3
"""
Audio Analysis Monitor for TuneForge

This module provides monitoring capabilities for the audio analysis system:
- Progress tracking over time with timestamps
- Stalled analysis detection
- Progress rate calculation and anomaly detection
- Configurable monitoring thresholds
"""

import os
import time
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health status enumeration for audio analysis"""
    HEALTHY = "healthy"
    WARNING = "warning"
    STALLED = "stalled"
    ERROR = "error"
    UNKNOWN = "unknown"

@dataclass
class ProgressSnapshot:
    """Represents a snapshot of analysis progress at a specific time"""
    timestamp: datetime
    total_tracks: int
    analyzed_tracks: int
    pending_tracks: int
    error_tracks: int
    progress_percentage: float
    processing_rate: Optional[float] = None  # tracks per minute
    estimated_completion: Optional[datetime] = None

# Import the configuration manager
from monitoring_config import MonitoringConfig, get_config_manager

class AudioAnalysisMonitor:
    """
    Monitors audio analysis progress and detects stalled analysis.
    
    Features:
    - Progress tracking with timestamps
    - Stalled analysis detection
    - Progress rate calculation
    - Health status monitoring
    - Configurable thresholds
    """
    
    def __init__(self, db_path: str = None, config: MonitoringConfig = None):
        """
        Initialize the AudioAnalysisMonitor.
        
        Args:
            db_path: Path to the SQLite database
            config: Monitoring configuration (uses defaults if None)
        """
        if db_path is None:
            # Use the same database as the main application
            db_path = os.path.join(os.path.dirname(__file__), 'db', 'local_music.db')
        
        self.db_path = db_path
        
        # Use configuration manager if no config provided
        if config is None:
            config_manager = get_config_manager()
            self.config = config_manager.get_monitoring_config()
        else:
            self.config = config
        
        self._ensure_monitoring_tables()
        
        logger.info(f"AudioAnalysisMonitor initialized with database: {db_path}")
        logger.info(f"Stall detection timeout: {self.config.stall_detection_timeout}s")
        logger.info(f"Monitoring interval: {self.config.monitoring_interval}s")
    
    def _ensure_monitoring_tables(self):
        """Ensure monitoring tables exist with proper structure."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                
                # Create analysis_progress_history table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS analysis_progress_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        total_tracks INTEGER NOT NULL,
                        analyzed_tracks INTEGER NOT NULL,
                        pending_tracks INTEGER NOT NULL,
                        error_tracks INTEGER NOT NULL,
                        progress_percentage REAL NOT NULL,
                        processing_rate REAL,
                        estimated_completion TIMESTAMP,
                        health_status TEXT DEFAULT 'unknown'
                    )
                """)
                
                # Create index for efficient timestamp-based queries
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_progress_history_timestamp 
                    ON analysis_progress_history(timestamp)
                """)
                
                # Create index for health status queries
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_progress_history_health 
                    ON analysis_progress_history(health_status)
                """)
                
                conn.commit()
                logger.info("Monitoring tables created/verified successfully")
                
        except Exception as e:
            logger.error(f"Error creating monitoring tables: {e}")
            raise
    
    def capture_progress_snapshot(self) -> ProgressSnapshot:
        """
        Capture current progress snapshot and store in database.
        
        Returns:
            ProgressSnapshot object with current progress data
        """
        try:
            from audio_analysis_service import AudioAnalysisService
            service = AudioAnalysisService(self.db_path)
            progress = service.get_analysis_progress()
            
            # Calculate processing rate if we have previous snapshots
            processing_rate = self._calculate_processing_rate()
            
            # Estimate completion time
            estimated_completion = self._estimate_completion_time(progress, processing_rate)
            
            # Create snapshot
            snapshot = ProgressSnapshot(
                timestamp=datetime.now(),
                total_tracks=progress['total_tracks'],
                analyzed_tracks=progress['analyzed_tracks'],
                pending_tracks=progress['pending_tracks'],
                error_tracks=progress['error_tracks'],
                progress_percentage=progress['progress_percentage'],
                processing_rate=processing_rate,
                estimated_completion=estimated_completion
            )
            
            # Store in database
            self._store_progress_snapshot(snapshot)
            
            logger.debug(f"Progress snapshot captured: {snapshot.progress_percentage}% complete")
            return snapshot
            
        except Exception as e:
            logger.error(f"Error capturing progress snapshot: {e}")
            # Return a minimal snapshot with error status
            return ProgressSnapshot(
                timestamp=datetime.now(),
                total_tracks=0,
                analyzed_tracks=0,
                pending_tracks=0,
                error_tracks=0,
                progress_percentage=0.0
            )
    
    def _calculate_processing_rate(self) -> Optional[float]:
        """
        Calculate current processing rate (tracks per minute).
        
        Returns:
            Processing rate in tracks per minute, or None if insufficient data
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get the last 2 snapshots to calculate rate
                cursor = conn.execute("""
                    SELECT analyzed_tracks, timestamp 
                    FROM analysis_progress_history 
                    ORDER BY timestamp DESC 
                    LIMIT 2
                """)
                
                snapshots = cursor.fetchall()
                if len(snapshots) < 2:
                    return None
                
                # Calculate rate between last two snapshots
                current_analyzed, current_time = snapshots[0]
                previous_analyzed, previous_time = snapshots[1]
                
                # Parse timestamps
                if isinstance(current_time, str):
                    current_time = datetime.fromisoformat(current_time.replace('Z', '+00:00'))
                if isinstance(previous_time, str):
                    previous_time = datetime.fromisoformat(previous_time.replace('Z', '+00:00'))
                
                time_diff = (current_time - previous_time).total_seconds() / 60.0  # minutes
                tracks_diff = current_analyzed - previous_analyzed
                
                if time_diff > 0 and tracks_diff >= 0:
                    return tracks_diff / time_diff
                
                return None
                
        except Exception as e:
            logger.error(f"Error calculating processing rate: {e}")
            return None
    
    def _estimate_completion_time(self, progress: Dict[str, Any], 
                                 processing_rate: Optional[float]) -> Optional[datetime]:
        """
        Estimate completion time based on current progress and rate.
        
        Args:
            progress: Current progress dictionary
            processing_rate: Current processing rate in tracks per minute
            
        Returns:
            Estimated completion datetime, or None if cannot estimate
        """
        if not processing_rate or processing_rate <= 0:
            return None
        
        pending_tracks = progress['pending_tracks']
        if pending_tracks <= 0:
            return None
        
        # Calculate minutes remaining
        minutes_remaining = pending_tracks / processing_rate
        
        # Add to current time
        estimated_completion = datetime.now() + timedelta(minutes=minutes_remaining)
        
        return estimated_completion
    
    def _store_progress_snapshot(self, snapshot: ProgressSnapshot):
        """Store progress snapshot in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO analysis_progress_history (
                        timestamp, total_tracks, analyzed_tracks, pending_tracks,
                        error_tracks, progress_percentage, processing_rate,
                        estimated_completion, health_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    snapshot.timestamp.isoformat(),
                    snapshot.total_tracks,
                    snapshot.analyzed_tracks,
                    snapshot.pending_tracks,
                    snapshot.error_tracks,
                    snapshot.progress_percentage,
                    snapshot.processing_rate,
                    snapshot.estimated_completion.isoformat() if snapshot.estimated_completion else None,
                    self._determine_health_status(snapshot).value
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error storing progress snapshot: {e}")
    
    def _determine_health_status(self, snapshot: ProgressSnapshot) -> HealthStatus:
        """
        Determine health status based on current snapshot and historical data.
        
        Args:
            snapshot: Current progress snapshot
            
        Returns:
            HealthStatus enum value
        """
        try:
            # Check if analysis is stalled
            if self._is_analysis_stalled():
                return HealthStatus.STALLED
            
            # Check for errors
            if snapshot.error_tracks > 0:
                error_rate = snapshot.error_tracks / snapshot.total_tracks
                if error_rate > 0.1:  # More than 10% errors
                    return HealthStatus.ERROR
            
            # Check processing rate with short-term smoothing to avoid flicker
            if snapshot.processing_rate is not None:
                recent_avg_rate = self._get_recent_average_processing_rate(limit=3)
                if (
                    recent_avg_rate is not None
                    and recent_avg_rate < self.config.min_progress_threshold
                ):
                    return HealthStatus.WARNING
            
            # Check if analysis is complete
            if snapshot.progress_percentage >= 100.0:
                return HealthStatus.HEALTHY
            
            # Check if analysis is progressing normally
            if snapshot.processing_rate and snapshot.processing_rate > 0:
                return HealthStatus.HEALTHY
            
            return HealthStatus.UNKNOWN
            
        except Exception as e:
            logger.error(f"Error determining health status: {e}")
            return HealthStatus.UNKNOWN
    
    def _is_analysis_stalled(self) -> bool:
        """
        Check if audio analysis has stalled (no progress for configured timeout).
        
        Returns:
            True if analysis is stalled, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get the most recent snapshot
                cursor = conn.execute("""
                    SELECT analyzed_tracks, timestamp 
                    FROM analysis_progress_history 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """)
                
                latest = cursor.fetchone()
                if not latest:
                    return False
                
                analyzed_tracks, timestamp = latest
                
                # Parse timestamp
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                
                # Check if enough time has passed
                time_since_update = (datetime.now() - timestamp).total_seconds()
                
                if time_since_update < self.config.stall_detection_timeout:
                    return False
                
                # If nothing is actively analyzing, we consider the system stopped, not stalled
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM tracks WHERE analysis_status = 'analyzing'
                """)
                analyzing_count = cursor.fetchone()[0]
                if analyzing_count == 0:
                    return False
                
                # Check if there are pending tracks (work remaining)
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM tracks WHERE analysis_status = 'pending'
                """)
                pending_count = cursor.fetchone()[0]
                
                # Analysis is stalled if there are pending tracks and no progress for timeout period
                return pending_count > 0
                
        except Exception as e:
            logger.error(f"Error checking if analysis is stalled: {e}")
            return False
    
    def _detect_anomalies(self, snapshot: ProgressSnapshot) -> List[str]:
        """
        Detect anomalies in the analysis progress.
        
        Args:
            snapshot: Current progress snapshot
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        try:
            # Check for sudden drops in progress
            if snapshot.progress_percentage < 100.0:
                recent_history = self._get_recent_progress_history(hours=1)
                if len(recent_history) >= 2:
                    # Check if progress went backwards
                    for i in range(len(recent_history) - 1):
                        current = recent_history[i]
                        previous = recent_history[i + 1]
                        
                        if current['progress_percentage'] < previous['progress_percentage']:
                            drop = previous['progress_percentage'] - current['progress_percentage']
                            if drop > 1.0:  # More than 1% drop
                                anomalies.append(f"Progress dropped by {drop:.1f}% in the last hour")
                                break
            
            # Check for unusually slow processing (use smoothed average over recent samples)
            if snapshot.processing_rate is not None and snapshot.processing_rate > 0:
                recent_avg_rate = self._get_recent_average_processing_rate(limit=3)
                if (
                    recent_avg_rate is not None
                    and recent_avg_rate < self.config.min_progress_threshold
                ):
                    anomalies.append(
                        f"Processing rate ({recent_avg_rate:.2f} tracks/min) is below optimal threshold"
                    )
            
            # Check for high error rates
            if snapshot.error_tracks > 0 and snapshot.total_tracks > 0:
                error_rate = (snapshot.error_tracks / snapshot.total_tracks) * 100
                if error_rate > 5.0:  # More than 5% errors
                    anomalies.append(f"High error rate: {error_rate:.1f}% of tracks failed analysis")
            
            # Check for stuck analysis (no progress for extended period)
            if snapshot.progress_percentage < 100.0:
                recent_history = self._get_recent_progress_history(hours=2)
                if len(recent_history) >= 5:
                    # Check if progress has been stagnant
                    recent_progress = [h['progress_percentage'] for h in recent_history[:5]]
                    # Consider it real stagnation only if there is work pending and something analyzing
                    if len(set(recent_progress)) == 1:
                        try:
                            with sqlite3.connect(self.db_path) as conn:
                                sc = dict(conn.execute("SELECT analysis_status, COUNT(*) FROM tracks GROUP BY analysis_status").fetchall())
                                if sc.get('pending', 0) > 0 and sc.get('analyzing', 0) > 0:
                                    anomalies.append("Progress has been stagnant for the last 2 hours")
                        except Exception:
                            # Fallback to previous behavior if status check fails
                            anomalies.append("Progress has been stagnant for the last 2 hours")
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
        
        return anomalies

    def _get_recent_average_processing_rate(self, limit: int = 3) -> Optional[float]:
        """Compute the average processing rate over the most recent snapshots.

        Uses a small window to smooth transient dips and reduce UI warning flicker.

        Args:
            limit: Number of most recent snapshots to average over.

        Returns:
            Average processing rate or None if insufficient data.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT processing_rate
                    FROM analysis_progress_history
                    WHERE processing_rate IS NOT NULL
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
                rates = [row[0] for row in cursor.fetchall() if row[0] is not None and row[0] > 0]
                if not rates:
                    return None
                return sum(rates) / len(rates)
        except Exception as e:
            logger.error(f"Error computing recent average processing rate: {e}")
            return None
    
    def get_stall_analysis(self) -> Dict[str, Any]:
        """
        Get detailed analysis of potential stalls and their causes.
        
        Returns:
            Dictionary with stall analysis information
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get recent progress history
                cursor = conn.execute("""
                    SELECT timestamp, analyzed_tracks, pending_tracks, progress_percentage, processing_rate
                    FROM analysis_progress_history 
                    ORDER BY timestamp DESC 
                    LIMIT 10
                """)
                
                history = []
                for row in cursor.fetchall():
                    history.append({
                        'timestamp': row[0],
                        'analyzed_tracks': row[1],
                        'pending_tracks': row[2],
                        'progress_percentage': row[3],
                        'processing_rate': row[4]
                    })
                
                # Analyze for stalls
                stall_indicators = []
                
                if len(history) >= 2:
                    # Check for no progress
                    latest = history[0]
                    previous = history[1]
                    
                    if latest['analyzed_tracks'] == previous['analyzed_tracks']:
                        time_diff = self._parse_timestamp(latest['timestamp']) - self._parse_timestamp(previous['timestamp'])
                        if time_diff.total_seconds() > self.config.stall_detection_timeout:
                            stall_indicators.append(f"No progress for {time_diff.total_seconds() / 60:.1f} minutes")
                    
                    # Check for stuck progress
                    if latest['progress_percentage'] < 100.0:
                        stagnant_count = 0
                        for i in range(len(history) - 1):
                            if abs(history[i]['progress_percentage'] - history[i+1]['progress_percentage']) < 0.1:
                                stagnant_count += 1
                            else:
                                break
                        
                        if stagnant_count >= 3:
                            stall_indicators.append(f"Progress stagnant for {stagnant_count} consecutive snapshots")
                
                # Get current pending/analyzing tracks info
                cursor = conn.execute("""
                    SELECT analysis_status, COUNT(*) as count
                    FROM tracks 
                    GROUP BY analysis_status
                """)
                
                status_counts = dict(cursor.fetchall())
                pending_count = status_counts.get('pending', 0)
                analyzing_count = status_counts.get('analyzing', 0)
                
                # Determine stall probability using current context
                latest_processing_rate = history[0]['processing_rate'] if history else None
                is_currently_stalled = self._is_analysis_stalled()
                
                stall_probability = 'low'
                # High only if there are indicators, we have work pending, something is analyzing,
                # processing rate is low, and current stalled check agrees
                if stall_indicators and pending_count > 0:
                    if analyzing_count > 0 and (latest_processing_rate is None or latest_processing_rate < self.config.min_progress_threshold) and is_currently_stalled:
                        stall_probability = 'high'
                
                return {
                    'stall_indicators': stall_indicators,
                    'current_status': {
                        'pending_tracks': pending_count,
                        'analyzing_tracks': analyzing_count,
                        'total_tracks': sum(status_counts.values())
                    },
                    'recent_history': history,
                    'stall_probability': stall_probability,
                    'recommended_action': self._get_stall_recommendation(stall_indicators, pending_count),
                    'stall_factors': self._identify_stall_factors()
                }
                
        except Exception as e:
            logger.error(f"Error getting stall analysis: {e}")
            return {
                'stall_indicators': [],
                'current_status': {},
                'recent_history': [],
                'stall_probability': 'unknown',
                'recommended_action': 'Unable to determine stall status'
            }
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp string to datetime object."""
        try:
            if isinstance(timestamp_str, str):
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return timestamp_str
        except Exception:
            return datetime.now()
    
    def _get_stall_recommendation(self, stall_indicators: List[str], pending_count: int) -> str:
        """Get recommendation based on stall indicators."""
        if not stall_indicators:
            return "Analysis appears to be progressing normally"
        
        if pending_count == 0:
            return "No pending tracks - analysis may be complete"
        
        if "No progress" in ' '.join(stall_indicators):
            return "Analysis appears stalled. Consider restarting the analysis process."
        
        if "Progress stagnant" in ' '.join(stall_indicators):
            return "Progress is stagnant. Check for problematic audio files or system resources."
        
        return "Multiple stall indicators detected. Manual intervention recommended."
    
    def _identify_stall_factors(self) -> List[str]:
        """Identify specific factors contributing to stalls."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                factors = []
                
                # Check for files with multiple failures
                cursor = conn.execute("""
                    SELECT file_path, analysis_error, COUNT(*) as failure_count
                    FROM tracks 
                    WHERE analysis_status = 'error' 
                    GROUP BY file_path, analysis_error
                    HAVING failure_count >= 3
                    ORDER BY failure_count DESC
                    LIMIT 5
                """)
                
                problematic_files = cursor.fetchall()
                if problematic_files:
                    factors.append(f"Found {len(problematic_files)} files with 3+ failures")
                    for file_path, error_msg, count in problematic_files[:3]:
                        filename = os.path.basename(file_path) if file_path else "Unknown"
                        factors.append(f"  - {filename}: {count} failures ({error_msg[:50] if error_msg else 'No error message'}...)")
                
                # Check for files stuck in 'analyzing' status for too long
                cursor = conn.execute("""
                    SELECT file_path, 
                           (strftime('%s', 'now') - strftime('%s', created_at)) / 60.0 as minutes_stuck
                    FROM tracks 
                    WHERE analysis_status = 'analyzing' 
                    AND created_at IS NOT NULL
                    AND (strftime('%s', 'now') - strftime('%s', created_at)) > 300
                    ORDER BY minutes_stuck DESC
                    LIMIT 5
                """)
                
                stuck_files = cursor.fetchall()
                if stuck_files:
                    factors.append(f"Found {len(stuck_files)} files stuck in analysis for 5+ minutes")
                    for file_path, minutes in stuck_files[:3]:
                        filename = os.path.basename(file_path) if file_path else "Unknown"
                        factors.append(f"  - {filename}: stuck for {minutes:.1f} minutes")
                
                # Check for recent error patterns
                cursor = conn.execute("""
                    SELECT analysis_error, COUNT(*) as count
                    FROM tracks 
                    WHERE analysis_status = 'error' 
                    AND analysis_error IS NOT NULL
                    AND analysis_error != ''
                    AND (analysis_completed_at > datetime('now', '-1 hour') 
                         OR analysis_started_at > datetime('now', '-1 hour'))
                    GROUP BY analysis_error
                    ORDER BY count DESC
                    LIMIT 3
                """)
                
                error_patterns = cursor.fetchall()
                if error_patterns:
                    factors.append("Recent error patterns:")
                    for error_msg, count in error_patterns:
                        factors.append(f"  - {error_msg[:50]}...: {count} occurrences")
                
                return factors
                
        except Exception as e:
            logger.error(f"Error identifying stall factors: {e}")
            return ["Unable to analyze stall factors due to database error"]
    
    def get_problematic_files_report(self) -> Dict[str, Any]:
        """
        Get a detailed report of problematic files that may be causing stalls.
        
        Returns:
            Dictionary with problematic files information and recommendations
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                report = {
                    'summary': {},
                    'problematic_files': [],
                    'stuck_files': [],
                    'ignored_files': [],
                    'error_patterns': [],
                    'recommendations': []
                }
                
                # Get summary statistics
                cursor = conn.execute("""
                    SELECT analysis_status, COUNT(*) as count
                    FROM tracks 
                    GROUP BY analysis_status
                """)
                
                status_counts = dict(cursor.fetchall())
                report['summary'] = {
                    'total_tracks': sum(status_counts.values()),
                    'pending_tracks': status_counts.get('pending', 0),
                    'analyzing_tracks': status_counts.get('analyzing', 0),
                    'completed_tracks': status_counts.get('completed', 0),
                    'error_tracks': status_counts.get('error', 0),
                    'ignored_tracks': status_counts.get('ignored', 0)
                }
                
                # Get files with multiple failures
                cursor = conn.execute("""
                    SELECT file_path, analysis_error, COUNT(*) as failure_count,
                           MAX(created_at) as last_failure
                    FROM tracks 
                    WHERE analysis_status = 'error' 
                    GROUP BY file_path, analysis_error
                    HAVING failure_count >= 2
                    ORDER BY failure_count DESC, last_failure DESC
                    LIMIT 10
                """)
                
                for row in cursor.fetchall():
                    file_path, error_msg, count, last_failure = row
                    filename = os.path.basename(file_path) if file_path else "Unknown"
                    report['problematic_files'].append({
                        'filename': filename,
                        'file_path': file_path,
                        'failure_count': count,
                        'last_failure': last_failure,
                        'error_message': error_msg,
                        'recommendation': 'skip' if count >= 3 else 'retry'
                    })
                
                # Get files stuck in analysis
                cursor = conn.execute("""
                    SELECT file_path, created_at,
                           (strftime('%s', 'now') - strftime('%s', created_at)) / 60.0 as minutes_stuck
                    FROM tracks 
                    WHERE analysis_status = 'analyzing' 
                    AND created_at IS NOT NULL
                    AND (strftime('%s', 'now') - strftime('%s', created_at)) > 60
                    ORDER BY minutes_stuck DESC
                    LIMIT 10
                """)
                
                for row in cursor.fetchall():
                    file_path, created_at, minutes = row
                    filename = os.path.basename(file_path) if file_path else "Unknown"
                    report['stuck_files'].append({
                        'filename': filename,
                        'file_path': file_path,
                        'minutes_stuck': minutes,
                        'last_updated': created_at,
                        'recommendation': 'force_reset' if minutes > 300 else 'monitor'
                    })
                
                # Get ignored files (permanently skipped)
                cursor = conn.execute("""
                    SELECT file_path, analysis_error, created_at
                    FROM tracks 
                    WHERE analysis_status = 'ignored'
                    ORDER BY created_at DESC
                    LIMIT 10
                """)
                
                for row in cursor.fetchall():
                    file_path, error_msg, created_at = row
                    filename = os.path.basename(file_path) if file_path else "Unknown"
                    report['ignored_files'].append({
                        'filename': filename,
                        'file_path': file_path,
                        'ignored_at': created_at,
                        'reason': error_msg or 'Permanently ignored due to analysis failures',
                        'recommendation': 'permanently_ignored'
                    })
                
                # Get error patterns
                cursor = conn.execute("""
                    SELECT analysis_error, COUNT(*) as count,
                           MAX(created_at) as last_occurrence
                    FROM tracks 
                    WHERE analysis_status = 'error' 
                    AND created_at > datetime('now', '-24 hours')
                    GROUP BY analysis_error
                    ORDER BY count DESC
                    LIMIT 5
                """)
                
                for row in cursor.fetchall():
                    error_msg, count, last_occurrence = row
                    report['error_patterns'].append({
                        'error_message': error_msg,
                        'count': count,
                        'last_occurrence': last_occurrence,
                        'frequency': 'high' if count > 10 else 'medium' if count > 5 else 'low'
                    })
                
                # Generate recommendations
                if report['problematic_files']:
                    high_failure_files = [f for f in report['problematic_files'] if f['failure_count'] >= 3]
                    if high_failure_files:
                        report['recommendations'].append(f"Skip {len(high_failure_files)} files with 3+ failures to prevent stalls")
                
                if report['stuck_files']:
                    long_stuck_files = [f for f in report['stuck_files'] if f['minutes_stuck'] > 300]
                    if long_stuck_files:
                        report['recommendations'].append(f"Force reset {len(long_stuck_files)} files stuck for 5+ hours")
                
                if report['ignored_files']:
                    report['recommendations'].append(f"{len(report['ignored_files'])} files are permanently ignored due to corruption")
                
                if report['error_patterns']:
                    high_freq_errors = [e for e in report['error_patterns'] if e['frequency'] == 'high']
                    if high_freq_errors:
                        report['recommendations'].append(f"Investigate {len(high_freq_errors)} high-frequency error patterns")
                
                if not report['recommendations']:
                    report['recommendations'].append("No immediate action required - system appears healthy")
                
                return report
                
        except Exception as e:
            logger.error(f"Error generating problematic files report: {e}")
            return {
                'error': f"Failed to generate report: {str(e)}",
                'summary': {},
                'problematic_files': [],
                'stuck_files': [],
                'error_patterns': [],
                'recommendations': []
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status of the audio analysis system.
        
        Returns:
            Dictionary with health status information
        """
        try:
            # Capture current snapshot
            snapshot = self.capture_progress_snapshot()
            
            # Get recent history
            recent_history = self._get_recent_progress_history()
            
            # Determine overall health
            health_status = self._determine_health_status(snapshot)
            
            # Check for consecutive stalls
            consecutive_stalls = self._count_consecutive_stalls()
            
            # Detect anomalies
            anomalies = self._detect_anomalies(snapshot)
            
            health_info = {
                'current_status': health_status.value,
                'timestamp': snapshot.timestamp.isoformat(),
                'progress': {
                    'total_tracks': snapshot.total_tracks,
                    'analyzed_tracks': snapshot.analyzed_tracks,
                    'pending_tracks': snapshot.pending_tracks,
                    'error_tracks': snapshot.error_tracks,
                    'progress_percentage': snapshot.progress_percentage
                },
                'processing_rate': snapshot.processing_rate,
                'estimated_completion': snapshot.estimated_completion.isoformat() if snapshot.estimated_completion else None,
                'stalled': self._is_analysis_stalled(),
                'consecutive_stalls': consecutive_stalls,
                'anomalies': anomalies,
                'recommendations': self._generate_recommendations(health_status, consecutive_stalls, anomalies),
                'recent_history': recent_history
            }
            
            return health_info
            
        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            return {
                'current_status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_recent_progress_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent progress history for the specified number of hours."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT timestamp, analyzed_tracks, pending_tracks, progress_percentage, health_status
                    FROM analysis_progress_history 
                    WHERE timestamp > datetime('now', '-{} hours')
                    ORDER BY timestamp DESC
                """.format(hours))
                
                history = []
                for row in cursor.fetchall():
                    history.append({
                        'timestamp': row[0],
                        'analyzed_tracks': row[1],
                        'pending_tracks': row[2],
                        'progress_percentage': row[3],
                        'health_status': row[4]
                    })
                
                return history
                
        except Exception as e:
            logger.error(f"Error getting recent progress history: {e}")
            return []
    
    def _count_consecutive_stalls(self) -> int:
        """Count consecutive stalls in recent history."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT health_status 
                    FROM analysis_progress_history 
                    ORDER BY timestamp DESC 
                    LIMIT 10
                """)
                
                consecutive_count = 0
                for row in cursor.fetchall():
                    if row[0] == 'stalled':
                        consecutive_count += 1
                    else:
                        break
                
                return consecutive_count
                
        except Exception as e:
            logger.error(f"Error counting consecutive stalls: {e}")
            return 0
    
    def _generate_recommendations(self, health_status: HealthStatus, 
                                 consecutive_stalls: int, anomalies: List[str] = None) -> List[str]:
        """Generate recommendations based on current health status and anomalies."""
        recommendations = []
        
        if health_status == HealthStatus.STALLED:
            if consecutive_stalls >= self.config.max_consecutive_stalls:
                recommendations.append("Analysis has stalled multiple times. Consider manual intervention.")
            else:
                recommendations.append("Analysis appears stalled. Auto-recovery will be attempted.")
        
        elif health_status == HealthStatus.ERROR:
            recommendations.append("High error rate detected. Check system logs and audio files.")
        
        elif health_status == HealthStatus.WARNING:
            recommendations.append("Processing rate is below optimal. Monitor for further degradation.")
        
        elif health_status == HealthStatus.HEALTHY:
            recommendations.append("Analysis is progressing normally.")
        
        # Add anomaly-specific recommendations
        if anomalies:
            for anomaly in anomalies:
                if "Progress dropped" in anomaly:
                    recommendations.append("Progress regression detected. Check for database issues or file corruption.")
                elif "Processing rate" in anomaly:
                    recommendations.append("Low processing rate detected. Consider reducing batch size or checking system resources.")
                elif "High error rate" in anomaly:
                    recommendations.append("High error rate detected. Review failed tracks and check audio file integrity.")
                elif "Progress has been stagnant" in anomaly:
                    recommendations.append("Progress stagnation detected. Analysis may be stuck on problematic files.")
        
        return recommendations
    
    def cleanup_old_history(self, days: int = None) -> int:
        """
        Clean up old progress history to save space.
        
        Args:
            days: Remove data older than this many days (uses config default if None)
            
        Returns:
            Number of records removed
        """
        if days is None:
            days = self.config.progress_history_retention_days
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM analysis_progress_history 
                    WHERE timestamp < datetime('now', '-{} days')
                """.format(days))
                
                removed_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleaned up {removed_count} old progress history records")
                return removed_count
                
        except Exception as e:
            logger.error(f"Error cleaning up old history: {e}")
            return 0


def main():
    """Test function for the AudioAnalysisMonitor"""
    print("🎵 TuneForge Audio Analysis Monitor Test")
    print("=" * 50)
    
    try:
        # Initialize monitor
        monitor = AudioAnalysisMonitor()
        print("✅ AudioAnalysisMonitor initialized successfully")
        
        # Test health status
        print("\n🔍 Testing health status...")
        health = monitor.get_health_status()
        
        print(f"📊 Current Health Status:")
        print(f"   - Status: {health['current_status']}")
        print(f"   - Progress: {health['progress']['progress_percentage']}%")
        print(f"   - Stalled: {health['stalled']}")
        print(f"   - Consecutive Stalls: {health['consecutive_stalls']}")
        
        if health['recommendations']:
            print(f"   - Recommendations:")
            for rec in health['recommendations']:
                print(f"     • {rec}")
        
        # Test progress snapshot
        print(f"\n📸 Testing progress snapshot...")
        snapshot = monitor.capture_progress_snapshot()
        print(f"   - Snapshot captured at: {snapshot.timestamp}")
        print(f"   - Progress: {snapshot.progress_percentage}%")
        print(f"   - Processing Rate: {snapshot.processing_rate or 'N/A'} tracks/min")
        
        # Test problematic files report
        print(f"\n📊 Testing problematic files report...")
        report = monitor.get_problematic_files_report()
        print(f"   - Summary: {report['summary']}")
        if report['problematic_files']:
            print(f"   - Problematic Files:")
            for pf in report['problematic_files']:
                print(f"     • {pf['filename']} (Path: {pf['file_path']}) - {pf['failure_count']} failures, last at {pf['last_failure']}")
        if report['stuck_files']:
            print(f"   - Stuck Files:")
            for sf in report['stuck_files']:
                print(f"     • {sf['filename']} (Path: {sf['file_path']}) - stuck for {sf['minutes_stuck']:.1f} minutes")
        if report['error_patterns']:
            print(f"   - Error Patterns:")
            for ep in report['error_patterns']:
                print(f"     • {ep['error_message'][:50]}... ({ep['count']} occurrences)")
        if report['recommendations']:
            print(f"   - Recommendations:")
            for rec in report['recommendations']:
                print(f"     • {rec}")
        
        # Test cleanup
        print(f"\n🧹 Testing cleanup...")
        removed = monitor.cleanup_old_history(days=30)
        print(f"   - Removed {removed} old records")
        
        print(f"\n🚀 Audio Analysis Monitor is ready for Phase 1, Task 1.1!")
        print("📊 Ready to detect stalled analysis and provide health monitoring")
        
    except Exception as e:
        print(f"❌ Monitor test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
