"""
MCP server entry point for BeerSmith 4 integration.

Run with: python -m mcp_beersmith4
"""

import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

import sys

try:
    from mcp_beersmith4.server import mcp

    if __name__ == "__main__":
        print("[BEERSMITH4] Starting MCP server...", file=sys.stderr, flush=True)
        mcp.run(show_banner=False)
        print("[BEERSMITH4] Server exited normally", file=sys.stderr, flush=True)
except Exception as e:
    print(f"Fatal error starting BeerSmith4 MCP: {e}", file=sys.stderr)
    import traceback

    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
