#!/usr/bin/env python3
"""
Monitoring Configuration Manager

This module provides configuration management for the audio analysis monitoring system.
It handles loading, validation, and access to monitoring configuration settings.
"""

import os
import configparser
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MonitoringConfig:
    """Configuration for monitoring system"""
    enabled: bool = True
    stall_detection_timeout: int = 300  # 5 minutes
    monitoring_interval: int = 60       # 1 minute
    progress_history_retention_days: int = 7
    
    # Progress monitoring settings
    min_progress_threshold: float = 0.1  # Minimum progress rate to consider healthy
    max_consecutive_stalls: int = 3      # Max consecutive stalls before escalating
    
    # Auto-recovery settings
    auto_recovery_enabled: bool = True
    auto_recovery_check_interval: int = 60
    max_consecutive_failures: int = 3
    recovery_backoff_multiplier: float = 2.0
    recovery_max_delay: int = 1800  # 30 minutes
    
    # Alert thresholds
    high_error_rate_threshold: float = 10.0  # percentage
    stall_warning_threshold: int = 2
    escalation_threshold: int = 3
    critical_stall_threshold: int = 5
    progress_stagnation_hours: int = 2
    
    # UI update intervals
    health_update_interval: int = 10
    stall_detection_interval: int = 5
    progress_update_interval: int = 2
    recovery_status_interval: int = 15

@dataclass
class LoggingConfig:
    """Configuration for logging system"""
    log_level: str = "INFO"
    log_file: str = "logs/tuneforge.log"
    max_log_size: str = "10MB"
    backup_count: int = 5

class MonitoringConfigManager:
    """Manages monitoring configuration loading and validation"""
    
    def __init__(self, config_file: str = "config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.monitoring_config = MonitoringConfig()
        self.logging_config = LoggingConfig()
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                self.config.read(self.config_file)
                self._parse_monitoring_config()
                self._parse_logging_config()
                logger.info(f"Configuration loaded from {self.config_file}")
            else:
                logger.warning(f"Configuration file {self.config_file} not found, using defaults")
                self._create_default_config()
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            logger.info("Using default configuration values")
    
    def _parse_monitoring_config(self):
        """Parse monitoring configuration section"""
        if 'monitoring' in self.config:
            section = self.config['monitoring']
            
            self.monitoring_config.enabled = section.getboolean('enabled', True)
            self.monitoring_config.stall_detection_timeout = section.getint('stall_detection_timeout', 300)
            self.monitoring_config.monitoring_interval = section.getint('monitoring_interval', 60)
            self.monitoring_config.progress_history_retention_days = section.getint('progress_history_retention_days', 7)
            
            self.monitoring_config.auto_recovery_enabled = section.getboolean('auto_recovery_enabled', True)
            self.monitoring_config.auto_recovery_check_interval = section.getint('auto_recovery_check_interval', 60)
            self.monitoring_config.max_consecutive_failures = section.getint('max_consecutive_failures', 3)
            self.monitoring_config.recovery_backoff_multiplier = section.getfloat('recovery_backoff_multiplier', 2.0)
            self.monitoring_config.recovery_max_delay = section.getint('recovery_max_delay', 1800)
        
        if 'monitoring_alerts' in self.config:
            section = self.config['monitoring_alerts']
            
            self.monitoring_config.high_error_rate_threshold = section.getfloat('high_error_rate_threshold', 10.0)
            self.monitoring_config.stall_warning_threshold = section.getint('stall_warning_threshold', 2)
            self.monitoring_config.escalation_threshold = section.getint('escalation_threshold', 3)
            self.monitoring_config.critical_stall_threshold = section.getint('critical_stall_threshold', 5)
            self.monitoring_config.progress_stagnation_hours = section.getint('progress_stagnation_hours', 2)
        
        if 'monitoring_ui' in self.config:
            section = self.config['monitoring_ui']
            
            self.monitoring_config.health_update_interval = section.getint('health_update_interval', 10)
            self.monitoring_config.stall_detection_interval = section.getint('stall_detection_interval', 5)
            self.monitoring_config.progress_update_interval = section.getint('progress_update_interval', 2)
            self.monitoring_config.recovery_status_interval = section.getint('recovery_status_interval', 15)
    
    def _parse_logging_config(self):
        """Parse logging configuration section"""
        if 'logging' in self.config:
            section = self.config['logging']
            
            self.logging_config.log_level = section.get('log_level', 'INFO')
            self.logging_config.log_file = section.get('log_file', 'logs/tuneforge.log')
            self.logging_config.max_log_size = section.get('max_log_size', '10MB')
            self.logging_config.backup_count = section.getint('backup_count', 5)
    
    def _create_default_config(self):
        """Create default configuration file"""
        try:
            # Ensure logs directory exists
            os.makedirs('logs', exist_ok=True)
            
            # Create default config
            self.config['database'] = {
                'db_path': 'db/local_music.db'
            }
            
            self.config['audio_analysis'] = {
                'max_workers': '1',
                'batch_size': '100',
                'default_limit': '1000'
            }
            
            self.config['monitoring'] = {
                'enabled': 'true',
                'stall_detection_timeout': '300',
                'monitoring_interval': '60',
                'progress_history_retention_days': '7',
                'auto_recovery_enabled': 'true',
                'auto_recovery_check_interval': '60',
                'max_consecutive_failures': '3',
                'recovery_backoff_multiplier': '2.0',
                'recovery_max_delay': '1800'
            }
            
            self.config['monitoring_alerts'] = {
                'high_error_rate_threshold': '10.0',
                'stall_warning_threshold': '2',
                'escalation_threshold': '3',
                'critical_stall_threshold': '5',
                'progress_stagnation_hours': '2'
            }
            
            self.config['monitoring_ui'] = {
                'health_update_interval': '10',
                'stall_detection_interval': '5',
                'progress_update_interval': '2',
                'recovery_status_interval': '15'
            }
            
            self.config['logging'] = {
                'log_level': 'INFO',
                'log_file': 'logs/tuneforge.log',
                'max_log_size': '10MB',
                'backup_count': '5'
            }
            
            # Write default config
            with open(self.config_file, 'w') as f:
                self.config.write(f)
            
            logger.info(f"Default configuration created at {self.config_file}")
            
        except Exception as e:
            logger.error(f"Error creating default configuration: {e}")
    
    def get_monitoring_config(self) -> MonitoringConfig:
        """Get monitoring configuration"""
        return self.monitoring_config
    
    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration"""
        return self.logging_config
    
    def update_monitoring_config(self, **kwargs):
        """Update monitoring configuration"""
        for key, value in kwargs.items():
            if hasattr(self.monitoring_config, key):
                setattr(self.monitoring_config, key, value)
                logger.info(f"Updated monitoring config: {key} = {value}")
            else:
                logger.warning(f"Unknown monitoring config key: {key}")
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            # Update config parser with current values
            if 'monitoring' not in self.config:
                self.config['monitoring'] = {}
            
            monitoring_section = self.config['monitoring']
            monitoring_section['enabled'] = str(self.monitoring_config.enabled)
            monitoring_section['stall_detection_timeout'] = str(self.monitoring_config.stall_detection_timeout)
            monitoring_section['monitoring_interval'] = str(self.monitoring_config.monitoring_interval)
            monitoring_section['progress_history_retention_days'] = str(self.monitoring_config.progress_history_retention_days)
            monitoring_section['auto_recovery_enabled'] = str(self.monitoring_config.auto_recovery_enabled)
            monitoring_section['auto_recovery_check_interval'] = str(self.monitoring_config.auto_recovery_check_interval)
            monitoring_section['max_consecutive_failures'] = str(self.monitoring_config.max_consecutive_failures)
            monitoring_section['recovery_backoff_multiplier'] = str(self.monitoring_config.recovery_backoff_multiplier)
            monitoring_section['recovery_max_delay'] = str(self.monitoring_config.recovery_max_delay)
            
            # Write to file
            with open(self.config_file, 'w') as f:
                self.config.write(f)
            
            logger.info(f"Configuration saved to {self.config_file}")
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration and return validation results"""
        validation_results = {
            'valid': True,
            'warnings': [],
            'errors': []
        }
        
        # Validate monitoring intervals
        if self.monitoring_config.stall_detection_interval >= self.monitoring_config.monitoring_interval:
            validation_results['warnings'].append(
                "Stall detection interval should be less than monitoring interval for optimal performance"
            )
        
        if self.monitoring_config.health_update_interval < 5:
            validation_results['warnings'].append(
                "Health update interval below 5 seconds may impact performance"
            )
        
        # Validate thresholds
        if self.monitoring_config.high_error_rate_threshold > 50:
            validation_results['warnings'].append(
                "High error rate threshold above 50% may mask serious issues"
            )
        
        if self.monitoring_config.critical_stall_threshold < self.monitoring_config.escalation_threshold:
            validation_results['errors'].append(
                "Critical stall threshold must be greater than escalation threshold"
            )
        
        # Check for errors
        if validation_results['errors']:
            validation_results['valid'] = False
        
        return validation_results
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration"""
        return {
            'monitoring_enabled': self.monitoring_config.enabled,
            'auto_recovery_enabled': self.monitoring_config.auto_recovery_enabled,
            'stall_detection_timeout': f"{self.monitoring_config.stall_detection_timeout}s",
            'monitoring_interval': f"{self.monitoring_config.monitoring_interval}s",
            'health_update_interval': f"{self.monitoring_config.health_update_interval}s",
            'stall_detection_interval': f"{self.monitoring_config.stall_detection_interval}s",
            'max_consecutive_failures': self.monitoring_config.max_consecutive_failures,
            'high_error_rate_threshold': f"{self.monitoring_config.high_error_rate_threshold}%",
            'progress_history_retention': f"{self.monitoring_config.progress_history_retention_days} days"
        }

def get_config_manager(config_file: str = "config.ini") -> MonitoringConfigManager:
    """Get a configuration manager instance"""
    return MonitoringConfigManager(config_file)

if __name__ == "__main__":
    # Test configuration manager
    config_manager = MonitoringConfigManager()
    
    print("🎵 TuneForge Monitoring Configuration")
    print("=" * 50)
    
    # Show current config
    config_summary = config_manager.get_config_summary()
    for key, value in config_summary.items():
        print(f"{key.replace('_', ' ').title()}: {value}")
    
    # Validate config
    validation = config_manager.validate_config()
    print(f"\nConfiguration Valid: {validation['valid']}")
    
    if validation['warnings']:
        print("\n⚠️ Warnings:")
        for warning in validation['warnings']:
            print(f"   • {warning}")
    
    if validation['errors']:
        print("\n❌ Errors:")
        for error in validation['errors']:
            print(f"   • {error}")
    
    if validation['valid']:
        print("\n✅ Configuration is valid and ready to use!")
    else:
        print("\n❌ Configuration has errors that need to be fixed!")
