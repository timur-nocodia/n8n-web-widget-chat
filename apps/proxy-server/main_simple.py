#!/usr/bin/env python3

from fastapi import FastAPI, HTTPException, Request, Cookie, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn
import time
import secrets
import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, AsyncGenerator
import httpx
from jose import JWTError, jwt
from dotenv import load_dotenv
import socket
from starlette.responses import Response as StarletteResponse

# Load environment variables
load_dotenv()

class SSEResponse(StreamingResponse):
    """Custom SSE Response that forces immediate flushing of each chunk"""
    def __init__(self, content: AsyncGenerator, status_code: int = 200):
        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate, no-transform",
            "X-Accel-Buffering": "no",
            "X-Content-Type-Options": "nosniff",
            "Connection": "keep-alive",
        }
        super().__init__(content=content, status_code=status_code, headers=headers, media_type="text/event-stream")

def get_server_ip():
    """Get the server's external IP address for n8n validation"""
    try:
        # Connect to external service to get our public IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "unknown"

SERVER_IP = get_server_ip()

app = FastAPI(title="Chat Proxy - JWT + n8n Integration")

# Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-change-this-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = 10  # Ultra-short expiry for security
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "https://n8n.nocodia.dev/webhook/ded631bb-9ebf-41f9-a87a-a4b1a22d3a14/chat")

# HTTP client for n8n requests
httpx_client = httpx.AsyncClient(timeout=30.0)

# Basic CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173", "null"],  # "null" allows file:// protocol
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Simple models
class CreateSessionRequest(BaseModel):
    origin_domain: str
    page_url: str = None

class SendMessageRequest(BaseModel):
    message: str
    page_url: Optional[str] = None

# In-memory storage for testing (sessions only for security, no persistence needed)
sessions = {}

def create_jwt_token(session_data: dict, request: Request) -> str:
    """Create JWT token with session context for n8n"""
    now = datetime.utcnow()
    payload = {
        "session_id": session_data["id"],
        "origin_domain": session_data["origin_domain"],
        "page_url": session_data.get("page_url"),
        "client_ip": request.client.host if request.client else "unknown",
        "server_ip": SERVER_IP,  # For n8n IP validation
        "user_agent": request.headers.get("user-agent", ""),
        "timestamp": now.timestamp(),
        "iat": now,
        "exp": now + timedelta(seconds=JWT_EXPIRATION_SECONDS)
    }
    
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def get_session_from_cookie(session_id: Optional[str]) -> Optional[dict]:
    """Get session data from cookie"""
    if not session_id or session_id not in sessions:
        return None
    return sessions[session_id]

async def forward_to_n8n_stream(message: str, jwt_token: str, session_data: dict):
    """Forward message to n8n webhook and yield streaming response - NATIVE N8N SPEED"""
    
    # TEST MODE: Character-by-character streaming for debugging
    if "TEST" in message.upper() or "ТЕСТ" in message.upper():
        test_text = f"Привет! Это тестовое сообщение для '{message}'.\nКаждая буква отдельно.\nНовая строка тест."
        print(f"🔬 TEST MODE: Sending {len(test_text)} characters")
        for i, char in enumerate(test_text):
            # Escape newlines for SSE format
            escaped_char = char.replace('\n', '\\n').replace('\r', '\\r')
            chunk = f"data: {escaped_char}\n\n".encode('utf-8')
            print(f"📤 Sending char #{i}: '{repr(char)}' (code: {ord(char)})")
            yield chunk
            await asyncio.sleep(0.01)  # 10ms between chars for visibility
        yield "data: [DONE]\n\n".encode('utf-8')
        print("✅ TEST MODE complete")
        return
    
    try:
        # Decode JWT to get session context for n8n
        jwt_payload = jwt.decode(jwt_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        payload = {
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "jwt_token": jwt_token,
            "session": {
                "session_id": jwt_payload["session_id"],
                "origin_domain": jwt_payload["origin_domain"],
                "page_url": jwt_payload["page_url"],
                "client_ip": jwt_payload["client_ip"],
                "server_ip": jwt_payload["server_ip"],
                "user_agent": jwt_payload["user_agent"],
                "timestamp": jwt_payload["timestamp"]
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/plain"  # Request streaming response from n8n
        }
        
        # Log when we start connecting to n8n
        print(f"🔌 Connecting to n8n at {datetime.utcnow().isoformat()}")
        
        # 🚀 INSTANT STREAMING: Connect to n8n and start processing immediately
        async with httpx_client.stream(
            "POST",
            N8N_WEBHOOK_URL,
            json=payload,
            headers=headers,
            timeout=60.0
        ) as response:
            print(f"✅ Connected to n8n at {datetime.utcnow().isoformat()}, status: {response.status_code}")
            
            if response.status_code == 200:
                buffer = ""
                byte_buffer = b""  # Buffer for incomplete UTF-8 sequences
                
                # 🚀 REAL-TIME PROCESSING: Process chunks immediately as they arrive
                first_chunk_time = None
                chunk_count = 0
                async for chunk in response.aiter_bytes(chunk_size=64):  # Use larger chunks to avoid breaking UTF-8
                    chunk_count += 1
                    chunk_time = datetime.utcnow()
                    if first_chunk_time is None:
                        first_chunk_time = chunk_time
                        print(f"🎯 FIRST CHUNK from n8n at {first_chunk_time.isoformat()} (chunk #{chunk_count}, {len(chunk)} bytes)")
                    
                    # Accumulate bytes to handle incomplete UTF-8 sequences
                    byte_buffer += chunk
                    
                    # Try to decode the accumulated bytes
                    try:
                        # Decode what we can
                        chunk_str = byte_buffer.decode('utf-8')
                        byte_buffer = b""  # Clear buffer on successful decode
                    except UnicodeDecodeError as e:
                        # Keep incomplete bytes in buffer and decode what we can
                        if e.start > 0:
                            # Some bytes can be decoded
                            chunk_str = byte_buffer[:e.start].decode('utf-8')
                            byte_buffer = byte_buffer[e.start:]  # Keep problematic bytes for next iteration
                        else:
                            # Can't decode anything yet, wait for more bytes
                            continue
                    
                    buffer += chunk_str
                    
                    # Process complete lines immediately (n8n sends NDJSON)
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        
                        if line:
                            try:
                                json_obj = json.loads(line)
                                print(f"🔍 n8n JSON: {json.dumps(json_obj)[:200]}")
                                
                                if json_obj.get("type") == "item":
                                    content = json_obj.get("content", "")
                                    
                                    # 🚀 ZERO DELAY: Mirror n8n chunk instantly to frontend
                                    if content is not None:  # Send even empty strings
                                        # Properly escape content for SSE - preserve all characters
                                        # SSE requires escaping newlines in data
                                        escaped_content = content.replace('\n', '\\n').replace('\r', '\\r')
                                        sse_data = f"data: {escaped_content}\n\n"
                                        
                                        # Debug: show actual content including special chars
                                        preview = repr(content[:50]) if content else "''"
                                        print(f"📤 Sending to frontend: {preview} at {datetime.utcnow().isoformat()}")
                                        
                                        yield sse_data.encode('utf-8')  # Send as UTF-8 bytes
                                    
                                elif json_obj.get("type") == "error":
                                    error_content = json_obj.get("content", "Unknown error")
                                    yield f"data: Error: {error_content}\n\n".encode('utf-8')
                                    
                            except json.JSONDecodeError:
                                # Fallback: treat as plain text
                                if line and not line.startswith('{'):
                                    escaped_line = line.replace('\n', '\\n').replace('\r', '\\r')
                                    yield f"data: {escaped_line}\n\n".encode('utf-8')
                                    
                # Handle remaining bytes and buffer
                if byte_buffer:
                    # Force decode any remaining bytes
                    try:
                        remaining_str = byte_buffer.decode('utf-8', errors='replace')
                        buffer += remaining_str
                    except:
                        pass
                
                if buffer.strip():
                    try:
                        json_obj = json.loads(buffer.strip())
                        if json_obj.get("type") == "item":
                            content = json_obj.get("content", "")
                            if content:
                                escaped_content = content.replace('\n', '\\n').replace('\r', '\\r')
                                yield f"data: {escaped_content}\n\n".encode('utf-8')
                    except json.JSONDecodeError:
                        if buffer.strip():
                            escaped_buffer = buffer.strip().replace('\n', '\\n').replace('\r', '\\r')
                            yield f"data: {escaped_buffer}\n\n".encode('utf-8')
            else:
                # Quick fallback for non-200 status
                fallback_msg = f"Echo (n8n unavailable, status {response.status_code}): {message}"
                yield f"data: {fallback_msg}\n\n".encode('utf-8')
            
        # Send completion signal
        yield "data: [DONE]\n\n".encode('utf-8')
                
    except Exception as e:
        # Quick error response
        yield f"data: Извините, проблема с подключением: {str(e)}\n\n".encode('utf-8')
        yield "data: [DONE]\n\n".encode('utf-8')

async def forward_to_n8n(message: str, jwt_token: str, session_data: dict) -> dict:
    """Forward message to n8n webhook with JWT and session data in body (non-streaming)"""
    try:
        # Decode JWT to get session context for n8n
        jwt_payload = jwt.decode(jwt_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        payload = {
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "jwt_token": jwt_token,
            "session": {
                "session_id": jwt_payload["session_id"],
                "origin_domain": jwt_payload["origin_domain"],
                "page_url": jwt_payload["page_url"],
                "client_ip": jwt_payload["client_ip"],
                "server_ip": jwt_payload["server_ip"],
                "user_agent": jwt_payload["user_agent"],
                "timestamp": jwt_payload["timestamp"]
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = await httpx_client.post(
            N8N_WEBHOOK_URL,
            json=payload,
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            # Fallback to echo if n8n is not available
            return {
                "response": f"Echo (n8n unavailable): {message}",
                "timestamp": datetime.utcnow().isoformat(),
                "model": "fallback-echo",
                "n8n_status": response.status_code
            }
            
    except Exception as e:
        # Fallback to echo if n8n connection fails
        return {
            "response": f"Echo (n8n error): {message}",
            "timestamp": datetime.utcnow().isoformat(),
            "model": "fallback-echo",
            "error": str(e)
        }

@app.get("/")
async def root():
    return {"message": "Chat Proxy Simple Version", "status": "working"}

@app.get("/health")
async def health_check():
    # Test n8n connectivity
    n8n_status = "unknown"
    try:
        response = await httpx_client.get(N8N_WEBHOOK_URL.replace('/webhook/chat', '/health'), timeout=5)
        n8n_status = "healthy" if response.status_code == 200 else f"unhealthy ({response.status_code})"
    except:
        n8n_status = "unreachable"
    
    return {
        "status": "healthy",
        "version": "jwt-n8n-0.2",
        "services": {
            "n8n_webhook": n8n_status,
            "jwt_service": "active"
        },
        "config": {
            "n8n_url": N8N_WEBHOOK_URL,
            "jwt_expiration": f"{JWT_EXPIRATION_SECONDS}s"
        }
    }

@app.post("/api/v1/session/create")
async def create_session(request: CreateSessionRequest, http_request: Request):
    session_id = secrets.token_urlsafe(16)
    
    sessions[session_id] = {
        "id": session_id,
        "origin_domain": request.origin_domain,
        "page_url": request.page_url,
        "created_at": time.time(),
        "ip": http_request.client.host if http_request.client else "unknown",
        "user_agent": http_request.headers.get("user-agent", "")
    }
    
    return JSONResponse(
        content={
            "session_id": session_id,
            "expires_at": time.time() + 86400  # 24 hours
        },
        headers={"Set-Cookie": f"chat_session_id={session_id}; HttpOnly; Path=/; Max-Age=86400"}
    )

@app.post("/api/v1/chat/message")
async def send_message(
    request: SendMessageRequest, 
    http_request: Request,
    chat_session_id: Optional[str] = Cookie(None)
):
    # Get session from cookie
    session = get_session_from_cookie(chat_session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or missing session")
    
    # Update session with current page URL if provided
    if request.page_url:
        session["page_url"] = request.page_url
    
    # Create JWT token with session context
    jwt_token = create_jwt_token(session, http_request)
    
    # Forward to n8n with JWT and session data
    response = await forward_to_n8n(request.message, jwt_token, session)
    
    return response

@app.post("/api/v1/chat/stream")
async def stream_chat_post(
    request: SendMessageRequest, 
    http_request: Request,
    chat_session_id: Optional[str] = Cookie(None)
):
    return await stream_chat_impl(request.message, request.page_url, http_request, chat_session_id)

@app.get("/api/v1/chat/stream")
async def stream_chat_get(
    message: str,
    page_url: str,
    http_request: Request,
    chat_session_id: Optional[str] = Cookie(None)
):
    return await stream_chat_impl(message, page_url, http_request, chat_session_id)

async def stream_chat_impl(
    message: str,
    page_url: str, 
    http_request: Request,
    chat_session_id: Optional[str]
):
    """SSE streaming endpoint for real-time chat responses"""
    # Get session from cookie
    session = get_session_from_cookie(chat_session_id)
    if not session:
        # Return error as SSE
        async def error_stream():
            yield "data: {\"error\": \"Invalid or missing session\"}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")
    
    # Update session with current page URL if provided
    if page_url:
        session["page_url"] = page_url
    
    # Create JWT token with session context
    jwt_token = create_jwt_token(session, http_request)
    
    # Return custom SSE response with forced flushing
    return SSEResponse(forward_to_n8n_stream(message, jwt_token, session))

@app.get("/api/v1/jwt/test")
async def test_jwt(
    http_request: Request,
    chat_session_id: Optional[str] = Cookie(None)
):
    """Test JWT generation - useful for debugging your n8n workflow"""
    session = get_session_from_cookie(chat_session_id)
    if not session:
        return {"error": "No valid session found"}
    
    jwt_token = create_jwt_token(session, http_request)
    
    # Decode the token to show what n8n will receive
    try:
        payload = jwt.decode(jwt_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return {
            "jwt_token": jwt_token,
            "decoded_payload": payload,
            "info": "This is what your n8n workflow will receive in the JWT"
        }
    except JWTError as e:
        return {"error": f"JWT error: {str(e)}"}

# Add cleanup for httpx client
@app.on_event("shutdown")
async def shutdown_event():
    await httpx_client.aclose()

if __name__ == "__main__":
    print("🚀 Starting Chat Proxy with JWT + n8n Integration...")
    print(f"📡 n8n webhook URL: {N8N_WEBHOOK_URL}")
    print(f"🔑 JWT expiration: {JWT_EXPIRATION_SECONDS} seconds")
    print(f"🌐 Server IP (for n8n validation): {SERVER_IP}")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")