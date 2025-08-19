#!/usr/bin/env python3
"""
Performance comparison test for AudioAnalyzer optimizations.
"""

import sys
import time
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

def performance_test():
    """Test performance of optimized vs original AudioAnalyzer"""
    try:
        from audio_analyzer import AudioAnalyzer
        
        # Test file
        test_file = "/home/hnyg/Music/3 Doors Down/3 Doors Down - Away From The Sun/01 - When I'm Gone.flac"
        
        print("🚀 AudioAnalyzer Performance Test")
        print("=" * 50)
        
        # Test 1: Original settings (22050 Hz, full duration)
        print("\n🧪 Test 1: Original Settings (22050 Hz, full duration)")
        analyzer_original = AudioAnalyzer(sample_rate=22050, max_duration=300, hop_length=512, frame_length=2048)
        
        start_time = time.time()
        features_original = analyzer_original.extract_all_features(test_file)
        original_time = time.time() - start_time
        
        if features_original['success']:
            print(f"   ✅ Completed in {original_time:.2f}s")
            print(f"   📊 Sample rate: {analyzer_original.sample_rate} Hz")
            print(f"   📊 Duration limit: {analyzer_original.max_duration}s")
        else:
            print(f"   ❌ Failed: {features_original['error_message']}")
            return False
        
        # Test 2: Optimized settings (8000 Hz, 60s limit)
        print("\n🧪 Test 2: Optimized Settings (8000 Hz, 60s limit)")
        analyzer_optimized = AudioAnalyzer(sample_rate=8000, max_duration=60, hop_length=512, frame_length=2048)
        
        start_time = time.time()
        features_optimized = analyzer_optimized.extract_all_features(test_file)
        optimized_time = time.time() - start_time
        
        if features_optimized['success']:
            print(f"   ✅ Completed in {optimized_time:.2f}s")
            print(f"   📊 Sample rate: {analyzer_optimized.sample_rate} Hz")
            print(f"   📊 Duration limit: {analyzer_optimized.max_duration}s")
        else:
            print(f"   ❌ Failed: {features_optimized['error_message']}")
            return False
        
        # Test 3: Ultra-optimized settings (8000 Hz, 30s limit, larger hop)
        print("\n🧪 Test 3: Ultra-Optimized Settings (8000 Hz, 30s limit, larger hop)")
        analyzer_ultra = AudioAnalyzer(sample_rate=8000, max_duration=30, hop_length=1024, frame_length=4096)
        
        start_time = time.time()
        features_ultra = analyzer_ultra.extract_all_features(test_file)
        ultra_time = time.time() - start_time
        
        if features_ultra['success']:
            print(f"   ✅ Completed in {ultra_time:.2f}s")
            print(f"   📊 Sample rate: {analyzer_ultra.sample_rate} Hz")
            print(f"   📊 Duration limit: {analyzer_ultra.max_duration}s")
            print(f"   📊 Hop length: {analyzer_ultra.hop_length}")
        else:
            print(f"   ❌ Failed: {features_ultra['error_message']}")
            return False
        
        # Performance comparison
        print("\n📊 Performance Comparison:")
        print("=" * 50)
        print(f"Original (22050 Hz, full):     {original_time:.2f}s")
        print(f"Optimized (8000 Hz, 60s):      {optimized_time:.2f}s")
        print(f"Ultra-optimized (8000 Hz, 30s): {ultra_time:.2f}s")
        
        # Calculate improvements
        improvement_1 = ((original_time - optimized_time) / original_time) * 100
        improvement_2 = ((original_time - ultra_time) / original_time) * 100
        
        print(f"\n🚀 Performance Improvements:")
        print(f"Optimized vs Original:     {improvement_1:.1f}% faster")
        print(f"Ultra-optimized vs Original: {improvement_2:.1f}% faster")
        
        # Feature quality comparison
        print(f"\n🔍 Feature Quality Comparison:")
        print("=" * 50)
        
        if features_original['success'] and features_optimized['success'] and features_ultra['success']:
            orig_features = features_original['features']
            opt_features = features_optimized['features']
            ultra_features = features_ultra['features']
            
            # Compare key features
            for feature in ['tempo', 'key', 'mode', 'energy', 'danceability']:
                if feature in orig_features and feature in opt_features and feature in ultra_features:
                    orig_val = orig_features[feature]
                    opt_val = opt_features[feature]
                    ultra_val = ultra_features[feature]
                    
                    if orig_val is not None and opt_val is not None and ultra_val is not None:
                        print(f"{feature:15}: {orig_val:>10} | {opt_val:>10} | {ultra_val:>10}")
        
        # Projected time for 100k files
        print(f"\n📈 Projected Processing Times for 100,000 files:")
        print("=" * 50)
        print(f"Original:        {original_time * 100000 / 3600:.1f} hours ({original_time * 100000 / 86400:.1f} days)")
        print(f"Optimized:       {optimized_time * 100000 / 3600:.1f} hours ({optimized_time * 100000 / 86400:.1f} days)")
        print(f"Ultra-optimized: {ultra_time * 100000 / 3600:.1f} hours ({ultra_time * 100000 / 86400:.1f} days)")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False

if __name__ == "__main__":
    success = performance_test()
    
    if success:
        print("\n🎉 Performance test completed successfully!")
    else:
        print("\n❌ Performance test failed.")
    
    sys.exit(0 if success else 1)
