#!/usr/bin/env python3
"""
Integrated Audio Processor for TuneForge

This module combines the AudioAnalyzer with the AudioAnalysisService
to provide a complete audio processing pipeline that extracts features
and stores them in the database.
"""

import os
import time
import logging
import sqlite3
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# Import our modules
from audio_analyzer import AudioAnalyzer
from audio_analysis_service import AudioAnalysisService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegratedAudioProcessor:
    """
    Integrated audio processor that combines feature extraction with database storage.
    
    This class provides:
    - Audio feature extraction using AudioAnalyzer
    - Database storage using AudioAnalysisService
    - Batch processing capabilities
    - Progress tracking and error handling
    """
    
    def __init__(self, db_path: str = None, sample_rate: int = 8000, 
                 max_duration: int = 60, hop_length: int = 512):
        """
        Initialize the IntegratedAudioProcessor.
        
        Args:
            db_path: Path to the database
            sample_rate: Sample rate for audio analysis
            max_duration: Maximum duration to analyze per file
            hop_length: Hop length for analysis
        """
        self.analyzer = AudioAnalyzer(sample_rate=sample_rate, max_duration=max_duration, hop_length=hop_length)
        self.service = AudioAnalysisService(db_path)
        self.analysis_version = "1.0"
        
        logger.info(f"IntegratedAudioProcessor initialized with sample rate: {sample_rate} Hz")
    
    def process_single_track(self, track_id: int, file_path: str) -> Dict[str, Any]:
        """
        Process a single track: extract features and store in database.
        
        Args:
            track_id: Database ID of the track
            file_path: Path to the audio file
            
        Returns:
            Dictionary with processing results
        """
        result = {
            'track_id': track_id,
            'file_path': file_path,
            'success': False,
            'features': None,
            'processing_time': 0,
            'error_message': ''
        }
        
        try:
            # Update status to analyzing
            self.service.update_analysis_status(track_id, 'analyzing')
            
            # Start timing
            start_time = time.time()
            
            # Extract features
            logger.info(f"Processing track {track_id}: {Path(file_path).name}")
            features_result = self.analyzer.extract_all_features(file_path)
            
            if not features_result['success']:
                error_msg = f"Feature extraction failed: {features_result['error_message']}"
                self.service.update_analysis_status(track_id, 'error', error_msg)
                result['error_message'] = error_msg
                return result
            
            # Get extracted features
            extracted_features = features_result['features']
            
            # Add analysis metadata
            extracted_features['analysis_version'] = self.analysis_version
            
            # Store features in database
            if self.service.store_audio_features(track_id, extracted_features):
                result['success'] = True
                result['features'] = extracted_features
                result['processing_time'] = time.time() - start_time
                
                logger.info(f"Successfully processed track {track_id} in {result['processing_time']:.2f}s")
            else:
                error_msg = "Failed to store features in database"
                self.service.update_analysis_status(track_id, 'error', error_msg)
                result['error_message'] = error_msg
                logger.error(f"Database storage failed for track {track_id}")
            
        except Exception as e:
            error_msg = f"Processing error: {str(e)}"
            self.service.update_analysis_status(track_id, 'error', error_msg)
            result['error_message'] = error_msg
            logger.error(f"Error processing track {track_id}: {e}")
        
        return result
    
    def process_tracks_batch(self, tracks: List[Dict[str, Any]], 
                           max_workers: int = 1, progress_callback=None) -> Dict[str, Any]:
        """
        Process multiple tracks in batch.
        
        Args:
            tracks: List of track dictionaries with 'id' and 'file_path'
            max_workers: Maximum concurrent workers (currently 1 for simplicity)
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dictionary with batch processing results
        """
        batch_result = {
            'total_tracks': len(tracks),
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'total_time': 0,
            'results': [],
            'errors': []
        }
        
        start_time = time.time()
        
        logger.info(f"Starting batch processing of {len(tracks)} tracks")
        
        for i, track in enumerate(tracks):
            try:
                # Process track
                result = self.process_single_track(track['id'], track['file_path'])
                batch_result['results'].append(result)
                
                if result['success']:
                    batch_result['successful'] += 1
                else:
                    batch_result['failed'] += 1
                    batch_result['errors'].append({
                        'track_id': track['id'],
                        'error': result['error_message']
                    })
                
                batch_result['processed'] += 1
                
                # Update progress
                if progress_callback:
                    progress = (i + 1) / len(tracks) * 100
                    progress_callback(progress, i + 1, len(tracks))
                
                # Log progress
                if (i + 1) % 10 == 0 or (i + 1) == len(tracks):
                    logger.info(f"Progress: {i + 1}/{len(tracks)} tracks processed "
                              f"({batch_result['successful']} successful, {batch_result['failed']} failed)")
                
            except Exception as e:
                error_msg = f"Batch processing error for track {track['id']}: {str(e)}"
                logger.error(error_msg)
                batch_result['failed'] += 1
                batch_result['errors'].append({
                    'track_id': track['id'],
                    'error': error_msg
                })
                batch_result['processed'] += 1
        
        batch_result['total_time'] = time.time() - start_time
        
        logger.info(f"Batch processing completed: {batch_result['successful']} successful, "
                   f"{batch_result['failed']} failed in {batch_result['total_time']:.2f}s")
        
        return batch_result
    
    def process_pending_tracks(self, limit: int = 50, progress_callback=None) -> Dict[str, Any]:
        """
        Process all pending tracks from the database.
        
        Args:
            limit: Maximum number of tracks to process
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with processing results
        """
        # Get pending tracks
        tracks = self.service.get_tracks_for_analysis(limit=limit)
        
        if not tracks:
            logger.info("No pending tracks found for analysis")
            return {
                'total_tracks': 0,
                'processed': 0,
                'successful': 0,
                'failed': 0,
                'total_time': 0,
                'results': [],
                'errors': []
            }
        
        logger.info(f"Found {len(tracks)} pending tracks to process")
        
        # Process the batch
        return self.process_tracks_batch(tracks, progress_callback=progress_callback)
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive summary of analysis status and progress.
        
        Returns:
            Dictionary with analysis summary
        """
        progress = self.service.get_analysis_progress()
        
        # Get sample of analyzed tracks
        try:
            with sqlite3.connect(self.service.db_path) as conn:
                cursor = conn.execute("""
                    SELECT t.id, t.title, af.tempo, af.key, af.mode, af.energy, af.danceability
                    FROM tracks t
                    JOIN audio_features af ON t.id = af.track_id
                    WHERE t.analysis_status = 'analyzed'
                    ORDER BY af.created_at DESC
                    LIMIT 5
                """)
                
                recent_analyzed = []
                for row in cursor.fetchall():
                    recent_analyzed.append({
                        'id': row[0],
                        'title': row[1],
                        'tempo': row[2],
                        'key': row[3],
                        'mode': row[4],
                        'energy': row[5],
                        'danceability': row[6]
                    })
        except Exception as e:
            logger.warning(f"Could not fetch recent analyzed tracks: {e}")
            recent_analyzed = []
        
        summary = {
            'progress': progress,
            'recent_analyzed': recent_analyzed,
            'analyzer_info': {
                'sample_rate': self.analyzer.sample_rate,
                'max_duration': self.analyzer.max_duration,
                'hop_length': self.analyzer.hop_length,
                'analysis_version': self.analysis_version
            }
        }
        
        return summary


def main():
    """Test function for the IntegratedAudioProcessor"""
    print("🎵 TuneForge Integrated Audio Processor Test")
    print("=" * 60)
    
    try:
        # Initialize processor
        processor = IntegratedAudioProcessor()
        print("✅ IntegratedAudioProcessor initialized successfully")
        
        # Get analysis summary
        print("\n📊 Analysis Summary:")
        summary = processor.get_analysis_summary()
        progress = summary['progress']
        
        print(f"   - Total tracks: {progress['total_tracks']}")
        print(f"   - Analyzed: {progress['analyzed_tracks']}")
        print(f"   - Pending: {progress['pending_tracks']}")
        print(f"   - Progress: {progress['progress_percentage']}%")
        
        # Test with a small batch
        print(f"\n🧪 Testing batch processing...")
        tracks = processor.service.get_tracks_for_analysis(limit=3)
        
        if tracks:
            print(f"   Processing {len(tracks)} sample tracks...")
            
            def progress_callback(percent, current, total):
                print(f"   Progress: {percent:.1f}% ({current}/{total})")
            
            # Process the batch
            result = processor.process_tracks_batch(tracks, progress_callback=progress_callback)
            
            print(f"\n📊 Batch Processing Results:")
            print(f"   - Total: {result['total_tracks']}")
            print(f"   - Successful: {result['successful']}")
            print(f"   - Failed: {result['failed']}")
            print(f"   - Total time: {result['total_time']:.2f}s")
            
            if result['errors']:
                print(f"   - Errors: {len(result['errors'])}")
                for error in result['errors'][:3]:  # Show first 3 errors
                    print(f"     Track {error['track_id']}: {error['error']}")
            
            # Show updated summary
            print(f"\n📊 Updated Analysis Summary:")
            updated_summary = processor.get_analysis_summary()
            updated_progress = updated_summary['progress']
            print(f"   - Analyzed: {updated_progress['analyzed_tracks']}")
            print(f"   - Progress: {updated_progress['progress_percentage']}%")
            
        else:
            print("   No tracks available for testing")
        
        print(f"\n🚀 Integrated Audio Processor is ready for production!")
        print("📊 Ready to process your entire music library")
        
    except Exception as e:
        print(f"❌ Processor test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
