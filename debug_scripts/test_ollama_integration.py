#!/usr/bin/env python3
"""
Test Ollama integration directly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_ollama_integration():
    """Test Ollama integration directly"""
    print("🧪 Testing Ollama Integration")
    print("=" * 50)
    
    try:
        from app.routes import get_config_value, generate_tracks_with_ollama
        
        # Check Ollama configuration
        print("1. Checking Ollama configuration...")
        ollama_url = get_config_value('OLLAMA', 'URL')
        ollama_model = get_config_value('OLLAMA', 'Model', 'gemma3:12b')
        
        print(f"   Ollama URL: {ollama_url}")
        print(f"   Ollama Model: {ollama_model}")
        
        if not ollama_url:
            print("❌ Ollama URL not configured!")
            return False
        
        # Test Ollama connectivity
        print("\n2. Testing Ollama connectivity...")
        try:
            import requests
            response = requests.get(f"{ollama_url}/api/tags", timeout=10)
            if response.status_code == 200:
                print("✅ Ollama is accessible")
                models = response.json().get('models', [])
                print(f"   Available models: {[m['name'] for m in models]}")
            else:
                print(f"❌ Ollama returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot connect to Ollama: {e}")
            return False
        
        # Test track generation
        print("\n3. Testing track generation...")
        test_prompt = "Suggest 5 songs similar to: 3 Doors Down - When I'm Gone\n\nUse random seed abc123 to ensure variety.\n\nReturn only Title and Artist, one per line."
        
        print(f"   Test prompt: {test_prompt[:100]}...")
        
        try:
            candidates = generate_tracks_with_ollama(ollama_url, ollama_model, test_prompt, 5, 0, [])
            if candidates:
                print(f"✅ Generated {len(candidates)} candidates:")
                for i, candidate in enumerate(candidates[:3]):
                    print(f"     {i+1}. {candidate}")
            else:
                print("❌ No candidates generated")
                return False
        except Exception as e:
            print(f"❌ Error generating tracks: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test candidate mapping
        print("\n4. Testing candidate mapping...")
        from app.routes import _map_candidates_to_local_with_features
        
        mapped = _map_candidates_to_local_with_features(candidates)
        print(f"   Mapped {len(mapped)} candidates to local tracks")
        
        if mapped:
            for i, track in enumerate(mapped[:3]):
                print(f"     {i+1}. {track['artist']} - {track['title']} (ID: {track['id']})")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ollama_integration()
    sys.exit(0 if success else 1)
