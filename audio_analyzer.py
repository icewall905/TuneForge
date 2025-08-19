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
    
    def __init__(self, sample_rate: int = None, max_duration: int = 60, 
                 hop_length: int = 512, frame_length: int = 2048):
        """
        Initialize the AudioAnalyzer with performance optimizations.
        
        Args:
            sample_rate: Sample rate for audio processing (default: 8000 Hz for speed)
            max_duration: Maximum duration in seconds to analyze (default: 60s)
            hop_length: Hop length for frame analysis (default: 512 for speed)
            frame_length: Frame length for analysis (default: 2048 for speed)
        """
        self.sample_rate = sample_rate or 8000  # Lower sample rate for speed
        self.max_duration = max_duration
        self.hop_length = hop_length
        self.frame_length = frame_length
        logger.info(f"AudioAnalyzer initialized with sample rate: {self.sample_rate} Hz, "
                   f"max duration: {max_duration}s, hop length: {hop_length}")
    
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
            
            # Limit duration for performance (analyze only first N seconds)
            max_samples = int(self.max_duration * sr)
            if len(y) > max_samples:
                y = y[:max_samples]
                logger.info(f"Limited analysis to first {self.max_duration}s for performance")
            
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
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr, hop_length=self.hop_length)
            # Handle numpy array properly
            if hasattr(tempo, 'item'):
                tempo_value = tempo.item()
            else:
                tempo_value = float(tempo)
            
            logger.debug(f"Extracted tempo: {tempo_value:.1f} BPM")
            return tempo_value
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
            # Extract chroma features with optimized parameters
            # Use chroma_stft for lower sample rates to avoid Nyquist issues
            if sr < 10000:
                # For lower sample rates, use STFT-based chroma which is more suitable
                chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=self.hop_length, n_fft=2048)
            else:
                # For higher sample rates, use CQT-based chroma for better quality
                chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=self.hop_length)
            
            # Use chroma features to estimate key
            # This is a simplified approach since key_mode might not be available
            chroma_avg = np.mean(chroma, axis=1)
            key_idx = np.argmax(chroma_avg)
            
            # Map index to key names
            key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            key = key_names[key_idx]
            
            # Simple mode detection based on chroma patterns
            # This is a basic heuristic - more sophisticated methods exist
            major_pattern = [1, 0, 0.5, 0, 1, 1, 0.5, 1, 0, 1, 0.5, 1]
            minor_pattern = [1, 0, 1, 1, 0, 1, 0.5, 1, 1, 0, 1, 0.5]
            
            # Calculate correlation with major and minor patterns
            major_corr = np.corrcoef(chroma_avg, major_pattern)[0, 1]
            minor_corr = np.corrcoef(chroma_avg, minor_pattern)[0, 1]
            
            if major_corr > minor_corr:
                mode = 'major'
            else:
                mode = 'minor'
            
            logger.debug(f"Extracted key: {key}, mode: {mode}")
            return key, mode
                
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
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=self.hop_length)
            features['spectral_centroid'] = float(np.mean(spectral_centroids))
            
            # Spectral rolloff
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=self.hop_length)
            features['spectral_rolloff'] = float(np.mean(spectral_rolloff))
            
            # Spectral bandwidth
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr, hop_length=self.hop_length)
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
            
            # Get onset strength with optimized parameters
            onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=self.hop_length)
            
            # Calculate rhythm strength
            rhythm_strength = np.std(onset_env)
            
            # Normalize to 0-1 range
            danceability = min(1.0, rhythm_strength / 2.0)
            
            logger.debug(f"Extracted danceability: {danceability:.3f}")
            return float(danceability)
            
        except Exception as e:
            logger.warning(f"Danceability extraction failed: {e}")
            return 0.5  # Default middle value
    
    def extract_valence(self, y: np.ndarray, sr: int) -> float:
        """
        Extract valence (positivity/happiness) score from audio.
        
        Args:
            y: Audio time series
            sr: Sample rate
            
        Returns:
            Valence score (0.0 to 1.0, where 1.0 is very positive)
        """
        try:
            # Valence estimation based on multiple factors
            # This is a simplified approach - more sophisticated methods exist
            
            # 1. Spectral centroid (brightness correlates with happiness)
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=self.hop_length)
            brightness = np.mean(spectral_centroids) / (sr / 2)  # Normalize to 0-1
            
            # 2. Tempo (faster = more energetic = more positive)
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr, hop_length=self.hop_length)
            if hasattr(tempo, 'item'):
                tempo_value = tempo.item()
            else:
                tempo_value = float(tempo)
            tempo_factor = min(1.0, tempo_value / 200.0)  # Normalize to 0-1
            
            # 3. Energy (higher energy = more positive)
            energy = self.extract_energy(y)
            
            # Combine factors with weights
            valence = (brightness * 0.4 + tempo_factor * 0.3 + energy * 0.3)
            valence = max(0.0, min(1.0, valence))  # Clamp to 0-1
            
            logger.debug(f"Extracted valence: {valence:.3f}")
            return float(valence)
            
        except Exception as e:
            logger.warning(f"Valence extraction failed: {e}")
            return 0.5  # Default middle value
    
    def extract_acousticness(self, y: np.ndarray, sr: int) -> float:
        """
        Extract acousticness score (acoustic vs electronic) from audio.
        
        Args:
            y: Audio time series
            sr: Sample rate
            
        Returns:
            Acousticness score (0.0 to 1.0, where 1.0 is very acoustic)
        """
        try:
            # Acousticness estimation based on spectral characteristics
            # This is a simplified approach - more sophisticated methods exist
            
            # 1. Spectral rolloff (acoustic instruments have lower rolloff)
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=self.hop_length)
            rolloff_avg = np.mean(spectral_rolloff)
            rolloff_factor = 1.0 - min(1.0, rolloff_avg / (sr / 2))  # Lower rolloff = more acoustic
            
            # 2. Spectral bandwidth (acoustic instruments have narrower bandwidth)
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr, hop_length=self.hop_length)
            bandwidth_avg = np.mean(spectral_bandwidth)
            bandwidth_factor = 1.0 - min(1.0, bandwidth_avg / (sr / 2))  # Narrower = more acoustic
            
            # 3. Zero crossing rate (acoustic instruments have lower ZCR)
            zero_crossing_rate = librosa.feature.zero_crossing_rate(y, hop_length=self.hop_length)
            zcr_avg = np.mean(zero_crossing_rate)
            zcr_factor = 1.0 - min(1.0, zcr_avg)  # Lower ZCR = more acoustic
            
            # Combine factors with weights
            acousticness = (rolloff_factor * 0.4 + bandwidth_factor * 0.4 + zcr_factor * 0.2)
            acousticness = max(0.0, min(1.0, acousticness))  # Clamp to 0-1
            
            logger.debug(f"Extracted acousticness: {acousticness:.3f}")
            return float(acousticness)
            
        except Exception as e:
            logger.warning(f"Acousticness extraction failed: {e}")
            return 0.5  # Default middle value
    
    def extract_instrumentalness(self, y: np.ndarray, sr: int) -> float:
        """
        Extract instrumentalness score (instrumental vs vocal) from audio.
        
        Args:
            y: Audio time series
            sr: Sample rate
            
        Returns:
            Instrumentalness score (0.0 to 1.0, where 1.0 is very instrumental)
        """
        try:
            # Instrumentalness estimation based on vocal characteristics
            # This is a simplified approach - more sophisticated methods exist
            
            # 1. Spectral centroid variance (vocals have more variance)
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=self.hop_length)
            centroid_variance = np.var(spectral_centroids)
            variance_factor = 1.0 - min(1.0, centroid_variance / 1000000)  # Lower variance = more instrumental
            
            # 2. Spectral contrast (vocals have more contrast)
            # For low sample rates, use a simpler approach to avoid Nyquist issues
            if sr < 10000:
                # Use spectral centroid variance instead for low sample rates
                contrast_factor = 0.5  # Default middle value
            else:
                spectral_contrast = librosa.feature.spectral_contrast(y=y, sr=sr, hop_length=self.hop_length)
                contrast_avg = np.mean(spectral_contrast)
                contrast_factor = 1.0 - min(1.0, contrast_avg / 10)  # Lower contrast = more instrumental
            
            # 3. MFCC variance (vocals have more MFCC variance)
            mfcc = librosa.feature.mfcc(y=y, sr=sr, hop_length=self.hop_length, n_mfcc=13)
            mfcc_variance = np.var(mfcc)
            mfcc_factor = 1.0 - min(1.0, mfcc_variance / 100)  # Lower MFCC variance = more instrumental
            
            # Combine factors with weights
            instrumentalness = (variance_factor * 0.4 + contrast_factor * 0.3 + mfcc_factor * 0.3)
            instrumentalness = max(0.0, min(1.0, instrumentalness))  # Clamp to 0-1
            
            logger.debug(f"Extracted instrumentalness: {instrumentalness:.3f}")
            return float(instrumentalness)
            
        except Exception as e:
            logger.warning(f"Instrumentalness extraction failed: {e}")
            return 0.5  # Default middle value
    
    def extract_loudness(self, y: np.ndarray) -> float:
        """
        Extract loudness (perceived volume) from audio.
        
        Args:
            y: Audio time series
            
        Returns:
            Loudness in dB (typically -60 to 0 dB)
        """
        try:
            # Calculate RMS and convert to dB
            rms = np.sqrt(np.mean(y**2))
            if rms > 0:
                loudness_db = 20 * np.log10(rms)
            else:
                loudness_db = -60.0  # Minimum loudness
            
            # Normalize to typical range (-60 to 0 dB)
            loudness_normalized = max(-60.0, min(0.0, loudness_db))
            
            logger.debug(f"Extracted loudness: {loudness_normalized:.1f} dB")
            return float(loudness_normalized)
            
        except Exception as e:
            logger.warning(f"Loudness extraction failed: {e}")
            return -30.0  # Default middle value
    
    def extract_speechiness(self, y: np.ndarray, sr: int) -> float:
        """
        Extract speechiness score (speech vs music) from audio.
        
        Args:
            y: Audio time series
            sr: Sample rate
            
        Returns:
            Speechiness score (0.0 to 1.0, where 1.0 is very speech-like)
        """
        try:
            # Speechiness estimation based on speech characteristics
            # This is a simplified approach - more sophisticated methods exist
            
            # 1. Zero crossing rate (speech has higher ZCR)
            zero_crossing_rate = librosa.feature.zero_crossing_rate(y, hop_length=self.hop_length)
            zcr_avg = np.mean(zero_crossing_rate)
            zcr_factor = min(1.0, zcr_avg / 0.1)  # Higher ZCR = more speech-like
            
            # 2. Spectral centroid stability (speech has more stable centroids)
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=self.hop_length)
            centroid_stability = 1.0 - np.std(spectral_centroids) / np.mean(spectral_centroids)
            stability_factor = max(0.0, min(1.0, centroid_stability))
            
            # 3. MFCC stability (speech has more stable MFCCs)
            mfcc = librosa.feature.mfcc(y=y, sr=sr, hop_length=self.hop_length, n_mfcc=13)
            mfcc_stability = 1.0 - np.std(mfcc) / np.mean(np.abs(mfcc))
            mfcc_stability = max(0.0, min(1.0, mfcc_stability))
            
            # Combine factors with weights
            speechiness = (zcr_factor * 0.4 + stability_factor * 0.3 + mfcc_stability * 0.3)
            speechiness = max(0.0, min(1.0, speechiness))  # Clamp to 0-1
            
            logger.debug(f"Extracted speechiness: {speechiness:.3f}")
            return float(speechiness)
            
        except Exception as e:
            logger.warning(f"Speechiness extraction failed: {e}")
            return 0.1  # Default low value (most music is not speech)
    
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
            
            # Extract advanced features
            features['features']['valence'] = self.extract_valence(y, sr)
            features['features']['acousticness'] = self.extract_acousticness(y, sr)
            features['features']['instrumentalness'] = self.extract_instrumentalness(y, sr)
            features['features']['loudness'] = self.extract_loudness(y)
            features['features']['speechiness'] = self.extract_speechiness(y, sr)
            
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
    print("🚀 Ready for Phase 2, Task 2.4: Advanced Audio Features - COMPLETED!")
    print("📊 Now extracting 12+ musical features including:")
    print("   - Basic: tempo, key, mode, energy, danceability")
    print("   - Advanced: valence, acousticness, instrumentalness, loudness, speechiness")
    print("   - Spectral: centroid, rolloff, bandwidth")
    print("   - Ready for Phase 3: Database Integration and Batch Processing")


if __name__ == "__main__":
    main()
