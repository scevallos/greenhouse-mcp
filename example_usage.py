#!/usr/bin/env python3
"""
Example usage of the Greenhouse MCP server tools.
This demonstrates how to interact with the server programmatically.
"""

import asyncio
import os

from src.greenhouse_mcp import mcp


async def example_usage():
    """Example of using the Greenhouse MCP tools."""

    print("Greenhouse MCP Server - Example Usage\n")
    print("=" * 50)

    # Ensure API key is set
    if not os.getenv("GREENHOUSE_API_KEY"):
        print("❌ Please set GREENHOUSE_API_KEY in your .env file")
        return

    # Get available tools
    tools = await mcp.get_tools()
    print(f"\n📦 Available tools ({len(tools)}):")
    for tool in tools:
        tool_name = tool if isinstance(tool, str) else tool.name
        print(f"  - {tool_name}")

    print("\n" + "=" * 50)
    print("\n✅ Server is ready to use!")
    print("\nYou can now:")
    print("1. Run the server: python -m src.greenhouse_mcp")
    print("2. Connect it to Claude Desktop or other MCP clients")
    print("3. Use natural language to interact with Greenhouse")

    print("\nExample prompts you can use:")
    print("- 'List all open engineering jobs'")
    print("- 'Show candidates who applied this week'")
    print("- 'Get details for candidate ID 12345'")
    print("- 'Add a note to application 67890'")
    print("- 'Advance application 11111 to next stage'")


if __name__ == "__main__":
    asyncio.run(example_usage())
