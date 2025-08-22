#!/usr/bin/env python3
"""
Test encoding with Cyrillic characters
"""

import httpx
import asyncio
from datetime import datetime

API_BASE = "http://localhost:8001"

async def test_cyrillic():
    """Test Cyrillic encoding through the proxy"""
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Create session
        session_response = await client.post(
            f"{API_BASE}/api/v1/session/create",
            json={"origin_domain": "localhost", "page_url": "test"}
        )
        
        session_data = session_response.json()
        session_id = session_data["session_id"]
        cookies = session_response.cookies
        
        print(f"Session: {session_id}")
        print("=" * 80)
        
        # Test with TEST mode (should show Cyrillic)
        message = "TEST"
        params = {"message": message, "page_url": "test"}
        
        print(f"Sending: {message}")
        print("-" * 80)
        
        async with client.stream(
            "GET",
            f"{API_BASE}/api/v1/chat/stream",
            params=params,
            cookies=cookies,
            headers={"Accept": "text/event-stream"}
        ) as response:
            
            buffer = b""  # Use bytes buffer
            
            # Read raw bytes
            async for chunk in response.aiter_bytes():
                buffer += chunk
                
                # Process SSE events
                while b'\n\n' in buffer:
                    event_bytes, buffer = buffer.split(b'\n\n', 1)
                    
                    # Decode the event
                    try:
                        event = event_bytes.decode('utf-8')
                        
                        if event.startswith('data: '):
                            data = event[6:]  # Remove "data: " prefix
                            
                            if data == '[DONE]':
                                print("\n✅ Stream complete")
                                return
                            
                            # Unescape newlines
                            unescaped = data.replace('\\n', '\n').replace('\\r', '\r')
                            
                            # Show both raw and unescaped
                            print(f"Raw data: {repr(data)}")
                            print(f"Unescaped: {repr(unescaped)}")
                            print(f"Display: {unescaped}")
                            print("-" * 40)
                            
                    except UnicodeDecodeError as e:
                        print(f"❌ Decode error: {e}")
                        print(f"Raw bytes: {event_bytes[:100]}")

if __name__ == "__main__":
    print("Cyrillic Encoding Test")
    print("=" * 80)
    asyncio.run(test_cyrillic())