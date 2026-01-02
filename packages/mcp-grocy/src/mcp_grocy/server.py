"""
FastMCP server definition for Grocy.
"""

from fastmcp import FastMCP

from mcp_grocy.tools import register_tools

# Create the MCP server
mcp = FastMCP(
    "mcp-grocy",
    instructions="Grocy inventory and stock management",
)

# Register all tools
register_tools(mcp)
