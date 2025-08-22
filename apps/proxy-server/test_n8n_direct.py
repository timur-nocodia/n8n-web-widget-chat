#!/usr/bin/env python3
"""
Direct n8n webhook test - check if n8n sends chunks progressively or all at once
"""

import httpx
import asyncio
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from jose import jwt

load_dotenv()

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "https://n8n.nocodia.dev/webhook/ded631bb-9ebf-41f9-a87a-a4b1a22d3a14/chat")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-change-this-in-production")
JWT_ALGORITHM = "HS256"

async def test_n8n_streaming():
    """Test n8n streaming directly without any SSE conversion"""
    
    message = "Напиши короткий список из 3 пунктов про Python"
    
    # Create JWT token
    now = datetime.utcnow()
    jwt_payload = {
        "session_id": "test_direct_123",
        "origin_domain": "test.local",
        "page_url": "http://test.local/test",
        "client_ip": "127.0.0.1",
        "server_ip": "127.0.0.1",
        "user_agent": "TestClient/1.0",
        "timestamp": now.timestamp(),
        "iat": now.timestamp(),
        "exp": (now + timedelta(seconds=60)).timestamp()
    }
    
    jwt_token = jwt.encode(jwt_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    payload = {
        "message": message,
        "timestamp": now.isoformat(),
        "jwt_token": jwt_token,
        "session": {
            "session_id": "test_direct_123",
            "origin_domain": "test.local",
            "page_url": "http://test.local/test",
            "client_ip": "127.0.0.1",
            "server_ip": "127.0.0.1",
            "user_agent": "TestClient/1.0",
            "timestamp": now.timestamp()
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/plain"  # Request streaming response
    }
    
    print(f"[{datetime.now().isoformat()}] Connecting to n8n...")
    print(f"URL: {N8N_WEBHOOK_URL}")
    print(f"Message: {message}")
    print("-" * 80)
    
    start_time = datetime.now()
    first_chunk_time = None
    chunk_count = 0
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", N8N_WEBHOOK_URL, json=payload, headers=headers) as response:
            connect_time = datetime.now()
            print(f"[{connect_time.isoformat()}] Connected! Status: {response.status_code}")
            print(f"Connection time: {(connect_time - start_time).total_seconds():.2f}s")
            print("-" * 80)
            
            buffer = ""
            
            # Read chunks as they arrive
            async for chunk in response.aiter_bytes(chunk_size=1):  # Read 1 byte at a time
                chunk_count += 1
                current_time = datetime.now()
                
                if first_chunk_time is None:
                    first_chunk_time = current_time
                    latency = (first_chunk_time - start_time).total_seconds()
                    print(f"\n🎯 FIRST BYTE after {latency:.2f}s")
                
                chunk_str = chunk.decode('utf-8', errors='ignore')
                buffer += chunk_str
                
                # Process complete lines
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    
                    if line:
                        elapsed = (current_time - start_time).total_seconds()
                        
                        try:
                            json_obj = json.loads(line)
                            obj_type = json_obj.get("type", "unknown")
                            content = json_obj.get("content", "")
                            
                            if obj_type == "item" and content:
                                print(f"[{elapsed:6.2f}s] CONTENT: '{content}'")
                            elif obj_type == "begin":
                                print(f"[{elapsed:6.2f}s] BEGIN streaming")
                            elif obj_type == "end":
                                print(f"[{elapsed:6.2f}s] END streaming")
                            else:
                                print(f"[{elapsed:6.2f}s] {obj_type}: {line[:100]}")
                                
                        except json.JSONDecodeError:
                            print(f"[{elapsed:6.2f}s] RAW: {line[:100]}")
            
            # Process remaining buffer
            if buffer.strip():
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f"[{elapsed:6.2f}s] BUFFER: {buffer[:100]}")
    
    total_time = (datetime.now() - start_time).total_seconds()
    print("-" * 80)
    print(f"Total time: {total_time:.2f}s")
    print(f"Total chunks: {chunk_count}")
    print(f"First chunk latency: {(first_chunk_time - start_time).total_seconds():.2f}s" if first_chunk_time else "No chunks received")

if __name__ == "__main__":
    print("=" * 80)
    print("n8n Direct Streaming Test")
    print("=" * 80)
    asyncio.run(test_n8n_streaming())