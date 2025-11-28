#!/usr/bin/env python3
"""
Advanced Batch Processor for TuneForge

This module provides sophisticated batch processing capabilities for audio analysis:
- Queue management with priority and retry logic
- Concurrent processing with configurable workers
- Progress persistence and resume capability
- Resource management and monitoring
- Comprehensive error handling and recovery
"""

import os
import time
import asyncio
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import sqlite3

# Import our modules
from audio_analyzer import AudioAnalyzer
from audio_analysis_service import AudioAnalysisService
# Monitoring will be imported dynamically in _progress_monitor to avoid circular imports

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProcessingStatus(Enum):
    """Processing status enumeration"""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    SKIPPED = "skipped" # Added SKIPPED status

@dataclass
class ProcessingJob:
    """Represents a single processing job"""
    track_id: int
    file_path: str
    priority: int = 3  # 1=high, 5=low
    status: ProcessingStatus = ProcessingStatus.PENDING
    attempts: int = 0
    max_attempts: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    worker_id: Optional[str] = None

@dataclass
class ProcessingStats:
    """Processing statistics and metrics"""
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    retrying_jobs: int = 0
    processing_jobs: int = 0
    start_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    average_processing_time: float = 0.0
    success_rate: float = 0.0
    skipped_jobs: int = 0 # Added skipped_jobs to stats

class AdvancedBatchProcessor:
    """
    Advanced batch processor with queue management and concurrent processing.
    
    Features:
    - Configurable worker pool
    - Priority-based job scheduling
    - Automatic retry with exponential backoff
    - Progress persistence and resume capability
    - Resource monitoring and management
    - Comprehensive error handling
    """
    
    def __init__(self, db_path: str = None, max_workers: int = 1, 
                 batch_size: int = 100, checkpoint_interval: int = 50):
        """
        Initialize the AdvancedBatchProcessor.
        
        Args:
            db_path: Path to the database
            max_workers: Maximum concurrent workers (default 1 for SQLite compatibility)
            batch_size: Number of jobs to process in each batch
            checkpoint_interval: Save progress every N jobs
        """
        self.db_path = db_path
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.checkpoint_interval = checkpoint_interval
        
        # Initialize components
        self.analyzer = AudioAnalyzer(sample_rate=8000, max_duration=60, hop_length=512)
        self.service = AudioAnalysisService(db_path)
        
        # Processing state
        self.jobs_queue: List[ProcessingJob] = []
        self.active_jobs: Dict[str, ProcessingJob] = {}
        self.completed_jobs: List[ProcessingJob] = []
        self.failed_jobs: List[ProcessingJob] = []
        self.skipped_jobs: List[ProcessingJob] = [] # Added skipped_jobs list
        
        # Statistics and monitoring
        self.stats = ProcessingStats()
        self.processing_lock = threading.Lock()
        self.shutdown_event = threading.Event()
        
        # Worker management
        self.workers: List[threading.Thread] = []
        self.worker_semaphore = threading.Semaphore(max_workers)
        
        # Checkpoint and resume
        self.last_checkpoint = 0
        self.checkpoint_file = "temp/audio_analysis_checkpoint.json"
        
        logger.info(f"AdvancedBatchProcessor initialized with {max_workers} workers, "
                   f"batch size {batch_size}, checkpoint interval {checkpoint_interval}")
    
    def initialize_queue(self, limit: int = None) -> int:
        """
        Initialize the processing queue with pending tracks.
        
        Args:
            limit: Maximum number of tracks to queue (None for all)
            
        Returns:
            Number of jobs added to queue
        """
        try:
            # Get tracks from database
            tracks = self.service.get_tracks_for_analysis(limit=limit or 10000)
            
            with self.processing_lock:
                # Clear existing queue
                self.jobs_queue.clear()
                
                # Create processing jobs
                for track in tracks:
                    job = ProcessingJob(
                        track_id=track['id'],
                        file_path=track['file_path'],
                        priority=1 if track['analysis_status'] == 'error' else 3,
                        status=ProcessingStatus.QUEUED
                    )
                    self.jobs_queue.append(job)
                
                # Sort by priority (errors first, then by ID)
                self.jobs_queue.sort(key=lambda j: (j.priority, j.track_id))
                
                self.stats.total_jobs = len(self.jobs_queue)
                self.stats.start_time = datetime.now()
                
                logger.info(f"Initialized queue with {len(self.jobs_queue)} jobs")
                return len(self.jobs_queue)
                
        except Exception as e:
            logger.error(f"Error initializing queue: {e}")
            return 0
    
    def start_processing(self, progress_callback: Callable = None) -> bool:
        """
        Start the batch processing with multiple workers.
        
        Args:
            progress_callback: Optional callback for progress updates
            
        Returns:
            True if processing started successfully
        """
        try:
            if not self.jobs_queue:
                logger.warning("No jobs in queue to process")
                return False
            
            if self.workers:
                logger.warning("Processing already in progress")
                return False
            
            logger.info(f"Starting batch processing with {self.max_workers} workers")
            
            # Start worker threads
            for i in range(self.max_workers):
                worker = threading.Thread(
                    target=self._worker_loop,
                    args=(f"worker-{i}", progress_callback),
                    daemon=True
                )
                worker.start()
                self.workers.append(worker)
            
            # Start progress monitoring thread
            monitor_thread = threading.Thread(
                target=self._progress_monitor,
                args=(progress_callback,),
                daemon=True
            )
            monitor_thread.start()
            
            # Capture initial progress snapshot for monitoring
            self._capture_monitoring_snapshot()
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting processing: {e}")
            return False
    
    def stop_processing(self) -> bool:
        """
        Stop the batch processing gracefully.
        
        Returns:
            True if processing stopped successfully
        """
        try:
            logger.info("Stopping batch processing...")
            
            # Signal shutdown
            self.shutdown_event.set()
            
            # Wait for workers to finish
            for worker in self.workers:
                worker.join(timeout=10)
            
            # Clear workers list
            self.workers.clear()
            
            # Save final checkpoint
            self._save_checkpoint()
            
            # Capture final progress snapshot for monitoring
            self._capture_monitoring_snapshot()
            
            logger.info("Batch processing stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping processing: {e}")
            return False
    
    def _worker_loop(self, worker_id: str, progress_callback: Callable = None):
        """Main worker loop for processing jobs"""
        logger.info(f"Worker {worker_id} started")
        
        while not self.shutdown_event.is_set():
            try:
                # Get next job from queue
                job = self._get_next_job()
                if not job:
                    time.sleep(1)  # Wait for jobs
                    continue
                
                # Process the job
                self._process_job(job, worker_id, progress_callback)
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                time.sleep(1)
        
        logger.info(f"Worker {worker_id} stopped")
    
    def _get_next_job(self) -> Optional[ProcessingJob]:
        """Get the next job from the queue with proper locking"""
        with self.processing_lock:
            if not self.jobs_queue:
                return None
            
            # Get highest priority job
            job = self.jobs_queue.pop(0)
            job.status = ProcessingStatus.PROCESSING
            job.started_at = datetime.now()
            job.worker_id = threading.current_thread().name
            
            self.active_jobs[job.worker_id] = job
            return job
    
    def _process_job(self, job: ProcessingJob, worker_id: str, progress_callback: Callable = None):
        """Process a single job"""
        try:
            logger.info(f"Processing job {job.track_id} (attempt {job.attempts + 1})")
            
            # Update database status
            self.service.update_analysis_status(job.track_id, 'analyzing')
            
            # Start timing
            start_time = time.time()
            
            # Extract features
            features_result = self.analyzer.extract_all_features(job.file_path)
            
            if not features_result['success']:
                raise Exception(f"Feature extraction failed: {features_result['error_message']}")
            
            # Store features in database
            extracted_features = features_result['features']
            extracted_features['analysis_version'] = "1.0"
            
            if not self.service.store_audio_features(job.track_id, extracted_features):
                raise Exception("Failed to store features in database")
            
            # Job completed successfully
            job.status = ProcessingStatus.COMPLETED
            job.completed_at = datetime.now()
            job.processing_time = time.time() - start_time
            
            # Update statistics
            with self.processing_lock:
                self.completed_jobs.append(job)
                self.stats.completed_jobs += 1
                self._update_stats()
            
            # Capture progress snapshot for monitoring
            self._capture_monitoring_snapshot()
            
            logger.info(f"Job {job.track_id} completed successfully in {job.processing_time:.2f}s")
            
        except Exception as e:
            # Job failed
            error_msg = str(e)
            job.error_message = error_msg
            job.attempts += 1
            
            # Check if this file should be permanently skipped
            if self._should_skip_file_permanently(job):
                job.status = ProcessingStatus.SKIPPED
                job.completed_at = datetime.now()
                
                # Update database status to 'skipped' with reason
                self.service.update_analysis_status(job.track_id, 'skipped', f"Permanently skipped after {job.attempts} failures: {error_msg}")
                
                with self.processing_lock:
                    self.skipped_jobs.append(job)
                    self.stats.skipped_jobs += 1
                    self._update_stats()
                
                logger.warning(f"Job {job.track_id} permanently skipped after {job.attempts} failures: {error_msg}")
                
            elif job.attempts < job.max_attempts:
                # Retry with exponential backoff
                job.status = ProcessingStatus.RETRYING
                delay = min(300, 2 ** job.attempts)  # Max 5 minutes
                
                logger.warning(f"Job {job.track_id} failed (attempt {job.attempts}), "
                             f"retrying in {delay}s: {error_msg}")
                
                # Schedule retry
                threading.Timer(delay, self._retry_job, args=[job]).start()
                
                with self.processing_lock:
                    self.stats.retrying_jobs += 1
                    self._update_stats()
                
            else:
                # Max attempts reached
                job.status = ProcessingStatus.FAILED
                job.completed_at = datetime.now()
                
                # Update database status
                self.service.update_analysis_status(job.track_id, 'error', error_msg)
                
                with self.processing_lock:
                    self.failed_jobs.append(job)
                    self.stats.failed_jobs += 1
                    self._update_stats()
                
                # Capture progress snapshot for monitoring
                self._capture_monitoring_snapshot()
                
                logger.error(f"Job {job.track_id} failed permanently after {job.attempts} attempts: {error_msg}")
        
        finally:
            # Clean up active job
            with self.processing_lock:
                if worker_id in self.active_jobs:
                    del self.active_jobs[worker_id]
    
    def _retry_job(self, job: ProcessingJob):
        """Retry a failed job"""
        with self.processing_lock:
            if job.status == ProcessingStatus.RETRYING:
                job.status = ProcessingStatus.QUEUED
                self.jobs_queue.append(job)
                self.stats.retrying_jobs -= 1
                logger.info(f"Job {job.track_id} queued for retry")
    
    def _progress_monitor(self, progress_callback: Callable = None):
        """Monitor processing progress and save checkpoints"""
        # Initialize monitoring if available
        monitor = None
        try:
            from audio_analysis_monitor import AudioAnalysisMonitor
            monitor = AudioAnalysisMonitor(self.db_path)
            logger.info("Audio analysis monitoring enabled")
        except ImportError as e:
            logger.warning(f"Audio analysis monitoring not available: {e}")
        except Exception as e:
            logger.warning(f"Failed to initialize monitoring: {e}")
        
        last_monitoring_update = 0
        monitoring_interval = 60  # Update monitoring every 60 seconds
        
        while not self.shutdown_event.is_set():
            try:
                # Update statistics
                with self.processing_lock:
                    self._update_stats()
                
                # Call progress callback if provided
                if progress_callback:
                    progress = self._calculate_progress()
                    progress_callback(progress)
                
                # Capture progress snapshot for monitoring (every 60 seconds)
                current_time = time.time()
                if monitor and (current_time - last_monitoring_update) >= monitoring_interval:
                    try:
                        monitor.capture_progress_snapshot()
                        last_monitoring_update = current_time
                        logger.debug("Progress snapshot captured for monitoring")
                    except Exception as e:
                        logger.warning(f"Failed to capture progress snapshot: {e}")
                
                # Save checkpoint if needed
                if self.stats.completed_jobs - self.last_checkpoint >= self.checkpoint_interval:
                    self._save_checkpoint()
                
                time.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                logger.error(f"Progress monitor error: {e}")
                time.sleep(5)
    
    def _update_stats(self):
        """Update processing statistics"""
        total_processed = self.stats.completed_jobs + self.stats.failed_jobs + self.stats.skipped_jobs
        
        if total_processed > 0:
            # Calculate average processing time
            if self.stats.completed_jobs > 0:
                total_time = sum(job.processing_time for job in self.completed_jobs)
                self.stats.average_processing_time = total_time / len(self.completed_jobs)
            else:
                self.stats.average_processing_time = 0.0
            
            # Calculate success rate
            self.stats.success_rate = (self.stats.completed_jobs / total_processed) * 100
            
            # Estimate completion time
            if self.stats.average_processing_time > 0:
                remaining_jobs = self.stats.total_jobs - total_processed
                estimated_seconds = (remaining_jobs * self.stats.average_processing_time) / self.max_workers
                self.stats.estimated_completion = datetime.now() + timedelta(seconds=estimated_seconds)
    
    def _calculate_progress(self) -> Dict[str, Any]:
        """Calculate current processing progress"""
        total_processed = self.stats.completed_jobs + self.stats.failed_jobs + self.stats.skipped_jobs
        
        return {
            'total_jobs': self.stats.total_jobs,
            'completed_jobs': self.stats.completed_jobs,
            'failed_jobs': self.stats.failed_jobs,
            'retrying_jobs': self.stats.retrying_jobs,
            'processing_jobs': len(self.active_jobs),
            'progress_percentage': round((total_processed / self.stats.total_jobs * 100) if self.stats.total_jobs > 0 else 0, 1),
            'success_rate': round(self.stats.success_rate, 1),
            'average_processing_time': round(self.stats.average_processing_time, 2),
            'estimated_completion': self.stats.estimated_completion.isoformat() if self.stats.estimated_completion else None,
            'active_workers': len(self.workers),
            'queue_size': len(self.jobs_queue),
            'skipped_jobs': self.stats.skipped_jobs # Added skipped_jobs to progress
        }
    
    def _save_checkpoint(self):
        """Save processing checkpoint for resume capability"""
        try:
            checkpoint_data = {
                'timestamp': datetime.now().isoformat(),
                'stats': {
                    'total_jobs': self.stats.total_jobs,
                    'completed_jobs': self.stats.completed_jobs,
                    'failed_jobs': self.stats.failed_jobs,
                    'start_time': self.stats.start_time.isoformat() if self.stats.start_time else None
                },
                'last_checkpoint': self.stats.completed_jobs
            }
            
            # Ensure temp directory exists
            checkpoint_path = Path(self.checkpoint_file)
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save to file (could be enhanced to use database)
            import json
            with open(self.checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)
            
            self.last_checkpoint = self.stats.completed_jobs
            logger.info(f"Checkpoint saved: {self.stats.completed_jobs}/{self.stats.total_jobs} jobs completed")
            
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
    
    def _capture_monitoring_snapshot(self):
        """Capture progress snapshot for monitoring system"""
        try:
            from audio_analysis_monitor import AudioAnalysisMonitor
            monitor = AudioAnalysisMonitor(self.db_path)
            monitor.capture_progress_snapshot()
            logger.debug("Monitoring snapshot captured after job completion")
        except Exception as e:
            logger.debug(f"Failed to capture monitoring snapshot: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current processing status"""
        with self.processing_lock:
            progress = self._calculate_progress()
            
            return {
                'status': 'running' if self.workers else 'stopped',
                'progress': progress,
                'workers': len(self.workers),
                'active_jobs': len(self.active_jobs),
                'queue_size': len(self.jobs_queue),
                'shutdown_requested': self.shutdown_event.is_set()
            }

    def _should_skip_file_permanently(self, job: ProcessingJob) -> bool:
        """
        Determine if a file should be permanently skipped based on failure patterns.
        
        Args:
            job: The job that just failed
            
        Returns:
            True if the file should be permanently skipped
        """
        # Skip files with 3+ failures
        if job.attempts >= 3:
            return True
        
        # Skip files with specific error patterns that indicate corruption
        error_msg = job.error_message.lower()
        skip_patterns = [
            'file not found',
            'permission denied',
            'corrupted',
            'invalid format',
            'unsupported format',
            'file is empty',
            'access denied'
        ]
        
        if any(pattern in error_msg for pattern in skip_patterns):
            logger.info(f"File {job.track_id} matches skip pattern, marking as permanently skipped")
            return True
        
        return False


def main():
    """Test function for the AdvancedBatchProcessor"""
    print("🎵 TuneForge Advanced Batch Processor Test")
    print("=" * 60)
    
    try:
        # Initialize processor
        processor = AdvancedBatchProcessor(max_workers=2, batch_size=10, checkpoint_interval=5)
        print("✅ AdvancedBatchProcessor initialized successfully")
        
        # Initialize queue with a small batch for testing
        print("\n🔍 Initializing processing queue...")
        jobs_added = processor.initialize_queue(limit=10)
        print(f"📁 Added {jobs_added} jobs to queue")
        
        if jobs_added == 0:
            print("❌ No jobs available for testing")
            return
        
        # Progress callback
        def progress_callback(progress):
            print(f"\r📊 Progress: {progress['progress_percentage']}% "
                  f"({progress['completed_jobs']}/{progress['total_jobs']}) "
                  f"Success: {progress['success_rate']}% "
                  f"ETA: {progress['estimated_completion'] or 'Calculating...'}", end='')
        
        # Start processing
        print(f"\n🚀 Starting batch processing with {processor.max_workers} workers...")
        if processor.start_processing(progress_callback=progress_callback):
            print("\n✅ Processing started successfully")
            
            # Wait for completion
            while processor.get_status()['status'] == 'running':
                time.sleep(2)
            
            # Get final status
            final_status = processor.get_status()
            print(f"\n\n📊 Final Processing Results:")
            print(f"   - Status: {final_status['status']}")
            print(f"   - Completed: {final_status['progress']['completed_jobs']}")
            print(f"   - Failed: {final_status['progress']['failed_jobs']}")
            print(f"   - Success Rate: {final_status['progress']['success_rate']}%")
            print(f"   - Average Time: {final_status['progress']['average_processing_time']}s")
            
        else:
            print("❌ Failed to start processing")
        
        print(f"\n🚀 Advanced Batch Processor is ready for production!")
        print("📊 Ready to process your entire music library efficiently")
        
    except Exception as e:
        print(f"❌ Processor test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
