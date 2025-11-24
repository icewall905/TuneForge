#!/usr/bin/env python3
"""
Quick test script to verify AudioAnalyzer fixes.
"""

import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

def quick_test():
    """Quick test of the fixed AudioAnalyzer"""
    try:
        from audio_analyzer import AudioAnalyzer
        
        # Create analyzer
        analyzer = AudioAnalyzer()
        print(f"✅ AudioAnalyzer created with sample rate: {analyzer.sample_rate} Hz")
        
        # Test file
        test_file = "/home/hnyg/Music/3 Doors Down/3 Doors Down - Away From The Sun/01 - When I'm Gone.flac"
        
        print(f"\n🎵 Testing file: {Path(test_file).name}")
        
        # Extract features
        features = analyzer.extract_all_features(test_file)
        
        if features['success']:
            print("✅ Feature extraction successful!")
            print("\n📊 Extracted features:")
            for key, value in features['features'].items():
                if value is not None:
                    if isinstance(value, float):
                        print(f"   - {key}: {value:.3f}")
                    else:
                        print(f"   - {key}: {value}")
        else:
            print(f"❌ Feature extraction failed: {features['error_message']}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Quick AudioAnalyzer Test")
    print("=" * 40)
    
    success = quick_test()
    
    if success:
        print("\n🎉 Quick test passed! Fixes are working.")
    else:
        print("\n❌ Quick test failed.")
    
    sys.exit(0 if success else 1)
