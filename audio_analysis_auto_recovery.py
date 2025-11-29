#!/usr/bin/env python3
"""
Audio Analysis Auto-Recovery System for TuneForge

This module provides automatic recovery capabilities for stalled audio analysis:
- Automatic restart when stalled analysis is detected
- Exponential backoff for repeated failures
- Graceful shutdown and restart of analysis processes
- Integration with monitoring system
"""

import os
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

# Import our monitoring system
from audio_analysis_monitor import AudioAnalysisMonitor, MonitoringConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecoveryStatus(Enum):
    """Recovery status enumeration"""
    IDLE = "idle"
    MONITORING = "monitoring"
    RECOVERING = "recovering"
    FAILED = "failed"
    DISABLED = "disabled"

@dataclass
class RecoveryAttempt:
    """Represents a recovery attempt"""
    timestamp: datetime
    reason: str
    success: bool
    error_message: Optional[str] = None
    recovery_time: Optional[float] = None

@dataclass
class AutoRecoveryConfig:
    """Configuration for the auto-recovery system"""
    enabled: bool = True
    check_interval: int = 60  # Check every 60 seconds
    max_consecutive_failures: int = 3  # Max consecutive failures before escalating
    base_backoff_minutes: int = 5  # Base backoff time in minutes
    max_backoff_minutes: int = 60  # Maximum backoff time in minutes
    recovery_timeout_minutes: int = 10  # Timeout for recovery attempts
    require_manual_intervention_after: int = 5  # Require manual intervention after N failures

class AudioAnalysisAutoRecovery:
    """
    Automatic recovery system for stalled audio analysis.
    
    Features:
    - Continuous monitoring for stalled analysis
    - Automatic restart with exponential backoff
    - Graceful process management
    - Failure tracking and escalation
    """
    
    def __init__(self, config: AutoRecoveryConfig = None, 
                 monitor: AudioAnalysisMonitor = None,
                 restart_callback: Callable = None):
        """
        Initialize the AutoRecovery system.
        
        Args:
            config: Auto-recovery configuration
            monitor: Audio analysis monitor instance
            restart_callback: Callback function to restart analysis
        """
        self.config = config or AutoRecoveryConfig()
        # Use passed monitor or create one lazily
        self._monitor = monitor
        self.restart_callback = restart_callback
        
        # Recovery state
        self.status = RecoveryStatus.IDLE
        self.monitoring_thread = None
        self.shutdown_event = threading.Event()
        
        # Recovery tracking
        self.recovery_attempts: List[RecoveryAttempt] = []
        self.consecutive_failures = 0
        self.last_recovery_attempt = None
        self.backoff_multiplier = 1
        
        # Lock for thread safety
        self.recovery_lock = threading.Lock()
        
        logger.info(f"AudioAnalysisAutoRecovery initialized with config: enabled={self.config.enabled}")
        logger.info(f"Check interval: {self.config.check_interval}s, Max failures: {self.config.max_consecutive_failures}")
    
    @property
    def monitor(self) -> AudioAnalysisMonitor:
        """Lazily get or create the monitor instance"""
        if self._monitor is None:
            self._monitor = AudioAnalysisMonitor()
        return self._monitor
    
    def start_monitoring(self) -> bool:
        """
        Start the auto-recovery monitoring.
        
        Returns:
            True if monitoring started successfully
        """
        if not self.config.enabled:
            logger.info("Auto-recovery is disabled")
            self.status = RecoveryStatus.DISABLED
            return False
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            logger.warning("Monitoring is already running")
            return False
        
        try:
            self.shutdown_event.clear()
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="AutoRecovery-Monitor"
            )
            self.monitoring_thread.start()
            
            self.status = RecoveryStatus.MONITORING
            logger.info("Auto-recovery monitoring started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            self.status = RecoveryStatus.FAILED
            return False
    
    def stop_monitoring(self) -> bool:
        """
        Stop the auto-recovery monitoring.
        
        Returns:
            True if monitoring stopped successfully
        """
        try:
            logger.info("Stopping auto-recovery monitoring...")
            self.shutdown_event.set()
            
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=10)
            
            self.status = RecoveryStatus.IDLE
            logger.info("Auto-recovery monitoring stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}")
            return False
    
    def _monitoring_loop(self):
        """Main monitoring loop for auto-recovery"""
        logger.info("Auto-recovery monitoring loop started")
        
        while not self.shutdown_event.is_set():
            try:
                # Check if recovery is needed
                if self._should_attempt_recovery():
                    self._attempt_recovery()
                
                # Wait for next check
                self.shutdown_event.wait(self.config.check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Brief pause on error
        
        logger.info("Auto-recovery monitoring loop stopped")
    
    def _should_attempt_recovery(self) -> bool:
        """
        Determine if recovery should be attempted.
        
        Returns:
            True if recovery should be attempted
        """
        try:
            # Check if we're already recovering
            if self.status == RecoveryStatus.RECOVERING:
                return False
            
            # Check if we've exceeded max consecutive failures
            if self.consecutive_failures >= self.config.max_consecutive_failures:
                logger.warning(f"Max consecutive failures ({self.config.max_consecutive_failures}) exceeded")
                return False
            
            # Check if we need manual intervention
            if self.consecutive_failures >= self.config.require_manual_intervention_after:
                logger.warning(f"Manual intervention required after {self.consecutive_failures} failures")
                return False
            
            # Check for stuck tracks (tracks in 'analyzing' status for too long)
            import sqlite3
            with sqlite3.connect(self.monitor.db_path) as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) 
                    FROM tracks 
                    WHERE analysis_status = 'analyzing' 
                    AND (analysis_started_at IS NULL 
                         OR analysis_started_at < datetime('now', '-10 minutes'))
                """)
                stuck_count = cursor.fetchone()[0]
                
                if stuck_count > 0:
                    logger.info(f"Found {stuck_count} stuck tracks in 'analyzing' status - recovery needed")
                    return True
            
            # Check if analysis is stalled
            if not self.monitor._is_analysis_stalled():
                return False
            
            # Check backoff timing
            if self.last_recovery_attempt:
                time_since_last = (datetime.now() - self.last_recovery_attempt).total_seconds()
                backoff_seconds = self.backoff_multiplier * self.config.base_backoff_minutes * 60
                
                if time_since_last < backoff_seconds:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking if recovery should be attempted: {e}")
            return False
    
    def _attempt_recovery(self) -> bool:
        """
        Attempt to recover stalled analysis.
        
        Returns:
            True if recovery was successful
        """
        with self.recovery_lock:
            try:
                logger.info("Attempting auto-recovery of stalled analysis...")
                self.status = RecoveryStatus.RECOVERING
                
                # Record recovery attempt
                recovery_start = datetime.now()
                reason = "Analysis stalled - automatic restart"
                
                # Attempt restart
                success = self._perform_restart()
                
                # Calculate recovery time
                recovery_time = (datetime.now() - recovery_start).total_seconds()
                
                # Record attempt
                attempt = RecoveryAttempt(
                    timestamp=recovery_start,
                    reason=reason,
                    success=success,
                    recovery_time=recovery_time
                )
                
                if not success:
                    attempt.error_message = "Restart callback failed or returned False"
                
                self.recovery_attempts.append(attempt)
                self.last_recovery_attempt = recovery_start
                
                if success:
                    logger.info(f"Auto-recovery successful in {recovery_time:.2f}s")
                    self.consecutive_failures = 0
                    self.backoff_multiplier = 1
                    self.status = RecoveryStatus.MONITORING
                else:
                    logger.error(f"Auto-recovery failed in {recovery_time:.2f}s")
                    self.consecutive_failures += 1
                    self.backoff_multiplier = min(self.backoff_multiplier * 2, 
                                                self.config.max_backoff_minutes / self.config.base_backoff_minutes)
                    self.status = RecoveryStatus.FAILED
                    
                    # Wait before returning to monitoring
                    time.sleep(5)
                    self.status = RecoveryStatus.MONITORING
                
                return success
                
            except Exception as e:
                logger.error(f"Error during recovery attempt: {e}")
                
                # Record failed attempt
                attempt = RecoveryAttempt(
                    timestamp=datetime.now(),
                    reason="Recovery attempt failed with exception",
                    success=False,
                    error_message=str(e)
                )
                self.recovery_attempts.append(attempt)
                
                self.consecutive_failures += 1
                self.status = RecoveryStatus.FAILED
                
                # Wait before returning to monitoring
                time.sleep(5)
                self.status = RecoveryStatus.MONITORING
                
                return False
    
    def _perform_restart(self) -> bool:
        """
        Perform the actual restart operation.
        
        Returns:
            True if restart was successful
        """
        try:
            if not self.restart_callback:
                logger.warning("No restart callback provided")
                return False
            
            # Call the restart callback
            result = self.restart_callback()
            
            if result is None:
                # Assume success if callback doesn't return a value
                return True
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error in restart callback: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current auto-recovery status.
        
        Returns:
            Dictionary with recovery status information
        """
        with self.recovery_lock:
            return {
                'status': self.status.value,
                'enabled': self.config.enabled,
                'consecutive_failures': self.consecutive_failures,
                'backoff_multiplier': self.backoff_multiplier,
                'next_recovery_available': self._get_next_recovery_time(),
                'recovery_attempts_count': len(self.recovery_attempts),
                'last_recovery_attempt': self.last_recovery_attempt.isoformat() if self.last_recovery_attempt else None,
                'requires_manual_intervention': self.consecutive_failures >= self.config.require_manual_intervention_after,
                'monitoring_active': self.monitoring_thread and self.monitoring_thread.is_alive()
            }
    
    def _get_next_recovery_time(self) -> Optional[str]:
        """Get the next time recovery will be available."""
        if not self.last_recovery_attempt:
            return None
        
        backoff_seconds = self.backoff_multiplier * self.config.base_backoff_minutes * 60
        next_available = self.last_recovery_attempt + timedelta(seconds=backoff_seconds)
        
        if next_available <= datetime.now():
            return "Available now"
        
        return next_available.isoformat()
    
    def get_recovery_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recovery attempt history.
        
        Args:
            limit: Maximum number of attempts to return
            
        Returns:
            List of recovery attempt dictionaries
        """
        with self.recovery_lock:
            history = []
            for attempt in self.recovery_attempts[-limit:]:
                history.append({
                    'timestamp': attempt.timestamp.isoformat(),
                    'reason': attempt.reason,
                    'success': attempt.success,
                    'error_message': attempt.error_message,
                    'recovery_time': attempt.recovery_time
                })
            
            return history
    
    def reset_failure_count(self):
        """Reset the consecutive failure count (manual intervention)."""
        with self.recovery_lock:
            self.consecutive_failures = 0
            self.backoff_multiplier = 1
            logger.info("Failure count reset by manual intervention")
    
    def force_recovery(self) -> bool:
        """
        Force a recovery attempt (bypassing normal checks).
        
        Returns:
            True if recovery was successful
        """
        logger.info("Manual recovery attempt requested")
        return self._attempt_recovery()


def main():
    """Test function for the AutoRecovery system"""
    print("🎵 TuneForge Audio Analysis Auto-Recovery Test")
    print("=" * 60)
    
    try:
        # Initialize auto-recovery system
        config = AutoRecoveryConfig(
            enabled=True,
            check_interval=30,  # Check every 30 seconds for testing
            max_consecutive_failures=3,
            base_backoff_minutes=1,  # 1 minute base backoff for testing
            max_backoff_minutes=10
        )
        
        # Create a simple restart callback for testing
        def test_restart_callback():
            print("   🔄 Test restart callback called")
            return True  # Simulate successful restart
        
        auto_recovery = AudioAnalysisAutoRecovery(
            config=config,
            restart_callback=test_restart_callback
        )
        
        print("✅ AutoRecovery system initialized successfully")
        
        # Test status
        print(f"\n📊 Initial Status:")
        status = auto_recovery.get_status()
        for key, value in status.items():
            print(f"   - {key}: {value}")
        
        # Test monitoring start
        print(f"\n🚀 Starting monitoring...")
        if auto_recovery.start_monitoring():
            print("   ✅ Monitoring started successfully")
            
            # Let it run for a few seconds
            time.sleep(3)
            
            # Test status while running
            print(f"\n📊 Status while monitoring:")
            status = auto_recovery.get_status()
            print(f"   - Status: {status['status']}")
            print(f"   - Monitoring active: {status['monitoring_active']}")
            
            # Stop monitoring
            print(f"\n🛑 Stopping monitoring...")
            if auto_recovery.stop_monitoring():
                print("   ✅ Monitoring stopped successfully")
            
        else:
            print("   ❌ Failed to start monitoring")
        
        print(f"\n🚀 Audio Analysis Auto-Recovery is ready for Phase 2, Task 2.1!")
        print("📊 Ready to automatically restart stalled analysis")
        
    except Exception as e:
        print(f"❌ Auto-recovery test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
