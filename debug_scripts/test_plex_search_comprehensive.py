#!/usr/bin/env python3
"""
Comprehensive test script for Plex track search in MCP service.

This script tests various query patterns and compares MCP service results
with direct Plex API calls to identify gaps in the search logic.
"""
import sys
import os
import json
import requests
import configparser
from typing import List, Dict, Set, Tuple, Any
from collections import defaultdict

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mcp_server import search_tracks, _search_plex_tracks, get_config_value


class PlexSearchTester:
    """Test harness for comparing MCP search with direct Plex API calls."""
    
    def __init__(self):
        self.url = get_config_value('PLEX', 'ServerURL')
        self.token = get_config_value('PLEX', 'Token')
        self.section_id = get_config_value('PLEX', 'MusicSectionID')
        
        if not all([self.url, self.token, self.section_id]):
            raise ValueError("Plex not configured (URL, Token, or MusicSectionID missing)")
        
        self.headers = {'X-Plex-Token': self.token, 'Accept': 'application/json'}
        self.all_url = f"{self.url.rstrip('/')}/library/sections/{self.section_id}/all"
        self.search_url = f"{self.url.rstrip('/')}/library/sections/{self.section_id}/search"
        
        self.results = []
    
    def query_plex_direct(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Query Plex API directly using multiple strategies."""
        all_results = []
        seen_ids = set()
        
        # Strategy 1: General text search
        try:
            params = {'type': '10', 'query': query, 'X-Plex-Token': self.token}
            response = requests.get(self.search_url, headers=self.headers, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            tracks = data.get('MediaContainer', {}).get('Metadata', [])
            for track in tracks[:limit]:
                track_id = track.get('ratingKey')
                if track_id and track_id not in seen_ids:
                    seen_ids.add(track_id)
                    all_results.append({
                        'id': str(track_id),
                        'title': track.get('title', ''),
                        'artist': track.get('grandparentTitle', ''),
                        'album': track.get('parentTitle', ''),
                        'source': 'general_search'
                    })
        except Exception as e:
            print(f"  Direct API general search failed: {e}")
        
        # Strategy 2: Search for artist, then get all tracks
        try:
            artist_params = {'type': '8', 'query': query, 'X-Plex-Token': self.token}
            response = requests.get(self.search_url, headers=self.headers, params=artist_params, timeout=10)
            response.raise_for_status()
            data = response.json()
            artists = data.get('MediaContainer', {}).get('Metadata', [])
            
            query_lower = query.lower().strip()
            for artist in artists:
                artist_title = artist.get('title', '').lower()
                if artist_title == query_lower or query_lower in artist_title or artist_title in query_lower:
                    artist_id = artist.get('ratingKey')
                    if artist_id:
                        track_params = {'type': '10', 'artist.id': artist_id, 'X-Plex-Token': self.token}
                        response = requests.get(self.all_url, headers=self.headers, params=track_params, timeout=5)
                        response.raise_for_status()
                        data = response.json()
                        tracks = data.get('MediaContainer', {}).get('Metadata', [])
                        for track in tracks[:limit]:
                            track_id = track.get('ratingKey')
                            if track_id and track_id not in seen_ids:
                                seen_ids.add(track_id)
                                all_results.append({
                                    'id': str(track_id),
                                    'title': track.get('title', ''),
                                    'artist': track.get('grandparentTitle', ''),
                                    'album': track.get('parentTitle', ''),
                                    'source': 'artist_search'
                                })
        except Exception as e:
            print(f"  Direct API artist search failed: {e}")
        
        # Strategy 3: Filter by artist name directly
        try:
            params = {'type': '10', 'grandparentTitle': query, 'X-Plex-Token': self.token}
            response = requests.get(self.all_url, headers=self.headers, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            tracks = data.get('MediaContainer', {}).get('Metadata', [])
            for track in tracks[:limit]:
                track_id = track.get('ratingKey')
                if track_id and track_id not in seen_ids:
                    seen_ids.add(track_id)
                    all_results.append({
                        'id': str(track_id),
                        'title': track.get('title', ''),
                        'artist': track.get('grandparentTitle', ''),
                        'album': track.get('parentTitle', ''),
                        'source': 'artist_filter'
                    })
        except Exception as e:
            print(f"  Direct API artist filter failed: {e}")
        
        # Strategy 4: Filter by title
        try:
            params = {'type': '10', 'title': query, 'X-Plex-Token': self.token}
            response = requests.get(self.all_url, headers=self.headers, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            tracks = data.get('MediaContainer', {}).get('Metadata', [])
            for track in tracks[:limit]:
                track_id = track.get('ratingKey')
                if track_id and track_id not in seen_ids:
                    seen_ids.add(track_id)
                    all_results.append({
                        'id': str(track_id),
                        'title': track.get('title', ''),
                        'artist': track.get('grandparentTitle', ''),
                        'album': track.get('parentTitle', ''),
                        'source': 'title_filter'
                    })
        except Exception as e:
            print(f"  Direct API title filter failed: {e}")
        
        return all_results[:limit]
    
    def query_mcp_service(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Query using MCP service search_tracks function."""
        try:
            result_str = search_tracks(query=query, limit=limit)
            if result_str.startswith("Error:"):
                return []
            tracks = json.loads(result_str)
            if isinstance(tracks, list):
                return tracks
            return []
        except Exception as e:
            print(f"  MCP service query failed: {e}")
            return []
    
    def normalize_track(self, track: Dict[str, Any]) -> Tuple[str, str, str]:
        """Normalize track for comparison."""
        track_id = str(track.get('id', ''))
        title = (track.get('title') or '').lower().strip()
        artist = (track.get('artist') or '').lower().strip()
        return (track_id, title, artist)
    
    def compare_results(self, query: str, plex_results: List[Dict], mcp_results: List[Dict]) -> Dict[str, Any]:
        """Compare Plex direct results with MCP service results."""
        # Normalize results for comparison
        plex_set = {self.normalize_track(t) for t in plex_results}
        mcp_set = {self.normalize_track(t) for t in mcp_results}
        
        # Find missing tracks (in Plex but not in MCP)
        missing = plex_set - mcp_set
        missing_tracks = [t for t in plex_results if self.normalize_track(t) in missing]
        
        # Find false positives (in MCP but not in Plex)
        false_positives = mcp_set - plex_set
        false_positive_tracks = [t for t in mcp_results if self.normalize_track(t) in false_positives]
        
        # Find common tracks
        common = plex_set & mcp_set
        
        return {
            'query': query,
            'plex_count': len(plex_results),
            'mcp_count': len(mcp_results),
            'common_count': len(common),
            'missing_count': len(missing),
            'false_positive_count': len(false_positives),
            'missing_tracks': missing_tracks[:10],  # Limit for readability
            'false_positive_tracks': false_positive_tracks[:10],
            'success_rate': len(common) / len(plex_results) * 100 if plex_results else 0
        }
    
    def test_query(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """Test a single query and return comparison results."""
        print(f"\n{'='*80}")
        print(f"Testing query: '{query}'")
        print(f"{'='*80}")
        
        print("  Querying Plex API directly...")
        plex_results = self.query_plex_direct(query, limit)
        print(f"  Plex API found {len(plex_results)} tracks")
        
        print("  Querying MCP service...")
        mcp_results = self.query_mcp_service(query, limit)
        print(f"  MCP service found {len(mcp_results)} tracks")
        
        comparison = self.compare_results(query, plex_results, mcp_results)
        
        print(f"\n  Results:")
        print(f"    Plex API: {comparison['plex_count']} tracks")
        print(f"    MCP Service: {comparison['mcp_count']} tracks")
        print(f"    Common: {comparison['common_count']} tracks")
        print(f"    Missing from MCP: {comparison['missing_count']} tracks")
        print(f"    False positives in MCP: {comparison['false_positive_count']} tracks")
        print(f"    Success rate: {comparison['success_rate']:.1f}%")
        
        if comparison['missing_count'] > 0:
            print(f"\n  Missing tracks (first {min(10, comparison['missing_count'])}):")
            for track in comparison['missing_tracks']:
                print(f"    - '{track.get('title')}' by '{track.get('artist')}' (ID: {track.get('id')})")
        
        if comparison['false_positive_count'] > 0:
            print(f"\n  False positives (first {min(10, comparison['false_positive_count'])}):")
            for track in comparison['false_positive_tracks']:
                print(f"    - '{track.get('title')}' by '{track.get('artist')}' (ID: {track.get('id')})")
        
        return comparison
    
    def run_all_tests(self):
        """Run comprehensive test suite."""
        print("="*80)
        print("COMPREHENSIVE PLEX SEARCH TEST SUITE")
        print("="*80)
        
        # Test queries organized by category (reduced set for faster testing)
        test_queries = {
            'Artist Names': [
                'Oasis',
                'The Beatles',
                'Red Hot Chili Peppers',
            ],
            'Song Titles': [
                'Wonderwall',
                'Stairway to Heaven',
            ],
            'Combined Queries (LLM-style)': [
                'Wonderwall Oasis',
                'Scar Tissue Red Hot Chili Peppers',
            ],
            'Partial Matches': [
                'Beatles',
                'RHCP',
            ],
            'Case Variations': [
                'oasis',
                'OASIS',
                'Oasis',
            ],
            'Special Characters': [
                'R.E.M.',
                'AC/DC',
            ],
            'Multi-word Queries': [
                'Red Hot Chili Peppers',
                'Pink Floyd',
            ],
            'Edge Cases': [
                'rock',  # Genre-like
                'jazz',  # Genre
            ]
        }
        
        all_results = []
        
        for category, queries in test_queries.items():
            print(f"\n\n{'#'*80}")
            print(f"# {category}")
            print(f"{'#'*80}")
            
            for query in queries:
                if query == '':  # Skip empty query
                    continue
                try:
                    result = self.test_query(query, limit=20)  # Reduced limit for faster testing
                    result['category'] = category
                    all_results.append(result)
                except Exception as e:
                    print(f"  ERROR testing '{query}': {e}")
                    all_results.append({
                        'query': query,
                        'category': category,
                        'error': str(e),
                        'plex_count': 0,
                        'mcp_count': 0,
                        'success_rate': 0
                    })
        
        # Generate summary report
        self.generate_report(all_results)
        
        return all_results
    
    def generate_report(self, results: List[Dict[str, Any]]):
        """Generate a detailed summary report."""
        print("\n\n" + "="*80)
        print("SUMMARY REPORT")
        print("="*80)
        
        # Overall statistics
        total_tests = len([r for r in results if 'error' not in r])
        total_queries = len(results)
        successful_queries = len([r for r in results if r.get('success_rate', 0) == 100])
        partial_success = len([r for r in results if 0 < r.get('success_rate', 0) < 100])
        failed_queries = len([r for r in results if r.get('success_rate', 0) == 0 and 'error' not in r])
        
        print(f"\nOverall Statistics:")
        print(f"  Total queries tested: {total_queries}")
        print(f"  Successful (100% match): {successful_queries}")
        print(f"  Partial success: {partial_success}")
        print(f"  Failed (0% match): {failed_queries}")
        print(f"  Errors: {total_queries - total_tests}")
        
        # Statistics by category
        print(f"\nStatistics by Category:")
        by_category = defaultdict(list)
        for result in results:
            if 'category' in result:
                by_category[result['category']].append(result)
        
        for category, cat_results in by_category.items():
            cat_total = len(cat_results)
            cat_success = len([r for r in cat_results if r.get('success_rate', 0) == 100])
            cat_avg_rate = sum(r.get('success_rate', 0) for r in cat_results) / cat_total if cat_total > 0 else 0
            print(f"  {category}:")
            print(f"    Total: {cat_total}, 100% success: {cat_success}, Avg success rate: {cat_avg_rate:.1f}%")
        
        # Worst performing queries
        print(f"\nWorst Performing Queries (by success rate):")
        sorted_results = sorted([r for r in results if 'success_rate' in r], 
                               key=lambda x: x.get('success_rate', 0))
        for result in sorted_results[:10]:
            print(f"  '{result['query']}' ({result.get('category', 'Unknown')}): "
                  f"{result.get('success_rate', 0):.1f}% "
                  f"(Plex: {result.get('plex_count', 0)}, MCP: {result.get('mcp_count', 0)}, "
                  f"Missing: {result.get('missing_count', 0)})")
        
        # Queries with most missing tracks
        print(f"\nQueries with Most Missing Tracks:")
        sorted_by_missing = sorted([r for r in results if 'missing_count' in r], 
                                   key=lambda x: x.get('missing_count', 0), reverse=True)
        for result in sorted_by_missing[:10]:
            if result.get('missing_count', 0) > 0:
                print(f"  '{result['query']}' ({result.get('category', 'Unknown')}): "
                      f"{result.get('missing_count', 0)} missing tracks "
                      f"(Plex: {result.get('plex_count', 0)}, MCP: {result.get('mcp_count', 0)})")
        
        # Pattern analysis
        print(f"\nPattern Analysis:")
        artist_queries = [r for r in results if r.get('category') == 'Artist Names']
        song_queries = [r for r in results if r.get('category') == 'Song Titles']
        combined_queries = [r for r in results if r.get('category') == 'Combined Queries (LLM-style)']
        
        if artist_queries:
            avg_artist_rate = sum(r.get('success_rate', 0) for r in artist_queries) / len(artist_queries)
            print(f"  Artist name queries: {avg_artist_rate:.1f}% average success rate")
        
        if song_queries:
            avg_song_rate = sum(r.get('success_rate', 0) for r in song_queries) / len(song_queries)
            print(f"  Song title queries: {avg_song_rate:.1f}% average success rate")
        
        if combined_queries:
            avg_combined_rate = sum(r.get('success_rate', 0) for r in combined_queries) / len(combined_queries)
            print(f"  Combined queries (LLM-style): {avg_combined_rate:.1f}% average success rate")


def main():
    """Main entry point."""
    try:
        tester = PlexSearchTester()
        results = tester.run_all_tests()
        
        # Save results to JSON file
        output_file = os.path.join(os.path.dirname(__file__), '..', 'notes', 'plex_search_test_results.json')
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n\nDetailed results saved to: {output_file}")
        
        return 0
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

