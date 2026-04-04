"""FastMCP server definition for BeerSmith 4."""

from fastmcp import FastMCP

from mcp_beersmith4.tools import register_tools

mcp = FastMCP(
    "mcp-beersmith4",
    instructions=(
        "BeerSmith 4 recipe and ingredient integration. "
        "Read and write BeerSmith 4 SQLite databases directly. "
        "Supports recipe browsing, searching, ingredient libraries, "
        "and creating/updating recipes."
    ),
)

register_tools(mcp)
