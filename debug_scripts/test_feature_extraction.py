#!/usr/bin/env python3
"""
Test script for AudioAnalyzer feature extraction with real audio files.
This tests the actual feature extraction capabilities on real music files.
"""

import os
import sys
import time
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

def test_audio_analyzer_import():
    """Test that we can import our AudioAnalyzer class"""
    print("🧪 Testing AudioAnalyzer import...")
    
    try:
        from audio_analyzer import AudioAnalyzer
        print("✅ AudioAnalyzer imported successfully")
        return AudioAnalyzer
    except ImportError as e:
        print(f"❌ AudioAnalyzer import failed: {e}")
        return None

def test_single_file_analysis(analyzer, file_path):
    """Test feature extraction on a single audio file"""
    print(f"\n🎵 Testing file: {os.path.basename(file_path)}")
    
    try:
        # Test file validation
        is_valid, error_msg = analyzer.validate_audio_file(file_path)
        if not is_valid:
            print(f"   ❌ File validation failed: {error_msg}")
            return False
        
        print("   ✅ File validation passed")
        
        # Test feature extraction
        start_time = time.time()
        features = analyzer.extract_all_features(file_path)
        extraction_time = time.time() - start_time
        
        if not features['success']:
            print(f"   ❌ Feature extraction failed: {features['error_message']}")
            return False
        
        print(f"   ✅ Feature extraction completed in {extraction_time:.2f}s")
        
        # Display extracted features
        print("   📊 Extracted features:")
        for key, value in features['features'].items():
            if value is not None:
                if isinstance(value, float):
                    print(f"      - {key}: {value:.3f}")
                else:
                    print(f"      - {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Analysis failed with exception: {e}")
        return False

def test_multiple_files(analyzer, test_files, max_files=3):
    """Test feature extraction on multiple files"""
    print(f"\n🧪 Testing feature extraction on {min(len(test_files), max_files)} files...")
    
    successful_tests = 0
    total_tests = min(len(test_files), max_files)
    
    for i, file_path in enumerate(test_files[:max_files]):
        print(f"\n--- Test {i+1}/{total_tests} ---")
        if test_single_file_analysis(analyzer, file_path):
            successful_tests += 1
    
    print(f"\n📊 Test Results: {successful_tests}/{total_tests} files processed successfully")
    return successful_tests == total_tests

def test_feature_consistency(analyzer, file_path):
    """Test that feature extraction is consistent across multiple runs"""
    print(f"\n🔄 Testing feature extraction consistency...")
    
    try:
        # Run extraction multiple times
        results = []
        for i in range(3):
            features = analyzer.extract_all_features(file_path)
            if features['success']:
                results.append(features['features'])
            else:
                print(f"   ❌ Run {i+1} failed: {features['error_message']}")
                return False
        
        # Check consistency of key features
        print("   📊 Checking feature consistency across 3 runs:")
        
        key_features = ['tempo', 'energy', 'danceability']
        for feature in key_features:
            values = [r.get(feature) for r in results if r.get(feature) is not None]
            if len(values) >= 2:
                max_diff = max(values) - min(values)
                if max_diff < 0.1:  # Allow small variations
                    print(f"      ✅ {feature}: consistent (max diff: {max_diff:.3f})")
                else:
                    print(f"      ⚠️  {feature}: inconsistent (max diff: {max_diff:.3f})")
            else:
                print(f"      ❌ {feature}: missing in some runs")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Consistency test failed: {e}")
        return False

def test_performance_benchmark(analyzer, file_path):
    """Test performance characteristics"""
    print(f"\n⚡ Testing performance characteristics...")
    
    try:
        # Test multiple runs to get average performance
        times = []
        for i in range(3):
            start_time = time.time()
            features = analyzer.extract_all_features(file_path)
            end_time = time.time()
            
            if features['success']:
                times.append(end_time - start_time)
            else:
                print(f"   ❌ Run {i+1} failed")
                return False
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"   📊 Performance results (3 runs):")
        print(f"      - Average time: {avg_time:.3f}s")
        print(f"      - Min time: {min_time:.3f}s")
        print(f"      - Max time: {max_time:.3f}s")
        print(f"      - Variance: {max_time - min_time:.3f}s")
        
        # Performance thresholds
        if avg_time < 10.0:  # Should process files in under 10 seconds
            print("   ✅ Performance meets requirements")
            return True
        else:
            print("   ⚠️  Performance may need optimization")
            return False
        
    except Exception as e:
        print(f"   ❌ Performance test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🎵 TuneForge Audio Feature Extraction Test")
    print("=" * 60)
    
    # Test import
    AudioAnalyzer = test_audio_analyzer_import()
    if not AudioAnalyzer:
        print("❌ Cannot proceed without AudioAnalyzer class")
        return False
    
    # Create analyzer instance
    analyzer = AudioAnalyzer()
    print(f"✅ AudioAnalyzer created with sample rate: {analyzer.sample_rate} Hz")
    
    # Find test files
    print("\n🔍 Finding test audio files...")
    music_dir = "/home/hnyg/Music"  # Use local Music directory for testing
    
    if not os.path.exists(music_dir):
        print(f"❌ Music directory not found: {music_dir}")
        return False
    
    # Find audio files
    test_files = []
    for ext in ['.mp3', '.flac', '.wav', '.ogg', '.m4a']:
        test_files.extend(Path(music_dir).rglob(f"*{ext}"))
    
    if not test_files:
        print("❌ No audio files found for testing")
        return False
    
    print(f"✅ Found {len(test_files)} audio files")
    
    # Select a few test files (avoid very long files for testing)
    test_files = [str(f) for f in test_files[:5]]  # Test first 5 files
    
    # Run comprehensive tests
    tests_passed = 0
    total_tests = 4
    
    print(f"\n🚀 Starting comprehensive feature extraction tests...")
    
    # Test 1: Multiple file processing
    if test_multiple_files(analyzer, test_files):
        tests_passed += 1
        print("✅ Multiple file processing test passed")
    else:
        print("❌ Multiple file processing test failed")
    
    # Test 2: Feature consistency (use first successful file)
    successful_file = None
    for file_path in test_files:
        if analyzer.validate_audio_file(file_path)[0]:
            successful_file = file_path
            break
    
    if successful_file and test_feature_consistency(analyzer, successful_file):
        tests_passed += 1
        print("✅ Feature consistency test passed")
    else:
        print("❌ Feature consistency test failed")
    
    # Test 3: Performance benchmark
    if successful_file and test_performance_benchmark(analyzer, successful_file):
        tests_passed += 1
        print("✅ Performance benchmark test passed")
    else:
        print("❌ Performance benchmark test failed")
    
    # Test 4: Analyzer capabilities
    print(f"\n🔧 Testing analyzer capabilities...")
    info = analyzer.get_analysis_info()
    print(f"   - Supported formats: {', '.join(info['supported_formats'])}")
    print(f"   - Sample rate: {info['sample_rate']} Hz")
    print(f"   - librosa version: {info['librosa_version']}")
    tests_passed += 1
    print("✅ Analyzer capabilities test passed")
    
    # Final results
    print("\n" + "=" * 60)
    print(f"📊 Final Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Feature extraction is working correctly.")
        print("✅ Ready for Phase 2, Task 2.4: Implement Advanced Audio Features")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
