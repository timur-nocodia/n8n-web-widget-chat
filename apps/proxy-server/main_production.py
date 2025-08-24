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
from fastapi import Cookie, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import jwt
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.getenv("LOG_LEVEL", "WARNING")
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

# Server configuration
API_PORT = int(os.getenv("API_PORT", 8000))


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
JWT_EXPIRATION_SECONDS = 300  # 5 minutes for n8n tokens (debugging)
N8N_WEBHOOK_URL = os.getenv(
    "N8N_WEBHOOK_URL",
    "https://n8n.nocodia.dev/webhook/ded631bb-9ebf-41f9-a87a-a4b1a22d3a14/chat",
)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(",")

# HTTP client pool settings for n8n requests
HTTP_POOL_LIMITS = httpx.Limits(max_keepalive_connections=20, max_connections=100)
HTTP_TIMEOUT = httpx.Timeout(30.0, pool=10.0)

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


def create_internal_jwt_token(session_data: dict, request: Request) -> str:
    """Create internal JWT token for browser-server authentication"""
    now = datetime.utcnow()
    
    # Generate browser fingerprint hash for security
    fingerprint_data = {
        "user_agent": request.headers.get("user-agent", ""),
        "client_ip": request.client.host if request.client else "unknown",
        "origin_domain": session_data["origin_domain"]
    }
    fingerprint_hash = str(hash(str(fingerprint_data)))

    payload = {
        "session_id": session_data["id"],
        "origin_domain": session_data["origin_domain"],
        "fingerprint": fingerprint_hash,
        "created_at": now.isoformat(),
        "iat": now,
        "exp": now + timedelta(days=7),  # Long-lived internal token
    }

    # Use JWT_SECRET_KEY for internal session management
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_n8n_jwt_token(session_data: dict, request: Request) -> str:
    """Create short-lived JWT token for n8n webhook authentication"""
    now = datetime.utcnow()
    payload = {
        "session_id": session_data["id"],
        "origin_domain": session_data["origin_domain"],
        "page_url": session_data.get("page_url"),
        "client_ip": request.client.host if request.client else "unknown",
        "server_ip": SERVER_IP,
        "user_agent": request.headers.get("user-agent", ""),
        "timestamp": now.isoformat(),
        "message_history": [],  # Will be populated per request
        "session_metadata": {},  # Additional context
        "iat": now,
        "exp": now + timedelta(seconds=JWT_EXPIRATION_SECONDS),  # Short-lived n8n token
    }

    # Use SESSION_SECRET_KEY for n8n JWT validation
    return jwt.encode(payload, SESSION_SECRET_KEY, algorithm=JWT_ALGORITHM)


def validate_internal_jwt_token(token: str) -> Optional[dict]:
    """Validate internal JWT token and return payload"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Internal JWT token expired")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid internal JWT token")
        return None


def get_session_from_cookie(session_id: Optional[str]) -> Optional[dict]:
    """Get session data from cookie"""
    if not session_id or session_id not in sessions:
        return None
    return sessions[session_id]


async def forward_to_n8n_stream(message: str, jwt_token: str, session_data: dict, app_instance=None):
    """Forward message to n8n webhook and yield streaming response"""

    # Track connection if app instance is available
    connection_id = None
    if app_instance and hasattr(app_instance.state, 'active_connections'):
        connection_id = f"{session_data.get('id', 'unknown')}_{int(time.time())}"
        app_instance.state.active_connections.add(connection_id)

    try:
        # Decode JWT to get session context
        logger.info(f"Decoding JWT token for message: '{message}'")
        jwt_payload = jwt.decode(
            jwt_token, SESSION_SECRET_KEY, algorithms=[JWT_ALGORITHM]
        )
        logger.info(f"JWT decoded successfully for session: {jwt_payload.get('session_id')}")

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
        logger.info(f"Full payload being sent to n8n: {payload}")
        logger.info(f"Message length: {len(message)}, JWT token length: {len(jwt_token)}")
        logger.info(f"n8n URL: {N8N_WEBHOOK_URL}")

        # Create fresh client for this request to avoid connection state conflicts
        async with httpx.AsyncClient(limits=HTTP_POOL_LIMITS, timeout=HTTP_TIMEOUT) as client:
            async with client.stream(
                "POST", N8N_WEBHOOK_URL, json=payload, headers=headers
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
                                        # Send the complete JSON structure that client expects
                                        json_response = json.dumps(json_obj)
                                        sse_data = f"data: {json_response}\n\n"
                                        yield sse_data.encode("utf-8")

                                    elif chunk_type == "item":
                                        # Stream content immediately as it arrives from n8n
                                        content = json_obj.get("content", "")
                                        if content:
                                            logger.debug(
                                                f"Chunk from n8n: {repr(content[:20])}"
                                            )

                                            # Send the complete JSON structure that client expects
                                            json_response = json.dumps(json_obj)
                                            sse_data = f"data: {json_response}\n\n"
                                            yield sse_data.encode("utf-8")
                                            # Force immediate flush
                                            await asyncio.sleep(0)

                                    elif chunk_type == "end":
                                        # Signal end of streaming for this node
                                        logger.info(
                                            f"Streaming ended for node: {json_obj.get('metadata', {}).get('nodeName')}"
                                        )
                                        # Send the complete JSON structure that client expects
                                        json_response = json.dumps(json_obj)
                                        sse_data = f"data: {json_response}\n\n"
                                        yield sse_data.encode("utf-8")

                                    elif chunk_type == "error":
                                        # Handle error from n8n
                                        error_content = json_obj.get(
                                            "content", "Unknown error"
                                        )
                                        # Send the complete JSON structure that client expects
                                        json_response = json.dumps(json_obj)
                                        sse_data = f"data: {json_response}\n\n"
                                        yield sse_data.encode("utf-8")

                                except json.JSONDecodeError:
                                    # If not JSON, treat as plain text and wrap in proper JSON
                                    if line and not line.startswith("{"):
                                        plain_text_json = {"type": "item", "content": line}
                                        json_response = json.dumps(plain_text_json)
                                        sse_data = f"data: {json_response}\n\n"
                                        yield sse_data.encode("utf-8")

                    # Handle remaining buffer
                    if buffer.strip():
                        try:
                            json_obj = json.loads(buffer.strip())
                            if json_obj.get("type") == "item":
                                content = json_obj.get("content", "")
                                if content:
                                    # Send the complete JSON structure that client expects
                                    json_response = json.dumps(json_obj)
                                    sse_data = f"data: {json_response}\n\n"
                                    yield sse_data.encode("utf-8")
                        except json.JSONDecodeError:
                            if buffer.strip():
                                # Wrap plain text in proper JSON format
                                plain_text_json = {"type": "item", "content": buffer.strip()}
                                json_response = json.dumps(plain_text_json)
                                sse_data = f"data: {json_response}\n\n"
                                yield sse_data.encode("utf-8")
                else:
                    # Fallback for non-200 status
                    fallback_msg = (
                        f"Echo (n8n unavailable, status {response.status_code}): {message}"
                    )
                    # Wrap in proper JSON format
                    fallback_json = {"type": "item", "content": fallback_msg}
                    json_response = json.dumps(fallback_json)
                    sse_data = f"data: {json_response}\n\n"
                    yield sse_data.encode("utf-8")

        # Send completion signal
        yield "data: [DONE]\n\n".encode("utf-8")

    except Exception as e:
        logger.error(f"Error in n8n stream: {str(e)}")
        yield f"data: Error: {str(e)}\n\n".encode("utf-8")
        yield "data: [DONE]\n\n".encode("utf-8")
    finally:
        # Remove connection from tracking set
        if connection_id and app_instance and hasattr(app_instance.state, 'active_connections'):
            app_instance.state.active_connections.discard(connection_id)


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
        # Quick n8n connectivity test with fresh client
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                N8N_WEBHOOK_URL.replace("/webhook/chat", "/health")
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
    """Create a new session with dual JWT tokens"""
    session_id = f"sess_{int(time.time())}_{secrets.token_hex(8)}"

    session_data = {
        "id": session_id,
        "origin_domain": request.origin_domain,
        "page_url": request.page_url,
        "created_at": time.time(),
        "ip": http_request.client.host if http_request.client else "unknown",
        "user_agent": http_request.headers.get("user-agent", ""),
    }

    sessions[session_id] = session_data

    # Create both tokens for dual-key security
    internal_token = create_internal_jwt_token(session_data, http_request)
    n8n_token = create_n8n_jwt_token(session_data, http_request)

    logger.info(f"Created session {session_id} for {request.origin_domain} with dual JWT tokens")

    expires_at = datetime.utcnow() + timedelta(days=7)
    
    return JSONResponse(
        content={
            "session_id": session_id,
            "internal_token": internal_token,  # Long-lived browser token
            "n8n_token": n8n_token,           # Short-lived n8n token
            "expires_at": expires_at.isoformat(),
            "token_info": {
                "internal_token_purpose": "Browser-server authentication (7 days)",
                "n8n_token_purpose": "n8n webhook authentication (30 seconds)",
                "security_note": "Tokens serve different purposes in dual-key architecture"
            }
        },
        headers={
            "Set-Cookie": f"chat_session_id={session_id}; Path=/; Max-Age=604800; SameSite=Lax"  # 7 days, removed HttpOnly for widget compatibility
        },
    )


@app.get("/api/v1/session/validate")
async def validate_session(
    chat_session_id: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
    http_request: Request = None
):
    """Validate an existing session with optional internal JWT token"""
    session = get_session_from_cookie(chat_session_id)

    if not session:
        raise HTTPException(status_code=401, detail="Invalid or missing session")

    # If internal JWT token is provided, validate it
    internal_token_valid = False
    if authorization and authorization.startswith("Bearer "):
        internal_token = authorization[7:]
        token_payload = validate_internal_jwt_token(internal_token)
        if token_payload and token_payload.get("session_id") == session["id"]:
            internal_token_valid = True

    # Generate fresh n8n token for this validation
    fresh_n8n_token = create_n8n_jwt_token(session, http_request) if http_request else None

    return {
        "valid": True,
        "session_id": session["id"],
        "origin_domain": session["origin_domain"],
        "internal_token_valid": internal_token_valid,
        "fresh_n8n_token": fresh_n8n_token,
        "security_info": {
            "dual_key_system": "Active",
            "internal_token_validated": internal_token_valid,
            "fresh_n8n_token_generated": fresh_n8n_token is not None
        }
    }


@app.post("/api/v1/chat/message")
async def send_message(
    request: SendMessageRequest,
    http_request: Request,
    chat_session_id: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
):
    """Send a message (non-streaming)"""
    session = get_session_from_cookie(chat_session_id)
    
    # If no cookie session, try Authorization header
    if not session and authorization and authorization.startswith("Bearer "):
        internal_token = authorization[7:]
        token_payload = validate_internal_jwt_token(internal_token)
        if token_payload:
            session = {
                "id": token_payload["session_id"],
                "origin_domain": token_payload["origin_domain"],
                "created_at": token_payload["created_at"],
                "fingerprint": token_payload["fingerprint"]
            }
    
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or missing session")

    if request.page_url:
        session["page_url"] = request.page_url

    jwt_token = create_n8n_jwt_token(session, http_request)

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
    authorization: Optional[str] = Header(None),
):
    """SSE streaming endpoint"""
    return await stream_chat_impl(
        request.message, request.page_url, http_request, chat_session_id, authorization
    )


@app.get("/api/v1/chat/stream")
async def stream_chat_get(
    message: str,
    page_url: str,
    http_request: Request,
    chat_session_id: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
):
    """SSE streaming endpoint (GET)"""
    return await stream_chat_impl(message, page_url, http_request, chat_session_id, authorization)


async def stream_chat_impl(
    message: str, page_url: str, http_request: Request, chat_session_id: Optional[str], authorization: Optional[str] = None
):
    """SSE streaming implementation"""
    session = get_session_from_cookie(chat_session_id)
    
    # If no cookie session, try Authorization header
    if not session and authorization and authorization.startswith("Bearer "):
        internal_token = authorization[7:]
        token_payload = validate_internal_jwt_token(internal_token)
        if token_payload:
            session = {
                "id": token_payload["session_id"],
                "origin_domain": token_payload["origin_domain"],
                "created_at": token_payload["created_at"],
                "fingerprint": token_payload["fingerprint"]
            }
    
    if not session:
        # Return error as SSE
        async def error_stream():
            yield 'data: {"error": "Invalid or missing session"}\n\n'
            yield "data: [DONE]\n\n"

        return StreamingResponse(error_stream(), media_type="text/event-stream")

    if page_url:
        session["page_url"] = page_url

    jwt_token = create_n8n_jwt_token(session, http_request)

    # Return custom SSE response with app state for connection tracking
    return SSEResponse(forward_to_n8n_stream(message, jwt_token, session, http_request.app))


# Application lifecycle events
@app.on_event("startup")
async def startup_event():
    app.state.start_time = time.time()
    app.state.active_connections = set()  # Track active SSE connections
    logger.info(f"🚀 Production Chat Proxy started on {SERVER_IP}:{API_PORT}")
    logger.info(f"📡 n8n webhook: {N8N_WEBHOOK_URL}")
    logger.info(f"🌐 Allowed origins: {', '.join(ALLOWED_ORIGINS)}")
    logger.info(f"🔑 JWT expiration: {JWT_EXPIRATION_SECONDS} seconds")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Graceful shutdown initiated...")
    
    # Wait for active SSE connections to finish
    if hasattr(app.state, 'active_connections'):
        active_count = len(app.state.active_connections)
        if active_count > 0:
            logger.info(f"⏳ Waiting for {active_count} active SSE connections to complete...")
            
            for i in range(30):  # Wait up to 30 seconds
                if len(app.state.active_connections) == 0:
                    break
                await asyncio.sleep(1)
                
            remaining = len(app.state.active_connections)
            if remaining > 0:
                logger.warning(f"⚠️  {remaining} connections still active after 30s timeout")
            else:
                logger.info("✅ All SSE connections completed gracefully")
    
    # Clear any in-memory state
    rate_limit_store.clear() if 'rate_limit_store' in globals() else None
    logger.info("🧹 Cleaned up in-memory state")
    
    uptime = time.time() - getattr(app.state, 'start_time', time.time())
    logger.info(f"✅ Production Chat Proxy shutdown complete (uptime: {uptime:.1f}s)")


# Import asyncio for shutdown event  
import asyncio


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
        port=API_PORT,
        log_level="info",
        # Disable buffering
        limit_concurrency=1000,
        timeout_keep_alive=75,
        access_log=False,  # Reduce overhead
    )
