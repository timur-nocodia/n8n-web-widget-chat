#!/usr/bin/env python3
"""
Analyze n8n streaming behavior - measure exact timing of chunks
"""

import httpx
import asyncio
import json
from datetime import datetime
import time

API_BASE = "http://localhost:8001"

async def analyze_stream():
    """Analyze n8n streaming with microsecond precision"""
    
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
        
        # Send message
        message = "Напиши одно слово 'Привет'"
        params = {"message": message, "page_url": "test"}
        
        # Measure with high precision
        chunks_data = []
        start_time = time.perf_counter()
        
        async with client.stream(
            "GET",
            f"{API_BASE}/api/v1/chat/stream",
            params=params,
            cookies=cookies,
            headers={"Accept": "text/event-stream"}
        ) as response:
            
            buffer = ""
            byte_count = 0
            
            # Read byte by byte for maximum precision
            async for chunk in response.aiter_bytes(chunk_size=1):
                byte_count += 1
                chunk_time = time.perf_counter()
                chunk_str = chunk.decode('utf-8', errors='ignore')
                buffer += chunk_str
                
                # Check for complete SSE event
                if buffer.endswith('\n\n'):
                    if buffer.startswith('data: '):
                        data = buffer[6:].strip()
                        if data and data != '[DONE]':
                            elapsed_ms = (chunk_time - start_time) * 1000
                            chunks_data.append({
                                'content': data,
                                'time_ms': elapsed_ms,
                                'byte_position': byte_count
                            })
                    buffer = ""
    
    # Analyze results
    print("\n📊 CHUNK ANALYSIS:")
    print("-" * 80)
    
    if chunks_data:
        print(f"Total chunks: {len(chunks_data)}")
        print(f"First chunk at: {chunks_data[0]['time_ms']:.3f}ms")
        print(f"Last chunk at: {chunks_data[-1]['time_ms']:.3f}ms")
        print(f"Total duration: {chunks_data[-1]['time_ms'] - chunks_data[0]['time_ms']:.3f}ms")
        
        print("\n📈 CHUNK TIMING:")
        print("-" * 80)
        
        # Group chunks by timing (within 1ms = same batch)
        batches = []
        current_batch = [chunks_data[0]]
        
        for i in range(1, len(chunks_data)):
            time_diff = chunks_data[i]['time_ms'] - chunks_data[i-1]['time_ms']
            
            if time_diff < 1.0:  # Same batch if < 1ms apart
                current_batch.append(chunks_data[i])
            else:
                batches.append(current_batch)
                current_batch = [chunks_data[i]]
        
        if current_batch:
            batches.append(current_batch)
        
        print(f"Number of batches: {len(batches)}")
        print()
        
        for i, batch in enumerate(batches, 1):
            batch_content = ''.join(c['content'] for c in batch)
            batch_time = batch[0]['time_ms']
            batch_size = len(batch)
            
            print(f"Batch #{i} at {batch_time:.1f}ms ({batch_size} chunks):")
            print(f"  Content: '{batch_content}'")
            
            if i < len(batches):
                next_batch_time = batches[i][0]['time_ms']
                gap = next_batch_time - batch_time
                print(f"  Gap to next: {gap:.1f}ms")
        
        print("\n🔍 TIMING DISTRIBUTION:")
        print("-" * 80)
        
        gaps = []
        for i in range(1, len(chunks_data)):
            gap = chunks_data[i]['time_ms'] - chunks_data[i-1]['time_ms']
            gaps.append(gap)
        
        if gaps:
            under_1ms = sum(1 for g in gaps if g < 1.0)
            under_10ms = sum(1 for g in gaps if 1.0 <= g < 10.0)
            over_10ms = sum(1 for g in gaps if g >= 10.0)
            
            print(f"< 1ms gaps: {under_1ms} ({under_1ms/len(gaps)*100:.1f}%)")
            print(f"1-10ms gaps: {under_10ms} ({under_10ms/len(gaps)*100:.1f}%)")
            print(f"≥ 10ms gaps: {over_10ms} ({over_10ms/len(gaps)*100:.1f}%)")
            
            if under_1ms > len(gaps) * 0.8:
                print("\n⚠️  DIAGNOSIS: n8n is batching tokens!")
                print("    Most chunks arrive within 1ms of each other")
                print("    This indicates n8n is not truly streaming")
            elif under_10ms > len(gaps) * 0.5:
                print("\n⚠️  DIAGNOSIS: Partial streaming")
                print("    Some batching, but also some progressive delivery")
            else:
                print("\n✅ DIAGNOSIS: True streaming")
                print("    Chunks arriving progressively")

if __name__ == "__main__":
    print("n8n STREAMING BEHAVIOR ANALYSIS")
    print("=" * 80)
    asyncio.run(analyze_stream())