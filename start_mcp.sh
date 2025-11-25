#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo "Starting TuneForge MCP Server on port 8000..."
python mcp_server.py
