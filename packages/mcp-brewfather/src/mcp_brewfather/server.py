"""
FastMCP server definition for Brewfather.
"""

from fastmcp import FastMCP

from mcp_brewfather.tools import register_tools

# Create the MCP server
mcp = FastMCP(
    "mcp-brewfather",
    description="Brewfather recipe and batch tracking",
)

# Register all tools
register_tools(mcp)
