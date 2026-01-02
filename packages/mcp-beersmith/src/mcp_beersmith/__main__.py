"""
MCP server entry point for BeerSmith integration.

Run with: python -m mcp_beersmith
"""

# Suppress Pydantic deprecation warnings BEFORE any imports
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import sys

try:
    import sys
    print("[BEERSMITH] Importing server module...", file=sys.stderr, flush=True)
    from mcp_beersmith.server import mcp
    
    if __name__ == "__main__":
        print("[BEERSMITH] Starting MCP server...", file=sys.stderr, flush=True)
        print(f"[BEERSMITH] stdin isatty: {sys.stdin.isatty()}", file=sys.stderr, flush=True)
        print(f"[BEERSMITH] stdout isatty: {sys.stdout.isatty()}", file=sys.stderr, flush=True)
        # Let FastMCP auto-detect transport
        mcp.run(show_banner=False)
        print("[BEERSMITH] Server exited normally", file=sys.stderr, flush=True)
except Exception as e:
    print(f"Fatal error starting BeerSmith MCP: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
