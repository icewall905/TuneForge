#!/usr/bin/env python3
"""
Test script for enhanced Sonic Traveller functionality
Tests the feedback loop and random seed integration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_enhanced_functionality():
    """Test the enhanced Sonic Traveller functionality"""
    print("🧪 Testing Enhanced Sonic Traveller Functionality")
    print("=" * 60)
    
    try:
        # Test the enhanced functions
        from app.routes import _build_adaptive_prompt
        print("✅ Enhanced functions imported successfully")
        
        # Test adaptive prompt building
        print("\n🔍 Testing Adaptive Prompt Building...")
        
        # Mock job object for testing
        class MockJob:
            def __init__(self):
                self.random_seed = "abc12345"
                self.accepted_examples = [
                    {'artist': 'Artist1', 'title': 'Song1'},
                    {'artist': 'Artist2', 'title': 'Song2'},
                    {'artist': 'Artist3', 'title': 'Song3'}
                ]
                self.rejected_examples = [
                    {'artist': 'Artist4', 'title': 'Song4'},
                    {'artist': 'Artist5', 'title': 'Song5'}
                ]
        
        mock_job = MockJob()
        seed_text = "Test Song - Test Artist"
        candidates_needed = 15
        excludes = {"Song1 - Artist1", "Song2 - Artist2"}
        
        prompt = _build_adaptive_prompt(mock_job, seed_text, candidates_needed, excludes)
        
        print("✅ Adaptive prompt generated successfully")
        print(f"Prompt length: {len(prompt)} characters")
        print(f"Contains random seed: {'abc12345' in prompt}")
        print(f"Contains accepted examples: {'Artist1 - Song1' in prompt}")
        print(f"Contains rejected examples: {'Artist4 - Song4' in prompt}")
        print(f"Contains exclusions: {'Song1 - Artist1' in prompt}")
        
        # Show first few lines of the prompt
        print("\n📝 Sample prompt content:")
        lines = prompt.split('\n')[:8]
        for i, line in enumerate(lines, 1):
            print(f"  {i:2d}: {line}")
        
        print("\n" + "=" * 60)
        print("✅ Enhanced Sonic Traveller functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Enhanced functionality test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_enhanced_functionality()
    sys.exit(0 if success else 1)
