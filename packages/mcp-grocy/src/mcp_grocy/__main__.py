"""
MCP server entry point for Grocy integration.

Run with: python -m mcp_grocy
"""

import warnings

# Suppress deprecation warnings that can interfere with MCP protocol
warnings.filterwarnings("ignore", category=DeprecationWarning)

import sys

try:
    import sys
    print("[GROCY] Importing server module...", file=sys.stderr, flush=True)
    from mcp_grocy.server import mcp
    
    if __name__ == "__main__":
        print("[GROCY] Starting MCP server...", file=sys.stderr, flush=True)
        print(f"[GROCY] stdin isatty: {sys.stdin.isatty()}", file=sys.stderr, flush=True)
        print(f"[GROCY] stdout isatty: {sys.stdout.isatty()}", file=sys.stderr, flush=True)
        # Let FastMCP auto-detect transport
        mcp.run(show_banner=False)
        print("[GROCY] Server exited normally", file=sys.stderr, flush=True)
except Exception as e:
    print(f"Fatal error starting Grocy MCP: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
