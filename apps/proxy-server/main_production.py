#!/usr/bin/env python3
"""
Production Chat Proxy Server
Simplified production version without complex dependencies
"""

import asyncio
import json
import logging
import os
import secrets
import socket
import time
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import Cookie, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from jose import jwt
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.getenv("LOG_LEVEL", "WARNING")
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)


class SSEResponse(StreamingResponse):
    """Custom SSE Response that forces immediate flushing of each chunk"""

    def __init__(self, content: AsyncGenerator, status_code: int = 200):
        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate, no-transform",
            "X-Accel-Buffering": "no",
            "X-Content-Type-Options": "nosniff",
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked",  # Force chunked encoding
        }
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type="text/event-stream",
        )


def get_server_ip():
    """Get the server's external IP address for n8n validation"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "unknown"


SERVER_IP = get_server_ip()

app = FastAPI(title="Chat Proxy - Production Server")

# Serve static files (widget)
import os

static_dir = os.path.join(os.path.dirname(__file__), "..", "chat-widget")
if os.path.exists(static_dir):
    app.mount("/widget", StaticFiles(directory=static_dir, html=True), name="widget")

# Configuration
JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY", "your-super-secret-jwt-key-change-this-in-production"
)
SESSION_SECRET_KEY = os.getenv(
    "SESSION_SECRET_KEY", "test-session-secret-for-development"
)  # For n8n JWT validation
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = 30  # 30 seconds for n8n tokens (security)
N8N_WEBHOOK_URL = os.getenv(
    "N8N_WEBHOOK_URL",
    "https://n8n.nocodia.dev/webhook/ded631bb-9ebf-41f9-a87a-a4b1a22d3a14/chat",
)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(",")

# HTTP client for n8n requests
httpx_client = httpx.AsyncClient(timeout=30.0)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS + ["null"],
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


# In-memory session storage (production should use Redis/Database)
sessions = {}


def create_jwt_token(session_data: dict, request: Request) -> str:
    """Create JWT token with session context for n8n"""
    now = datetime.utcnow()
    payload = {
        "session_id": session_data["id"],
        "origin_domain": session_data["origin_domain"],
        "page_url": session_data.get("page_url"),
        "client_ip": request.client.host if request.client else "unknown",
        "server_ip": SERVER_IP,
        "user_agent": request.headers.get("user-agent", ""),
        "timestamp": now.timestamp(),
        "iat": now,
        "exp": now + timedelta(seconds=JWT_EXPIRATION_SECONDS),
    }

    # Use SESSION_SECRET_KEY for n8n JWT validation
    return jwt.encode(payload, SESSION_SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_session_from_cookie(session_id: Optional[str]) -> Optional[dict]:
    """Get session data from cookie"""
    if not session_id or session_id not in sessions:
        return None
    return sessions[session_id]


async def forward_to_n8n_stream(message: str, jwt_token: str, session_data: dict):
    """Forward message to n8n webhook and yield streaming response"""

    try:
        # Decode JWT to get session context
        jwt_payload = jwt.decode(
            jwt_token, SESSION_SECRET_KEY, algorithms=[JWT_ALGORITHM]
        )

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
                "timestamp": jwt_payload["timestamp"],
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream, text/plain",  # Accept SSE format from n8n
        }

        logger.info(f"Sending request to n8n for session {jwt_payload['session_id']}")

        async with httpx_client.stream(
            "POST", N8N_WEBHOOK_URL, json=payload, headers=headers, timeout=60.0
        ) as response:
            logger.info(f"n8n response status: {response.status_code}")

            if response.status_code == 200:
                buffer = ""
                byte_buffer = b""

                async for chunk in response.aiter_bytes(
                    chunk_size=1
                ):  # Byte-by-byte for immediate processing
                    # Handle UTF-8 properly
                    byte_buffer += chunk

                    try:
                        chunk_str = byte_buffer.decode("utf-8")
                        byte_buffer = b""
                    except UnicodeDecodeError:
                        # Wait for more bytes to complete the character
                        continue

                    if chunk_str:
                        buffer += chunk_str

                    # Process complete JSON lines immediately (n8n sends newline-delimited JSON)
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()

                        if line:
                            try:
                                json_obj = json.loads(line)

                                # Handle different chunk types from n8n
                                chunk_type = json_obj.get("type")

                                if chunk_type == "begin":
                                    # Signal start of streaming
                                    logger.info(
                                        f"Streaming started for node: {json_obj.get('metadata', {}).get('nodeName')}"
                                    )

                                elif chunk_type == "item":
                                    # Stream content immediately as it arrives from n8n
                                    content = json_obj.get("content", "")
                                    if content:
                                        logger.debug(
                                            f"Chunk from n8n: {repr(content[:20])}"
                                        )

                                        # Option 1: Send as single chunk (current n8n behavior)
                                        # escaped_content = content.replace('\n', '\\n').replace('\r', '\\r')
                                        # sse_data = f"data: {escaped_content}\n\n"
                                        # yield sse_data.encode('utf-8')

                                        # Option 2: Send chunks as-is for real-time streaming
                                        # (n8n already sends in small chunks)
                                        escaped_content = content.replace(
                                            "\n", "\\n"
                                        ).replace("\r", "\\r")
                                        sse_data = f"data: {escaped_content}\n\n"
                                        yield sse_data.encode("utf-8")
                                        # Force immediate flush
                                        await asyncio.sleep(0)

                                elif chunk_type == "end":
                                    # Signal end of streaming for this node
                                    logger.info(
                                        f"Streaming ended for node: {json_obj.get('metadata', {}).get('nodeName')}"
                                    )

                                elif chunk_type == "error":
                                    # Handle error from n8n
                                    error_content = json_obj.get(
                                        "content", "Unknown error"
                                    )
                                    yield f"data: Error: {error_content}\n\n".encode(
                                        "utf-8"
                                    )

                            except json.JSONDecodeError:
                                # If not JSON, treat as plain text
                                if line and not line.startswith("{"):
                                    escaped_line = line.replace("\n", "\\n").replace(
                                        "\r", "\\r"
                                    )
                                    yield f"data: {escaped_line}\n\n".encode("utf-8")

                # Handle remaining buffer
                if buffer.strip():
                    try:
                        json_obj = json.loads(buffer.strip())
                        if json_obj.get("type") == "item":
                            content = json_obj.get("content", "")
                            if content:
                                escaped_content = content.replace("\n", "\\n").replace(
                                    "\r", "\\r"
                                )
                                yield f"data: {escaped_content}\n\n".encode("utf-8")
                    except json.JSONDecodeError:
                        if buffer.strip():
                            escaped_buffer = (
                                buffer.strip().replace("\n", "\\n").replace("\r", "\\r")
                            )
                            yield f"data: {escaped_buffer}\n\n".encode("utf-8")
            else:
                # Fallback for non-200 status
                fallback_msg = (
                    f"Echo (n8n unavailable, status {response.status_code}): {message}"
                )
                yield f"data: {fallback_msg}\n\n".encode("utf-8")

        # Send completion signal
        yield "data: [DONE]\n\n".encode("utf-8")

    except Exception as e:
        logger.error(f"Error in n8n stream: {str(e)}")
        yield f"data: Error: {str(e)}\n\n".encode("utf-8")
        yield "data: [DONE]\n\n".encode("utf-8")


@app.get("/")
async def root():
    return {
        "message": "Chat Proxy Production Server",
        "status": "running",
        "cors_origins": ALLOWED_ORIGINS,
        "has_8004": "http://localhost:8004" in ALLOWED_ORIGINS,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    n8n_status = "unknown"
    try:
        # Quick n8n connectivity test
        response = await httpx_client.get(
            N8N_WEBHOOK_URL.replace("/webhook/chat", "/health"), timeout=5
        )
        n8n_status = (
            "healthy"
            if response.status_code == 200
            else f"unhealthy ({response.status_code})"
        )
    except:
        n8n_status = "unreachable"

    return {
        "status": "healthy",
        "version": "production-1.0",
        "services": {
            "n8n_webhook": n8n_status,
            "jwt_service": "active",
            "sessions_active": len(sessions),
        },
        "config": {
            "n8n_url": N8N_WEBHOOK_URL,
            "jwt_expiration": f"{JWT_EXPIRATION_SECONDS}s",
            "allowed_origins": len(ALLOWED_ORIGINS),
        },
    }


@app.post("/api/v1/session/create")
async def create_session(request: CreateSessionRequest, http_request: Request):
    """Create a new session"""
    session_id = secrets.token_urlsafe(16)

    sessions[session_id] = {
        "id": session_id,
        "origin_domain": request.origin_domain,
        "page_url": request.page_url,
        "created_at": time.time(),
        "ip": http_request.client.host if http_request.client else "unknown",
        "user_agent": http_request.headers.get("user-agent", ""),
    }

    logger.info(f"Created session {session_id} for {request.origin_domain}")

    return JSONResponse(
        content={
            "session_id": session_id,
            "expires_at": time.time() + 86400,  # 24 hours
        },
        headers={
            "Set-Cookie": f"chat_session_id={session_id}; HttpOnly; Path=/; Max-Age=86400"
        },
    )


@app.get("/api/v1/session/validate")
async def validate_session(chat_session_id: Optional[str] = Cookie(None)):
    """Validate an existing session"""
    session = get_session_from_cookie(chat_session_id)

    if not session:
        raise HTTPException(status_code=401, detail="Invalid or missing session")

    return {
        "valid": True,
        "session_id": session["id"],
        "origin_domain": session["origin_domain"],
    }


@app.post("/api/v1/chat/message")
async def send_message(
    request: SendMessageRequest,
    http_request: Request,
    chat_session_id: Optional[str] = Cookie(None),
):
    """Send a message (non-streaming)"""
    session = get_session_from_cookie(chat_session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or missing session")

    if request.page_url:
        session["page_url"] = request.page_url

    jwt_token = create_jwt_token(session, http_request)

    # For non-streaming, collect the response
    response_text = ""
    async for chunk in forward_to_n8n_stream(request.message, jwt_token, session):
        chunk_str = chunk.decode("utf-8")
        if chunk_str.startswith("data: ") and not chunk_str.startswith("data: [DONE]"):
            content = chunk_str[6:].strip()
            if content and not content.startswith("Error:"):
                response_text += content.replace("\\n", "\n").replace("\\r", "\r")

    return {"response": response_text or f"Echo: {request.message}"}


@app.post("/api/v1/chat/stream")
async def stream_chat_post(
    request: SendMessageRequest,
    http_request: Request,
    chat_session_id: Optional[str] = Cookie(None),
):
    """SSE streaming endpoint"""
    return await stream_chat_impl(
        request.message, request.page_url, http_request, chat_session_id
    )


@app.get("/api/v1/chat/stream")
async def stream_chat_get(
    message: str,
    page_url: str,
    http_request: Request,
    chat_session_id: Optional[str] = Cookie(None),
):
    """SSE streaming endpoint (GET)"""
    return await stream_chat_impl(message, page_url, http_request, chat_session_id)


async def stream_chat_impl(
    message: str, page_url: str, http_request: Request, chat_session_id: Optional[str]
):
    """SSE streaming implementation"""
    session = get_session_from_cookie(chat_session_id)
    if not session:
        # Return error as SSE
        async def error_stream():
            yield 'data: {"error": "Invalid or missing session"}\n\n'
            yield "data: [DONE]\n\n"

        return StreamingResponse(error_stream(), media_type="text/event-stream")

    if page_url:
        session["page_url"] = page_url

    jwt_token = create_jwt_token(session, http_request)

    # Return custom SSE response
    return SSEResponse(forward_to_n8n_stream(message, jwt_token, session))


# Cleanup on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    await httpx_client.aclose()


if __name__ == "__main__":
    print("🚀 Starting Chat Proxy Production Server...")
    print(f"📡 n8n webhook URL: {N8N_WEBHOOK_URL}")
    print(f"🔑 JWT expiration: {JWT_EXPIRATION_SECONDS} seconds")
    print(f"🌐 Server IP: {SERVER_IP}")
    print(f"✅ CORS origins: {', '.join(ALLOWED_ORIGINS)}")
    # Run with no buffering and immediate response
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        # Disable buffering
        limit_concurrency=1000,
        timeout_keep_alive=75,
        access_log=False,  # Reduce overhead
    )
