#!/usr/bin/env python3
"""
Stateless Chat Proxy Server
No database required - all session data managed client-side
Ultra-lightweight FastAPI server for chat proxying to n8n
"""

import hashlib
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

import httpx
import jwt
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Configuration from environment
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "https://your-n8n.com/webhook/chat")
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "your-super-secure-jwt-secret-change-this")
SESSION_SECRET = os.getenv("SESSION_SECRET_KEY", "your-session-secret-change-this")
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://localhost:8000",
).split(",")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", 60))

# In-memory rate limiting (resets on server restart)
request_counts: Dict[str, Dict[str, int]] = {}

app = FastAPI(
    title="Stateless Chat Proxy",
    version="1.0.0",
    description="Lightweight chat proxy server with browser-side session management",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# Pydantic models
class ChatMessage(BaseModel):
    message: str = Field(..., max_length=10000)
    page_url: Optional[str] = None
    session_id: Optional[str] = None
    message_history: Optional[list] = []
    session_metadata: Optional[dict] = {}


class SessionCreate(BaseModel):
    origin_domain: Optional[str] = None
    page_url: Optional[str] = None
    session_id: Optional[str] = None  # Client can provide existing session ID


# Utility functions
def get_client_ip(request: Request) -> str:
    """Get client IP with proxy headers support"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit_check(client_ip: str) -> bool:
    """Simple in-memory rate limiting"""
    current_minute = int(time.time() // 60)

    if client_ip not in request_counts:
        request_counts[client_ip] = {}

    # Clean old entries (keep only current and previous minute)
    request_counts[client_ip] = {
        k: v for k, v in request_counts[client_ip].items() if k >= current_minute - 1
    }

    # Check current minute
    current_count = request_counts[client_ip].get(current_minute, 0)
    if current_count >= RATE_LIMIT_PER_MINUTE:
        return False

    # Increment counter
    request_counts[client_ip][current_minute] = current_count + 1
    return True


def create_session_token(session_id: str, client_ip: str, user_agent: str) -> str:
    """Create a stateless session token"""
    payload = {
        "session_id": session_id,
        "client_ip": client_ip,
        "user_agent": hashlib.sha256(user_agent.encode()).hexdigest()[:16],
        "issued_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_session_token(token: str, client_ip: str, user_agent: str) -> Optional[dict]:
    """Verify and decode session token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])

        # Check expiry
        expires_at = datetime.fromisoformat(payload["expires_at"])
        if datetime.utcnow() > expires_at:
            return None

        # Verify client fingerprint
        expected_ua_hash = hashlib.sha256(user_agent.encode()).hexdigest()[:16]
        if payload.get("user_agent") != expected_ua_hash:
            return None

        return payload
    except (jwt.InvalidTokenError, ValueError, KeyError):
        return None


def create_n8n_token(
    session_id: str, message_history: list = None, session_metadata: dict = None
) -> str:
    """Create JWT token for n8n validation"""
    payload = {
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat(),
        "message_history": message_history or [],
        "session_metadata": session_metadata or {},
        "exp": datetime.utcnow() + timedelta(seconds=30),  # Short-lived token
    }
    return jwt.encode(payload, SESSION_SECRET, algorithm="HS256")


# Dependency for rate limiting
async def check_rate_limit(request: Request):
    client_ip = get_client_ip(request)
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    return client_ip


# Routes
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "mode": "stateless",
        "features": {
            "database": False,
            "browser_storage": True,
            "n8n_integration": True,
            "rate_limiting": True,
        },
    }


@app.post("/api/v1/session/create")
async def create_session(
    request: Request,
    session_data: SessionCreate,
    client_ip: str = Depends(check_rate_limit),
):
    """Create or validate a session (stateless)"""
    user_agent = request.headers.get("User-Agent", "unknown")

    # Use provided session ID or generate new one
    session_id = (
        session_data.session_id or f"sess_{int(time.time())}_{str(uuid.uuid4())[:8]}"
    )

    # Create session token
    session_token = create_session_token(session_id, client_ip, user_agent)

    response = {
        "session_id": session_id,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "client_managed": True,
    }

    # Set HTTP-only cookie for token
    http_response = Response(content=response.__str__(), media_type="application/json")
    http_response.set_cookie(
        key="chat_session",
        value=session_token,
        max_age=30 * 24 * 60 * 60,  # 30 days
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
    )

    return response


@app.get("/api/v1/session/validate")
async def validate_session(
    request: Request, client_ip: str = Depends(check_rate_limit)
):
    """Validate session token"""
    user_agent = request.headers.get("User-Agent", "unknown")
    session_token = request.cookies.get("chat_session")

    if not session_token:
        raise HTTPException(status_code=401, detail="No session token")

    payload = verify_session_token(session_token, client_ip, user_agent)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid session token")

    return {
        "valid": True,
        "session_id": payload["session_id"],
        "issued_at": payload["issued_at"],
        "expires_at": payload["expires_at"],
    }


@app.post("/api/v1/chat/stream")
async def stream_chat(
    request: Request,
    message_data: ChatMessage,
    client_ip: str = Depends(check_rate_limit),
):
    """Stream chat response from n8n"""
    user_agent = request.headers.get("User-Agent", "unknown")
    session_token = request.cookies.get("chat_session")

    # Validate session if token exists (optional for stateless mode)
    session_id = message_data.session_id
    if session_token:
        payload = verify_session_token(session_token, client_ip, user_agent)
        if payload:
            session_id = payload["session_id"]

    # Use provided session_id or generate ephemeral one
    if not session_id:
        session_id = f"temp_{int(time.time())}_{str(uuid.uuid4())[:8]}"

    # Create n8n token with session data
    n8n_token = create_n8n_token(
        session_id, message_data.message_history, message_data.session_metadata
    )

    async def stream_from_n8n():
        try:
            headers = {
                "Authorization": f"Bearer {n8n_token}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }

            payload = {
                "message": message_data.message,
                "timestamp": datetime.utcnow().isoformat(),
                "jwt_token": n8n_token,
                "session": {
                    "session_id": session_id,
                    "origin_domain": message_data.page_url.split("/")[2]
                    if message_data.page_url
                    else "unknown",
                    "page_url": message_data.page_url,
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                    "timestamp": time.time(),
                },
            }

            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST", N8N_WEBHOOK_URL, headers=headers, json=payload, timeout=30.0
                ) as response:
                    if response.status_code != 200:
                        yield f"data: Error: Failed to connect to AI service (status: {response.status_code})\n\n"
                        yield "data: [DONE]\n\n"
                        return

                    async for chunk in response.aiter_text():
                        if chunk.strip():
                            # Forward n8n chunks directly
                            yield f"data: {chunk}\n\n"

                    yield "data: [DONE]\n\n"

        except httpx.TimeoutException:
            yield "data: Error: Request timeout\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: Error: {str(e)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_from_n8n(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Access-Control-Allow-Origin": request.headers.get("Origin", "*"),
            "Access-Control-Allow-Credentials": "true",
        },
    )


# Alternative GET endpoint for simple streaming
@app.get("/api/v1/chat/stream")
async def stream_chat_get(
    request: Request,
    message: str,
    session_id: Optional[str] = None,
    page_url: Optional[str] = None,
    client_ip: str = Depends(check_rate_limit),
):
    """GET endpoint for streaming (for simple integrations)"""
    # Convert to POST-style message data
    message_data = ChatMessage(
        message=message,
        session_id=session_id,
        page_url=page_url,
        message_history=[],
        session_metadata={},
    )

    return await stream_chat(request, message_data, client_ip)


@app.get("/metrics")
async def get_metrics():
    """Basic metrics endpoint"""
    total_requests = sum(sum(counts.values()) for counts in request_counts.values())

    return {
        "active_ips": len(request_counts),
        "total_requests_recent": total_requests,
        "rate_limit_per_minute": RATE_LIMIT_PER_MINUTE,
        "uptime_seconds": time.time() - app.state.start_time
        if hasattr(app.state, "start_time")
        else 0,
    }


# Static file serving for widget (optional)
@app.get("/widget/{file_path:path}")
async def serve_widget_files(file_path: str):
    """Serve widget static files"""
    import os

    from fastapi.responses import FileResponse

    widget_dir = "../chat-widget/dist"
    full_path = os.path.join(widget_dir, file_path)

    if os.path.exists(full_path) and os.path.isfile(full_path):
        return FileResponse(full_path)

    raise HTTPException(status_code=404, detail="File not found")


# Startup event
@app.on_event("startup")
async def startup_event():
    app.state.start_time = time.time()
    logger.info(f"🚀 Stateless Chat Proxy started on {API_HOST}:{API_PORT}")
    logger.info(f"📡 n8n webhook: {N8N_WEBHOOK_URL}")
    logger.info(f"🌐 Allowed origins: {ALLOWED_ORIGINS}")
    logger.info(f"⚡ Rate limit: {RATE_LIMIT_PER_MINUTE} requests/minute")


if __name__ == "__main__":
    uvicorn.run(
        "main_stateless:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,  # Disable for production
        log_level="warning",
    )
