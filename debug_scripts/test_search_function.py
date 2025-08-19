#!/usr/bin/env python3
"""
Test script for the search_local_tracks function directly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_search_function():
    """Test the search function directly"""
    print("🔍 Testing search_local_tracks function directly")
    print("=" * 50)
    
    try:
        # Import the function
        from app.routes import search_local_tracks
        print("✅ Function imported successfully")
        
        # Test queries
        test_queries = [
            "love",
            "test",
            "rock",
            "a",
            "ab",
            "the",
            "doors"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing query: '{query}'")
            try:
                results = search_local_tracks(query, limit=5)
                print(f"   Results: {len(results)}")
                
                if results:
                    for i, result in enumerate(results[:3]):
                        print(f"   {i+1}. {result.get('artist', 'Unknown')} - {result.get('title', 'Unknown')}")
                    if len(results) > 3:
                        print(f"   ... and {len(results) - 3} more")
                else:
                    print("   No results")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        print("\n" + "=" * 50)
        print("✅ Search function test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to import or test function: {e}")
        return False

if __name__ == "__main__":
    success = test_search_function()
    sys.exit(0 if success else 1)
