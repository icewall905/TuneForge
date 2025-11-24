#!/usr/bin/env python3
"""
Test script for local search functionality
"""

import requests
import json

def test_local_search():
    """Test the local search API endpoint"""
    base_url = "http://localhost:5395"
    
    # Test queries
    test_queries = [
        "love",
        "test", 
        "rock",
        "pop",
        "a",  # Single character (should return empty)
        "ab", # Two characters (should work)
        "the", # Common word
        "doors" # Artist name
    ]
    
    print("🔍 Testing Local Search API")
    print("=" * 40)
    
    for query in test_queries:
        try:
            url = f"{base_url}/api/local-search?q={query}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                results = response.json()
                print(f"✅ Query '{query}': {len(results)} results")
                
                # Show first 2 results
                for i, result in enumerate(results[:2]):
                    print(f"   {i+1}. {result.get('artist', 'Unknown')} - {result.get('title', 'Unknown')}")
                
                if len(results) > 2:
                    print(f"   ... and {len(results) - 2} more")
                    
            else:
                print(f"❌ Query '{query}': HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ Query '{query}': Error - {e}")
        
        print()
    
    print("=" * 40)
    print("Search test completed!")

if __name__ == "__main__":
    test_local_search()
