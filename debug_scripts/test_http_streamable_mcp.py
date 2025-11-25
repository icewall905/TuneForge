#!/usr/bin/env python3
"""
Test script to verify HTTP streamable MCP connection (same as n8n would use).
This tests the /mcp endpoint that n8n will connect to.
"""
import sys
import os
sys.path.insert(0, '/opt/tuneforge')

import requests
import json
import time

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_section(title):
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{title:^70}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

def print_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}✗ {msg}{RESET}")

def print_info(msg):
    print(f"  {msg}")

def test_http_streamable_connection(base_url="http://localhost:8000"):
    """Test HTTP streamable MCP connection"""
    print_section("Testing HTTP Streamable MCP Connection")
    
    mcp_endpoint = f"{base_url}/mcp"
    sse_endpoint = f"{base_url}/sse"
    
    print_info(f"MCP Endpoint: {mcp_endpoint}")
    print_info(f"SSE Endpoint: {sse_endpoint}")
    
    # Test 1: Check if server is running
    print_info("\n1. Checking if MCP server is running...")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print_success(f"Server is running (status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to server. Is it running?")
        print_info("Start it with: cd /opt/tuneforge && ./start_mcp.sh")
        return False
    except Exception as e:
        print_error(f"Error connecting: {e}")
        return False
    
    # Test 2: Check MCP endpoint
    print_info("\n2. Testing MCP endpoint...")
    try:
        # MCP HTTP streamable uses POST for messages
        # First, let's try to get the server info
        response = requests.post(
            mcp_endpoint,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                }
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            print_success(f"MCP endpoint responded (status: {response.status_code})")
            try:
                data = response.json()
                print_info(f"Response: {json.dumps(data, indent=2)[:200]}...")
            except:
                print_info(f"Response text: {response.text[:200]}...")
        else:
            print_error(f"MCP endpoint returned status {response.status_code}")
            print_info(f"Response: {response.text[:200]}...")
    except Exception as e:
        print_error(f"Error testing MCP endpoint: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Check SSE endpoint
    print_info("\n3. Testing SSE endpoint...")
    try:
        response = requests.get(
            sse_endpoint,
            headers={"Accept": "text/event-stream"},
            timeout=5,
            stream=True
        )
        if response.status_code == 200:
            print_success(f"SSE endpoint is accessible (status: {response.status_code})")
            # Read a few lines to see if it's streaming
            lines_read = 0
            for line in response.iter_lines():
                if line:
                    print_info(f"SSE data: {line.decode()[:100]}...")
                    lines_read += 1
                    if lines_read >= 2:
                        break
        else:
            print_error(f"SSE endpoint returned status {response.status_code}")
    except Exception as e:
        print_error(f"Error testing SSE endpoint: {e}")
    
    # Test 4: List tools (MCP protocol)
    print_info("\n4. Testing tool listing via MCP protocol...")
    try:
        response = requests.post(
            mcp_endpoint,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "result" in data and "tools" in data["result"]:
                tools = data["result"]["tools"]
                print_success(f"Found {len(tools)} tools:")
                for tool in tools:
                    print_info(f"  - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')[:50]}...")
            else:
                print_info(f"Response: {json.dumps(data, indent=2)[:300]}...")
        else:
            print_error(f"Tool listing returned status {response.status_code}")
    except Exception as e:
        print_error(f"Error listing tools: {e}")
    
    print_section("HTTP Streamable Test Complete")
    print_info("This is how n8n will connect to the MCP server.")
    print_info(f"n8n Configuration:")
    print_info(f"  - Transport: HTTP Streamable")
    print_info(f"  - Server URL: {mcp_endpoint}")
    
    return True

if __name__ == "__main__":
    import sys
    
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    print_section("HTTP Streamable MCP Connection Test")
    print_info(f"Testing connection to: {base_url}")
    print_info("This emulates how n8n will connect to the MCP service")
    
    test_http_streamable_connection(base_url)

