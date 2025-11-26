#!/usr/bin/env python3
"""
Test script for bulk_search_tracks MCP tool.
Tests bulk search functionality with multiple queries on both Plex and Navidrome.
"""

import sys
import os
import json

# Add parent directory to path to import mcp_server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server import bulk_search_tracks

def test_bulk_search_plex():
    """Test bulk search on Plex"""
    print("=" * 60)
    print("Testing bulk_search_tracks on Plex")
    print("=" * 60)
    
    queries = [
        "Oasis",
        "Wonderwall",
        "The Beatles",
        "Stairway to Heaven",
        "Jazz",
        "Rock",
        "Electronic",
        "Classical",
        "Blues",
        "Folk"
    ]
    
    print(f"\nSearching for {len(queries)} queries:")
    for i, q in enumerate(queries, 1):
        print(f"  {i}. {q}")
    
    print(f"\nCalling bulk_search_tracks with limit=50...")
    result = bulk_search_tracks(queries=queries, platform="plex", limit=50)
    
    try:
        data = json.loads(result)
        if "error" in data:
            print(f"\nERROR: {data['error']}")
            return False
        
        if "results" in data:
            results = data["results"]
            total_tracks = 0
            print(f"\nResults grouped by query:")
            for query, tracks in results.items():
                print(f"\n  Query: '{query}'")
                print(f"    Found {len(tracks)} track(s)")
                total_tracks += len(tracks)
                # Show first 3 tracks as examples
                for i, track in enumerate(tracks[:3], 1):
                    print(f"      {i}. {track.get('title', 'N/A')} by {track.get('artist', 'N/A')} (ID: {track.get('id', 'N/A')})")
                if len(tracks) > 3:
                    print(f"      ... and {len(tracks) - 3} more")
            
            print(f"\nTotal tracks found: {total_tracks}")
            
            if "errors" in data:
                print(f"\nErrors encountered:")
                for query, error in data["errors"].items():
                    print(f"  '{query}': {error}")
            
            return True
        else:
            print(f"\nUnexpected response format: {result}")
            return False
            
    except json.JSONDecodeError as e:
        print(f"\nERROR: Failed to parse JSON response: {e}")
        print(f"Response: {result}")
        return False

def test_bulk_search_navidrome():
    """Test bulk search on Navidrome"""
    print("\n" + "=" * 60)
    print("Testing bulk_search_tracks on Navidrome")
    print("=" * 60)
    
    queries = [
        "Oasis",
        "Wonderwall",
        "The Beatles",
        "Jazz",
        "Rock"
    ]
    
    print(f"\nSearching for {len(queries)} queries:")
    for i, q in enumerate(queries, 1):
        print(f"  {i}. {q}")
    
    print(f"\nCalling bulk_search_tracks with limit=30...")
    result = bulk_search_tracks(queries=queries, platform="navidrome", limit=30)
    
    try:
        data = json.loads(result)
        if "error" in data:
            print(f"\nERROR: {data['error']}")
            return False
        
        if "results" in data:
            results = data["results"]
            total_tracks = 0
            print(f"\nResults grouped by query:")
            for query, tracks in results.items():
                print(f"\n  Query: '{query}'")
                print(f"    Found {len(tracks)} track(s)")
                total_tracks += len(tracks)
                # Show first 3 tracks as examples
                for i, track in enumerate(tracks[:3], 1):
                    print(f"      {i}. {track.get('title', 'N/A')} by {track.get('artist', 'N/A')} (ID: {track.get('id', 'N/A')})")
                if len(tracks) > 3:
                    print(f"      ... and {len(tracks) - 3} more")
            
            print(f"\nTotal tracks found: {total_tracks}")
            
            if "errors" in data:
                print(f"\nErrors encountered:")
                for query, error in data["errors"].items():
                    print(f"  '{query}': {error}")
            
            return True
        else:
            print(f"\nUnexpected response format: {result}")
            return False
            
    except json.JSONDecodeError as e:
        print(f"\nERROR: Failed to parse JSON response: {e}")
        print(f"Response: {result}")
        return False

def test_limit_enforcement():
    """Test that total limit is properly enforced"""
    print("\n" + "=" * 60)
    print("Testing limit enforcement")
    print("=" * 60)
    
    queries = ["Rock", "Jazz", "Electronic", "Classical", "Blues"]
    limit = 10
    
    print(f"\nSearching for {len(queries)} queries with total limit={limit}...")
    result = bulk_search_tracks(queries=queries, platform="plex", limit=limit)
    
    try:
        data = json.loads(result)
        if "error" in data:
            print(f"\nERROR: {data['error']}")
            return False
        
        if "results" in data:
            results = data["results"]
            total_tracks = sum(len(tracks) for tracks in results.values())
            
            print(f"\nTotal tracks found: {total_tracks}")
            print(f"Limit specified: {limit}")
            
            if total_tracks <= limit:
                print("✓ Limit properly enforced!")
                return True
            else:
                print(f"✗ ERROR: Total tracks ({total_tracks}) exceeds limit ({limit})")
                return False
        else:
            print(f"\nUnexpected response format: {result}")
            return False
            
    except json.JSONDecodeError as e:
        print(f"\nERROR: Failed to parse JSON response: {e}")
        print(f"Response: {result}")
        return False

if __name__ == "__main__":
    print("Bulk Search MCP Tool Test")
    print("=" * 60)
    
    results = []
    
    # Test Plex
    results.append(("Plex", test_bulk_search_plex()))
    
    # Test Navidrome
    results.append(("Navidrome", test_bulk_search_navidrome()))
    
    # Test limit enforcement
    results.append(("Limit Enforcement", test_limit_enforcement()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    sys.exit(0 if all_passed else 1)

