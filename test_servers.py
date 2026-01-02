#!/usr/bin/env python3
"""
Test script to verify both MCP servers work correctly.
"""

import json
import subprocess
import sys

def test_server(package: str, env: dict = None):
    """Test an MCP server by sending an initialize message."""
    print(f"\nTesting {package}...")
    
    # MCP initialize message
    init_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"}
        }
    }
    
    try:
        # Run the server with the initialize message
        cmd = ["uv", "run", "--package", package, "python", "-m", package.replace("-", "_")]
        result = subprocess.run(
            cmd,
            input=json.dumps(init_msg).encode(),
            capture_output=True,
            timeout=5,
            env={**subprocess.os.environ, "PYTHONWARNINGS": "ignore", **(env or {})}
        )
        
        # Parse the output - look for JSON response
        output = result.stdout.decode()
        
        # Find the JSON response in the output
        for line in output.split('\n'):
            if line.strip().startswith('{'):
                try:
                    response = json.loads(line)
                    if response.get('id') == 1 and 'result' in response:
                        server_info = response['result'].get('serverInfo', {})
                        print(f"✅ {package} is working!")
                        print(f"   Server: {server_info.get('name')}")
                        print(f"   Version: {server_info.get('version')}")
                        return True
                except json.JSONDecodeError:
                    continue
        
        print(f"❌ {package} failed - no valid response")
        if result.stderr:
            print(f"   Error: {result.stderr.decode()[:200]}")
        return False
        
    except subprocess.TimeoutExpired:
        print(f"❌ {package} timed out")
        return False
    except Exception as e:
        print(f"❌ {package} error: {e}")
        return False

def main():
    print("=" * 60)
    print("MCP Server Test Suite")
    print("=" * 60)
    
    # Test BeerSmith (auto-detects path)
    beersmith_ok = test_server("mcp-beersmith")
    
    # Test Grocy (requires env vars - use dummy values for connection test)
    grocy_ok = test_server("mcp-grocy", {
        "GROCY_URL": "http://localhost:9283",
        "GROCY_API_KEY": "test-key"
    })
    
    print("\n" + "=" * 60)
    print("Results:")
    print(f"  BeerSmith: {'✅ PASS' if beersmith_ok else '❌ FAIL'}")
    print(f"  Grocy:     {'✅ PASS' if grocy_ok else '❌ FAIL'}")
    print("=" * 60)
    
    sys.exit(0 if (beersmith_ok and grocy_ok) else 1)

if __name__ == "__main__":
    main()
