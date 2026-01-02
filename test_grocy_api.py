#!/usr/bin/env python3
"""Test Grocy API endpoints to find the correct base path."""

import httpx
import sys

GROCY_URL = "http://192.168.24.24"
GROCY_API_KEY = "GTQl3siubFpwSZMU4lLjW8MDLMMScdJNSXv3jvsbTCeEojnFsS"

async def test_endpoint(client: httpx.AsyncClient, url: str) -> bool:
    """Test if an endpoint returns 200 OK."""
    try:
        response = await client.get(url)
        if response.status_code == 200:
            print(f"✅ {url} - OK (200)")
            return True
        else:
            print(f"❌ {url} - {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {url} - Error: {e}")
        return False

async def main():
    headers = {
        "GROCY-API-KEY": GROCY_API_KEY,
        "Accept": "application/json",
    }
    
    # Test different base paths
    test_paths = [
        "/api/system/info",
        "/api/v1/system/info",
        "/api/v2/system/info",
        "/system/info",
        "/grocy/api/system/info",
        "/api/stock",
        "/api/objects/products",
    ]
    
    print(f"Testing Grocy API at {GROCY_URL}")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
        for path in test_paths:
            url = f"{GROCY_URL}{path}"
            await test_endpoint(client, url)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
