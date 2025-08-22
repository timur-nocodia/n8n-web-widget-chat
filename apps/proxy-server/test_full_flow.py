#!/usr/bin/env python3
"""
Full flow test - create session, then test streaming
"""

import httpx
import asyncio
import json
from datetime import datetime
import time

API_BASE = "http://localhost:8001"

async def test_full_flow():
    """Test complete flow: create session -> send message with streaming"""
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Create session
        print(f"[{datetime.now().isoformat()}] Creating session...")
        
        session_response = await client.post(
            f"{API_BASE}/api/v1/session/create",
            json={
                "origin_domain": "localhost",
                "page_url": "http://localhost:3001/test"
            }
        )
        
        if session_response.status_code != 200:
            print(f"Failed to create session: {session_response.status_code}")
            print(session_response.text)
            return
            
        session_data = session_response.json()
        session_id = session_data["session_id"]
        
        # Extract cookie from response
        cookies = session_response.cookies
        
        print(f"✅ Session created: {session_id}")
        print("-" * 80)
        
        # Step 2: Send test message with streaming
        message = "Напиши короткий список из 3 пунктов про Python"
        print(f"[{datetime.now().isoformat()}] Sending message: {message}")
        print("-" * 80)
        
        start_time = datetime.now()
        first_chunk_time = None
        chunk_count = 0
        chunk_times = []
        
        # Use EventSource-style GET request
        params = {
            "message": message,
            "page_url": "http://localhost:3001/test"
        }
        
        async with client.stream(
            "GET",
            f"{API_BASE}/api/v1/chat/stream",
            params=params,
            cookies=cookies,
            headers={
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache"
            }
        ) as response:
            connect_time = datetime.now()
            print(f"[{connect_time.isoformat()}] Connected! Status: {response.status_code}")
            print(f"Connection time: {(connect_time - start_time).total_seconds():.2f}s")
            print("-" * 80)
            
            buffer = ""
            
            # Read stream
            async for chunk in response.aiter_bytes():
                chunk_str = chunk.decode('utf-8', errors='ignore')
                buffer += chunk_str
                
                # Process SSE events
                while '\n\n' in buffer:
                    event, buffer = buffer.split('\n\n', 1)
                    
                    if event.startswith('data: '):
                        data = event[6:]  # Remove "data: " prefix
                        current_time = datetime.now()
                        chunk_count += 1
                        
                        if first_chunk_time is None and data != '[DONE]':
                            first_chunk_time = current_time
                            latency = (first_chunk_time - start_time).total_seconds()
                            print(f"\n🎯 FIRST TOKEN after {latency:.2f}s")
                        
                        if data == '[DONE]':
                            print(f"\n✅ Stream complete")
                            break
                        else:
                            elapsed = (current_time - start_time).total_seconds()
                            if chunk_count > 1:
                                time_since_last = (current_time - chunk_times[-1]).total_seconds() * 1000
                                print(f"[{elapsed:6.2f}s] Chunk #{chunk_count}: '{data}' (+{time_since_last:.0f}ms)")
                            else:
                                print(f"[{elapsed:6.2f}s] Chunk #{chunk_count}: '{data}'")
                            chunk_times.append(current_time)
        
        # Analysis
        total_time = (datetime.now() - start_time).total_seconds()
        print("-" * 80)
        print(f"📊 Analysis:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Total chunks: {chunk_count}")
        
        if first_chunk_time:
            print(f"  First token latency: {(first_chunk_time - start_time).total_seconds():.2f}s")
            
            if len(chunk_times) > 1:
                # Calculate time between chunks
                deltas = []
                for i in range(1, len(chunk_times)):
                    delta = (chunk_times[i] - chunk_times[i-1]).total_seconds() * 1000
                    deltas.append(delta)
                
                avg_delta = sum(deltas) / len(deltas)
                min_delta = min(deltas)
                max_delta = max(deltas)
                
                print(f"  Chunk timing:")
                print(f"    Average gap: {avg_delta:.1f}ms")
                print(f"    Min gap: {min_delta:.1f}ms")
                print(f"    Max gap: {max_delta:.1f}ms")
                
                # Check if chunks arrive all at once (< 1ms gaps means batching)
                if avg_delta < 1.0:
                    print(f"\n⚠️  PROBLEM: All chunks arriving at once (avg {avg_delta:.1f}ms gap)")
                    print(f"    This means n8n is not streaming progressively")
                    print(f"    n8n is sending all data in one batch")
                elif avg_delta < 5.0:
                    print(f"\n⚠️  Chunks arriving very fast (avg {avg_delta:.1f}ms gap)")
                    print(f"    n8n might be batching tokens")
                else:
                    print(f"\n✅ Chunks arriving progressively")
        else:
            print(f"  ❌ No chunks received")

if __name__ == "__main__":
    print("=" * 80)
    print("Full Flow Test: Session + Streaming")
    print("=" * 80)
    asyncio.run(test_full_flow())