"""
FastMCP server definition for BeerSmith.
"""

from fastmcp import FastMCP

from mcp_beersmith.tools import register_tools
from mcp_beersmith.config import get_config

# Create the MCP server
mcp = FastMCP(
    "mcp-beersmith",
    description="BeerSmith recipe and ingredient integration",
)

# Register all tools
register_tools(mcp)
