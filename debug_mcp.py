#!/usr/bin/env python3
"""
Debug script that mimics Claude Desktop's MCP connection.
Run this to see the exact error messages that Claude Desktop would see.
"""

import subprocess
import sys
import json
import time

def debug_server(name: str, cmd: list, env: dict):
    """Run a server and show all output."""
    print(f"\n{'='*60}")
    print(f"Testing {name}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print(f"Env: {env}")
    print(f"{'='*60}\n")
    
    # Start the server
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**subprocess.os.environ, **env},
        text=True,
        bufsize=0
    )
    
    # Send initialize message
    init_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "claude-desktop", "version": "1.0"}
        }
    }
    
    try:
        # Write the initialize message
        proc.stdin.write(json.dumps(init_msg) + "\n")
        proc.stdin.flush()
        
        # Read response with timeout
        start_time = time.time()
        response_lines = []
        stderr_lines = []
        
        while time.time() - start_time < 3:
            # Check if process is still running
            if proc.poll() is not None:
                print(f"⚠️  Process exited with code: {proc.returncode}")
                break
            
            # Try to read stdout
            try:
                import select
                if select.select([proc.stdout], [], [], 0.1)[0]:
                    line = proc.stdout.readline()
                    if line:
                        response_lines.append(line.strip())
                        if line.strip().startswith('{'):
                            try:
                                resp = json.loads(line)
                                if resp.get('id') == 1:
                                    print("✅ Received valid initialize response:")
                                    print(json.dumps(resp, indent=2))
                                    proc.terminate()
                                    return True
                            except:
                                pass
                
                # Read stderr
                if select.select([proc.stderr], [], [], 0.1)[0]:
                    line = proc.stderr.readline()
                    if line:
                        stderr_lines.append(line.strip())
            except:
                time.sleep(0.1)
        
        # Print all output
        if stderr_lines:
            print("\n📝 STDERR output:")
            for line in stderr_lines:
                print(f"  {line}")
        
        if response_lines:
            print("\n📝 STDOUT output:")
            for line in response_lines:
                print(f"  {line}")
        
        # Check final status
        proc.terminate()
        proc.wait(timeout=1)
        
        if not response_lines:
            print("\n❌ No response received - server didn't respond to initialize")
        
        return False
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        proc.terminate()
        return False

def main():
    print("="*60)
    print("MCP Server Debug Tool")
    print("="*60)
    
    # Test BeerSmith
    beersmith_ok = debug_server(
        "BeerSmith MCP",
        [
            "uv", "run", 
            "--directory", "/Users/john/Development/brewing-mcp",
            "--package", "mcp-beersmith",
            "python", "-m", "mcp_beersmith"
        ],
        {
            "BEERSMITH_PATH": "~/Library/Application Support/BeerSmith3",
            "PYTHONWARNINGS": "ignore"
        }
    )
    
    # Test Grocy
    grocy_ok = debug_server(
        "Grocy MCP",
        [
            "uv", "run",
            "--directory", "/Users/john/Development/brewing-mcp", 
            "--package", "mcp-grocy",
            "python", "-m", "mcp_grocy"
        ],
        {
            "GROCY_URL": "http://192.168.24.24",
            "GROCY_API_KEY": "GTQl3siubFpwSZMU4lLjW8MDLMMScdJNSXv3jvsbTCeEojnFsS",
            "PYTHONWARNINGS": "ignore"
        }
    )
    
    print("\n" + "="*60)
    print("Final Results:")
    print(f"  BeerSmith: {'✅ PASS' if beersmith_ok else '❌ FAIL'}")
    print(f"  Grocy:     {'✅ PASS' if grocy_ok else '❌ FAIL'}")
    print("="*60)

if __name__ == "__main__":
    main()
