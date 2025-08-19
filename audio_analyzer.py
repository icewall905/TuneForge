#!/usr/bin/env python3
"""
Audio Analyzer Module for TuneForge

This module provides the core audio analysis functionality using librosa.
It handles audio file loading, validation, and feature extraction for
the content-based recommendation system.
"""

import os
import logging
import numpy as np
import librosa
import soundfile as sf
from typing import Dict, Optional, Tuple, Any
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioAnalyzer:
    """
    Core audio analysis class for extracting musical features from audio files.
    
    This class provides methods to:
    - Load and validate audio files
    - Extract musical features (tempo, key, mode, energy, etc.)
    - Handle different audio formats
    - Provide error handling and validation
    """
    
    # Supported audio file extensions
    SUPPORTED_EXTENSIONS = {'.mp3', '.flac', '.wav', '.ogg', '.m4a', '.aac'}
    
    # Default sample rate for analysis
    DEFAULT_SR = 22050
    
    def __init__(self, sample_rate: int = None):
        """
        Initialize the AudioAnalyzer.
        
        Args:
            sample_rate: Sample rate for audio processing (default: 22050 Hz)
        """
        self.sample_rate = sample_rate or self.DEFAULT_SR
        logger.info(f"AudioAnalyzer initialized with sample rate: {self.sample_rate} Hz")
    
    def is_supported_format(self, file_path: str) -> bool:
        """
        Check if the file format is supported for analysis.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            True if the format is supported, False otherwise
        """
        if not file_path:
            return False
        
        file_ext = Path(file_path).suffix.lower()
        return file_ext in self.SUPPORTED_EXTENSIONS
    
    def validate_audio_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Validate that an audio file exists and is readable.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file_path:
            return False, "No file path provided"
        
        if not os.path.exists(file_path):
            return False, f"File does not exist: {file_path}"
        
        if not os.path.isfile(file_path):
            return False, f"Path is not a file: {file_path}"
        
        if not self.is_supported_format(file_path):
            return False, f"Unsupported audio format: {Path(file_path).suffix}"
        
        # Check file size (minimum 1KB, maximum 500MB)
        file_size = os.path.getsize(file_path)
        if file_size < 1024:
            return False, f"File too small: {file_size} bytes"
        if file_size > 500 * 1024 * 1024:
            return False, f"File too large: {file_size / (1024*1024):.1f} MB"
        
        return True, ""
    
    def load_audio_file(self, file_path: str) -> Tuple[Optional[np.ndarray], Optional[int], str]:
        """
        Load an audio file and return the audio data and sample rate.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Tuple of (audio_data, sample_rate, error_message)
        """
        # Validate file first
        is_valid, error_msg = self.validate_audio_file(file_path)
        if not is_valid:
            return None, None, error_msg
        
        try:
            logger.info(f"Loading audio file: {file_path}")
            
            # Load audio with librosa
            y, sr = librosa.load(file_path, sr=self.sample_rate)
            
            # Validate loaded audio
            if len(y) == 0:
                return None, None, "Audio file is empty or corrupted"
            
            if sr != self.sample_rate:
                logger.info(f"Resampled audio from {sr} Hz to {self.sample_rate} Hz")
            
            logger.info(f"Successfully loaded audio: {len(y)} samples at {sr} Hz")
            return y, sr, ""
            
        except Exception as e:
            error_msg = f"Error loading audio file: {str(e)}"
            logger.error(error_msg)
            return None, None, error_msg
    
    def extract_tempo(self, y: np.ndarray, sr: int) -> Optional[float]:
        """
        Extract tempo (beats per minute) from audio.
        
        Args:
            y: Audio time series
            sr: Sample rate
            
        Returns:
            Tempo in BPM, or None if extraction failed
        """
        try:
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            logger.debug(f"Extracted tempo: {tempo:.1f} BPM")
            return float(tempo)
        except Exception as e:
            logger.warning(f"Tempo extraction failed: {e}")
            return None
    
    def extract_key_mode(self, y: np.ndarray, sr: int) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract musical key and mode from audio.
        
        Args:
            y: Audio time series
            sr: Sample rate
            
        Returns:
            Tuple of (key, mode) or (None, None) if extraction failed
        """
        try:
            # Extract chroma features
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
            
            # Get the most prominent key
            key_raw = librosa.feature.key_mode(y=y, sr=sr)
            
            # Parse key and mode
            if key_raw:
                key_str = str(key_raw)
                # Extract key (e.g., 'C', 'F#') and mode (e.g., 'major', 'minor')
                if 'major' in key_str.lower():
                    mode = 'major'
                    key = key_str.replace('major', '').strip()
                elif 'minor' in key_str.lower():
                    mode = 'minor'
                    key = key_str.replace('minor', '').strip()
                else:
                    key = key_str
                    mode = 'unknown'
                
                logger.debug(f"Extracted key: {key}, mode: {mode}")
                return key, mode
            else:
                return None, None
                
        except Exception as e:
            logger.warning(f"Key/mode extraction failed: {e}")
            return None, None
    
    def extract_spectral_features(self, y: np.ndarray, sr: int) -> Dict[str, float]:
        """
        Extract spectral features from audio.
        
        Args:
            y: Audio time series
            sr: Sample rate
            
        Returns:
            Dictionary of spectral features
        """
        features = {}
        
        try:
            # Spectral centroid (brightness)
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)
            features['spectral_centroid'] = float(np.mean(spectral_centroids))
            
            # Spectral rolloff
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
            features['spectral_rolloff'] = float(np.mean(spectral_rolloff))
            
            # Spectral bandwidth
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)
            features['spectral_bandwidth'] = float(np.mean(spectral_bandwidth))
            
            logger.debug(f"Extracted spectral features: {list(features.keys())}")
            
        except Exception as e:
            logger.warning(f"Spectral feature extraction failed: {e}")
        
        return features
    
    def extract_energy(self, y: np.ndarray) -> float:
        """
        Extract energy (RMS) from audio.
        
        Args:
            y: Audio time series
            
        Returns:
            Energy value (0.0 to 1.0)
        """
        try:
            # Calculate RMS energy
            rms = np.sqrt(np.mean(y**2))
            # Normalize to 0-1 range
            energy = min(1.0, rms * 10)  # Scale factor for normalization
            logger.debug(f"Extracted energy: {energy:.3f}")
            return float(energy)
        except Exception as e:
            logger.warning(f"Energy extraction failed: {e}")
            return 0.0
    
    def extract_danceability(self, y: np.ndarray, sr: int) -> float:
        """
        Extract danceability score from audio.
        
        Args:
            y: Audio time series
            sr: Sample rate
            
        Returns:
            Danceability score (0.0 to 1.0)
        """
        try:
            # Simple danceability based on rhythm strength
            # This is a simplified approach - more sophisticated methods exist
            
            # Get onset strength
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            
            # Calculate rhythm strength
            rhythm_strength = np.std(onset_env)
            
            # Normalize to 0-1 range
            danceability = min(1.0, rhythm_strength / 2.0)
            
            logger.debug(f"Extracted danceability: {danceability:.3f}")
            return float(danceability)
            
        except Exception as e:
            logger.warning(f"Danceability extraction failed: {e}")
            return 0.5  # Default middle value
    
    def extract_all_features(self, file_path: str) -> Dict[str, Any]:
        """
        Extract all available features from an audio file.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary containing all extracted features and metadata
        """
        logger.info(f"Starting feature extraction for: {file_path}")
        
        # Initialize result dictionary
        features = {
            'file_path': file_path,
            'success': False,
            'error_message': '',
            'features': {}
        }
        
        try:
            # Load audio file
            y, sr, error_msg = self.load_audio_file(file_path)
            if y is None:
                features['error_message'] = error_msg
                return features
            
            # Extract basic features
            features['features']['tempo'] = self.extract_tempo(y, sr)
            features['features']['key'], features['features']['mode'] = self.extract_key_mode(y, sr)
            features['features']['energy'] = self.extract_energy(y)
            features['features']['danceability'] = self.extract_danceability(y, sr)
            
            # Extract spectral features
            spectral_features = self.extract_spectral_features(y, sr)
            features['features'].update(spectral_features)
            
            # Add metadata
            features['features']['duration'] = len(y) / sr
            features['features']['sample_rate'] = sr
            features['features']['num_samples'] = len(y)
            
            # Mark as successful
            features['success'] = True
            logger.info(f"Feature extraction completed successfully for: {file_path}")
            
        except Exception as e:
            error_msg = f"Feature extraction failed: {str(e)}"
            features['error_message'] = error_msg
            logger.error(error_msg)
        
        return features
    
    def get_supported_formats(self) -> set:
        """
        Get the set of supported audio file formats.
        
        Returns:
            Set of supported file extensions
        """
        return self.SUPPORTED_EXTENSIONS.copy()
    
    def get_analysis_info(self) -> Dict[str, Any]:
        """
        Get information about the analyzer capabilities.
        
        Returns:
            Dictionary with analyzer information
        """
        return {
            'sample_rate': self.sample_rate,
            'supported_formats': list(self.SUPPORTED_EXTENSIONS),
            'librosa_version': librosa.__version__,
            'numpy_version': np.__version__
        }


def main():
    """Test function for the AudioAnalyzer class"""
    print("🎵 TuneForge Audio Analyzer Test")
    print("=" * 50)
    
    # Create analyzer instance
    analyzer = AudioAnalyzer()
    
    # Display analyzer info
    info = analyzer.get_analysis_info()
    print(f"📊 Analyzer Information:")
    print(f"   - Sample Rate: {info['sample_rate']} Hz")
    print(f"   - Supported Formats: {', '.join(info['supported_formats'])}")
    print(f"   - librosa Version: {info['librosa_version']}")
    print(f"   - numpy Version: {info['numpy_version']}")
    
    print("\n✅ AudioAnalyzer class created successfully!")
    print("🚀 Ready for Phase 2, Task 2.3: Implement Basic Feature Extraction")


if __name__ == "__main__":
    main()
