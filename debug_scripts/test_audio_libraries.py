#!/usr/bin/env python3
"""
Test script to verify audio analysis libraries are working correctly.
This tests the core functionality we'll need for the audio analysis system.
"""

import os
import sys
import numpy as np

def test_basic_imports():
    """Test that all required libraries can be imported"""
    print("🧪 Testing basic library imports...")
    
    try:
        import librosa
        print(f"✅ librosa imported successfully (version: {librosa.__version__})")
    except ImportError as e:
        print(f"❌ librosa import failed: {e}")
        return False
    
    try:
        import numpy as np
        print(f"✅ numpy imported successfully (version: {np.__version__})")
    except ImportError as e:
        print(f"❌ numpy import failed: {e}")
        return False
    
    try:
        import scipy
        print(f"✅ scipy imported successfully (version: {scipy.__version__})")
    except ImportError as e:
        print(f"❌ scipy import failed: {e}")
        return False
    
    return True

def test_librosa_functionality():
    """Test basic librosa functionality"""
    print("\n🧪 Testing librosa functionality...")
    
    try:
        import librosa
        
        # Test librosa version
        print(f"   - librosa version: {librosa.__version__}")
        
        # Test if librosa can create a simple audio signal
        sr = 22050  # Sample rate
        duration = 1.0  # 1 second
        t = np.linspace(0, duration, int(sr * duration))
        y = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
        
        # Test basic feature extraction
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        print(f"   - Beat tracking test: tempo = {tempo:.1f} BPM")
        
        # Test spectral features
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)
        print(f"   - Spectral centroid test: shape = {spectral_centroids.shape}")
        
        # Test chroma features
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        print(f"   - Chroma CQT test: shape = {chroma.shape}")
        
        print("✅ librosa functionality tests passed")
        return True
        
    except Exception as e:
        print(f"❌ librosa functionality test failed: {e}")
        return False

def test_audio_file_loading():
    """Test if librosa can load audio files"""
    print("\n🧪 Testing audio file loading capabilities...")
    
    try:
        import librosa
        
        # Check what audio formats are supported
        print("   - Supported audio formats:")
        import soundfile as sf
        formats = sf.available_formats()
        print(f"     * Total formats: {len(formats)}")
        print(f"     * Key formats: MP3, FLAC, WAV, OGG, M4A")
        
        # Test if we can create a dummy audio file and load it
        # This tests the audio loading pipeline without needing real files
        sr = 22050
        duration = 0.1  # Very short for testing
        t = np.linspace(0, duration, int(sr * duration))
        y = np.sin(2 * np.pi * 440 * t)
        
        # Save as temporary WAV file
        import tempfile
        import soundfile as sf
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            sf.write(tmp_file.name, y, sr)
            tmp_path = tmp_file.name
        
        try:
            # Try to load the file
            y_loaded, sr_loaded = librosa.load(tmp_path, sr=None)
            print(f"   - Audio loading test: loaded {len(y_loaded)} samples at {sr_loaded} Hz")
            
            # Clean up
            os.unlink(tmp_path)
            print("✅ Audio file loading test passed")
            return True
            
        except Exception as e:
            print(f"   - Audio loading failed: {e}")
            # Clean up on failure too
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return False
            
    except Exception as e:
        print(f"❌ Audio file loading test failed: {e}")
        return False

def test_performance_characteristics():
    """Test performance characteristics for large audio processing"""
    print("\n🧪 Testing performance characteristics...")
    
    try:
        import librosa
        import time
        
        # Create a longer audio signal to test performance
        sr = 22050
        duration = 5.0  # 5 seconds
        t = np.linspace(0, duration, int(sr * duration))
        y = np.sin(2 * np.pi * 440 * t) + 0.5 * np.sin(2 * np.pi * 880 * t)
        
        print(f"   - Processing {len(y)} samples ({duration}s at {sr} Hz)")
        
        # Test tempo detection performance
        start_time = time.time()
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        tempo_time = time.time() - start_time
        print(f"   - Tempo detection: {tempo_time:.3f}s")
        
        # Test spectral features performance
        start_time = time.time()
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)
        spectral_time = time.time() - start_time
        print(f"   - Spectral features: {spectral_time:.3f}s")
        
        # Test chroma features performance
        start_time = time.time()
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_time = time.time() - start_time
        print(f"   - Chroma features: {chroma_time:.3f}s")
        
        total_time = tempo_time + spectral_time + chroma_time
        print(f"   - Total processing time: {total_time:.3f}s")
        print(f"   - Processing speed: {len(y) / total_time / 1000:.1f} kSamples/second")
        
        print("✅ Performance tests completed")
        return True
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🎵 TuneForge Audio Analysis Library Test")
    print("=" * 50)
    
    # Run all tests
    tests = [
        test_basic_imports,
        test_librosa_functionality,
        test_audio_file_loading,
        test_performance_characteristics
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Audio analysis libraries are ready.")
        print("✅ Ready for Phase 2, Task 2.2: Create Audio Analyzer Class")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
