#!/usr/bin/env python3
"""
MCP Server wrapper for stdio transport (for Cursor IDE).
This allows Cursor to connect via stdio while keeping HTTP streamable for n8n.
"""
import sys
import asyncio
from mcp_server import mcp

async def main():
    """Run the MCP server in stdio mode"""
    await mcp.run_stdio_async()

if __name__ == "__main__":
    asyncio.run(main())

