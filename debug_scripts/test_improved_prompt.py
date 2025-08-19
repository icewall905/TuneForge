#!/usr/bin/env python3
"""
Test the improved Ollama prompt
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_improved_prompt():
    """Test the improved prompt"""
    print("🧪 Testing Improved Ollama Prompt")
    print("=" * 50)
    
    try:
        from app.routes import _build_adaptive_prompt, generate_tracks_with_ollama, get_config_value
        
        # Create a mock job for testing
        class MockJob:
            def __init__(self):
                self.random_seed = "test123"
                self.accepted_examples = []
                self.rejected_examples = []
                self.iteration_history = []
        
        mock_job = MockJob()
        
        # Test prompt building
        print("1. Testing improved prompt building...")
        prompt = _build_adaptive_prompt(mock_job, "3 Doors Down - When I'm Gone", 5, set())
        
        print("Generated prompt:")
        print("-" * 50)
        print(prompt)
        print("-" * 50)
        
        # Check if prompt contains key elements
        checks = [
            ("random seed", "random seed" in prompt.lower()),
            ("genre guidance", "genre" in prompt.lower()),
            ("rock focus", "rock" in prompt.lower()),
            ("avoid electronic", "electronic" in prompt.lower()),
            ("return format", "return only title and artist" in prompt.lower())
        ]
        
        print("\nPrompt quality checks:")
        for check_name, passed in checks:
            status = "✅" if passed else "❌"
            print(f"  {status} {check_name}")
        
        # Test with Ollama
        print("\n2. Testing with Ollama...")
        ollama_url = get_config_value('OLLAMA', 'URL')
        ollama_model = get_config_value('OLLAMA', 'Model', 'gemma3:12b')
        
        if not ollama_url:
            print("❌ Ollama URL not configured!")
            return False
        
        try:
            candidates = generate_tracks_with_ollama(ollama_url, ollama_model, prompt, 5, 0, [])
            if candidates:
                print(f"✅ Generated {len(candidates)} candidates:")
                for i, candidate in enumerate(candidates):
                    print(f"     {i+1}. {candidate}")
                
                # Test mapping
                print("\n3. Testing candidate mapping...")
                from app.routes import _map_candidates_to_local_with_features
                
                mapped = _map_candidates_to_local_with_features(candidates)
                print(f"   Mapped {len(mapped)} candidates to local tracks")
                
                if mapped:
                    for i, track in enumerate(mapped[:3]):
                        print(f"     {i+1}. {track['artist']} - {track['title']} (ID: {track['id']})")
                else:
                    print("   ⚠️  Still no matches - candidates may be too specific")
                    
            else:
                print("❌ No candidates generated")
                return False
                
        except Exception as e:
            print(f"❌ Error generating tracks: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_improved_prompt()
    sys.exit(0 if success else 1)
