import asyncio
from mcp_server import mcp
import json

async def main():
    tools = await mcp.list_tools()
    print(json.dumps([t.model_dump(mode='json') for t in tools], indent=2))

if __name__ == "__main__":
    asyncio.run(main())
