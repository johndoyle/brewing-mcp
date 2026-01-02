"""
MCP server entry point for Grocy integration.

Run with: python -m mcp_grocy
"""

from mcp_grocy.server import mcp

if __name__ == "__main__":
    mcp.run()
