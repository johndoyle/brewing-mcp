"""
MCP server entry point for BeerSmith integration.

Run with: python -m mcp_beersmith
"""

from mcp_beersmith.server import mcp

if __name__ == "__main__":
    mcp.run()
