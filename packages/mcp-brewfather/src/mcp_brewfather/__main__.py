"""
MCP server entry point for Brewfather integration.

Run with: python -m mcp_brewfather
"""

from mcp_brewfather.server import mcp

if __name__ == "__main__":
    mcp.run()
