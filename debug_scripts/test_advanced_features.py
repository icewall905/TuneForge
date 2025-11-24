#!/usr/bin/env python3
"""
Test script for advanced audio features in AudioAnalyzer.
"""

import sys
import time
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

def test_advanced_features():
    """Test all advanced features of the AudioAnalyzer"""
    try:
        from audio_analyzer import AudioAnalyzer
        
        print("🎵 TuneForge Advanced Features Test")
        print("=" * 60)
        
        # Create analyzer with optimized settings
        analyzer = AudioAnalyzer(sample_rate=8000, max_duration=60, hop_length=512)
        print(f"✅ AudioAnalyzer created with sample rate: {analyzer.sample_rate} Hz")
        
        # Test file
        test_file = "/home/hnyg/Music/3 Doors Down/3 Doors Down - Away From The Sun/01 - When I'm Gone.flac"
        
        print(f"\n🎵 Testing file: {Path(test_file).name}")
        print("=" * 60)
        
        # Extract all features
        start_time = time.time()
        features = analyzer.extract_all_features(test_file)
        extraction_time = time.time() - start_time
        
        if not features['success']:
            print(f"❌ Feature extraction failed: {features['error_message']}")
            return False
        
        print(f"✅ Feature extraction completed in {extraction_time:.2f}s")
        
        # Display all extracted features
        print(f"\n📊 All Extracted Features:")
        print("=" * 60)
        
        extracted_features = features['features']
        
        # Group features by category
        basic_features = ['tempo', 'key', 'mode', 'energy', 'danceability']
        advanced_features = ['valence', 'acousticness', 'instrumentalness', 'loudness', 'speechiness']
        spectral_features = ['spectral_centroid', 'spectral_rolloff', 'spectral_bandwidth']
        metadata_features = ['duration', 'sample_rate', 'num_samples']
        
        print("🎼 Basic Musical Features:")
        for feature in basic_features:
            if feature in extracted_features and extracted_features[feature] is not None:
                value = extracted_features[feature]
                if isinstance(value, float):
                    print(f"   {feature:15}: {value:>10.3f}")
                else:
                    print(f"   {feature:15}: {value:>10}")
        
        print("\n🚀 Advanced Audio Features:")
        for feature in advanced_features:
            if feature in extracted_features and extracted_features[feature] is not None:
                value = extracted_features[feature]
                if isinstance(value, float):
                    print(f"   {feature:15}: {value:>10.3f}")
                else:
                    print(f"   {feature:15}: {value:>10}")
        
        print("\n🔬 Spectral Features:")
        for feature in spectral_features:
            if feature in extracted_features and extracted_features[feature] is not None:
                value = extracted_features[feature]
                if isinstance(value, float):
                    print(f"   {feature:15}: {value:>10.3f}")
                else:
                    print(f"   {feature:15}: {value:>10}")
        
        print("\n📋 Metadata:")
        for feature in metadata_features:
            if feature in extracted_features and extracted_features[feature] is not None:
                value = extracted_features[feature]
                if isinstance(value, float):
                    print(f"   {feature:15}: {value:>10.3f}")
                else:
                    print(f"   {feature:15}: {value:>10}")
        
        # Feature validation
        print(f"\n🔍 Feature Validation:")
        print("=" * 60)
        
        total_features = len(extracted_features)
        non_null_features = sum(1 for v in extracted_features.values() if v is not None)
        
        print(f"Total features available: {total_features}")
        print(f"Features successfully extracted: {non_null_features}")
        print(f"Success rate: {(non_null_features/total_features)*100:.1f}%")
        
        # Check for expected feature ranges
        print(f"\n✅ Feature Range Validation:")
        print("=" * 60)
        
        range_checks = [
            ('tempo', 60, 200, 'BPM'),
            ('energy', 0.0, 1.0, 'normalized'),
            ('danceability', 0.0, 1.0, 'normalized'),
            ('valence', 0.0, 1.0, 'normalized'),
            ('acousticness', 0.0, 1.0, 'normalized'),
            ('instrumentalness', 0.0, 1.0, 'normalized'),
            ('speechiness', 0.0, 1.0, 'normalized'),
            ('loudness', -60.0, 0.0, 'dB'),
        ]
        
        for feature, min_val, max_val, unit in range_checks:
            if feature in extracted_features and extracted_features[feature] is not None:
                value = extracted_features[feature]
                if min_val <= value <= max_val:
                    print(f"   ✅ {feature:15}: {value:>8.3f} {unit:>8} (in range)")
                else:
                    print(f"   ⚠️  {feature:15}: {value:>8.3f} {unit:>8} (out of range)")
            else:
                print(f"   ❌ {feature:15}: {'MISSING':>8} {'':>8}")
        
        # Performance summary
        print(f"\n⚡ Performance Summary:")
        print("=" * 60)
        print(f"Processing time: {extraction_time:.2f}s")
        print(f"Sample rate: {analyzer.sample_rate} Hz")
        print(f"Duration limit: {analyzer.max_duration}s")
        print(f"Hop length: {analyzer.hop_length}")
        
        # Projected performance for 100k files
        files_per_hour = 3600 / extraction_time
        hours_for_100k = 100000 / files_per_hour
        
        print(f"\n📈 Projected Performance for 100,000 files:")
        print(f"Files per hour: {files_per_hour:.0f}")
        print(f"Total time: {hours_for_100k:.1f} hours ({hours_for_100k/24:.1f} days)")
        
        return True
        
    except Exception as e:
        print(f"❌ Advanced features test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_advanced_features()
    
    if success:
        print(f"\n🎉 Advanced features test completed successfully!")
        print("🚀 Phase 2, Task 2.4: Advanced Audio Features - COMPLETED!")
        print("📊 Ready for Phase 3: Database Integration and Batch Processing")
    else:
        print(f"\n❌ Advanced features test failed.")
    
    sys.exit(0 if success else 1)
