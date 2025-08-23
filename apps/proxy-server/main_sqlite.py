#!/usr/bin/env python3
"""
Lightweight Chat Proxy Server with SQLite
Minimal database storage with browser-first approach
"""

import os
import uuid
import time
import sqlite3
import asyncio
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

import jwt
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import httpx
import uvicorn

# Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "https://your-n8n.com/webhook/chat")
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "your-super-secure-jwt-secret-change-this")
SESSION_SECRET = os.getenv("SESSION_SECRET_KEY", "your-session-secret-change-this")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:8000").split(",")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", 60))
DB_PATH = os.getenv("SQLITE_DB_PATH", "chat_sessions.db")

app = FastAPI(
    title="SQLite Chat Proxy",
    version="1.0.0",
    description="Lightweight chat proxy with SQLite storage"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Models
class ChatMessage(BaseModel):
    message: str = Field(..., max_length=10000)
    page_url: Optional[str] = None
    session_id: Optional[str] = None

class SessionCreate(BaseModel):
    origin_domain: Optional[str] = None
    page_url: Optional[str] = None

# Database initialization
async def init_database():
    """Initialize SQLite database with minimal schema"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Sessions table (minimal)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                origin_domain TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # Optional: Message summary table (for analytics)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS session_summary (
                session_id TEXT PRIMARY KEY,
                message_count INTEGER DEFAULT 0,
                first_message TEXT,
                last_message_at TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        """)
        
        # Rate limiting table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS rate_limits (
                client_ip TEXT,
                minute_bucket INTEGER,
                request_count INTEGER DEFAULT 0,
                PRIMARY KEY (client_ip, minute_bucket)
            )
        """)
        
        await db.commit()

# Utility functions
def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

async def check_rate_limit(client_ip: str) -> bool:
    """SQLite-based rate limiting"""
    current_minute = int(time.time() // 60)
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Clean old entries
        await db.execute(
            "DELETE FROM rate_limits WHERE minute_bucket < ?",
            (current_minute - 5,)  # Keep 5 minutes of history
        )
        
        # Get current count
        cursor = await db.execute(
            "SELECT request_count FROM rate_limits WHERE client_ip = ? AND minute_bucket = ?",
            (client_ip, current_minute)
        )
        result = await cursor.fetchone()
        current_count = result[0] if result else 0
        
        if current_count >= RATE_LIMIT_PER_MINUTE:
            return False
        
        # Increment counter
        await db.execute("""
            INSERT OR REPLACE INTO rate_limits (client_ip, minute_bucket, request_count)
            VALUES (?, ?, COALESCE((SELECT request_count FROM rate_limits WHERE client_ip = ? AND minute_bucket = ?), 0) + 1)
        """, (client_ip, current_minute, client_ip, current_minute))
        
        await db.commit()
        return True

async def create_session(origin_domain: str = None) -> str:
    """Create new session in SQLite"""
    session_id = f"sess_{int(time.time())}_{str(uuid.uuid4())[:8]}"
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO sessions (id, origin_domain, created_at, last_activity)
            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (session_id, origin_domain))
        
        # Initialize summary
        await db.execute("""
            INSERT INTO session_summary (session_id, message_count)
            VALUES (?, 0)
        """, (session_id,))
        
        await db.commit()
    
    return session_id

async def update_session_activity(session_id: str, message_content: str = None):
    """Update session last activity and optionally message summary"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE sessions SET last_activity = CURRENT_TIMESTAMP WHERE id = ?
        """, (session_id,))
        
        if message_content:
            # Update message summary
            await db.execute("""
                UPDATE session_summary 
                SET message_count = message_count + 1,
                    last_message_at = CURRENT_TIMESTAMP,
                    first_message = COALESCE(first_message, ?)
                WHERE session_id = ?
            """, (message_content[:100], session_id))
        
        await db.commit()

async def get_session_info(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session information"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT s.id, s.created_at, s.last_activity, s.origin_domain, s.is_active,
                   ss.message_count, ss.first_message
            FROM sessions s
            LEFT JOIN session_summary ss ON s.id = ss.session_id
            WHERE s.id = ? AND s.is_active = 1
        """, (session_id,))
        
        result = await cursor.fetchone()
        if result:
            return {
                'id': result[0],
                'created_at': result[1],
                'last_activity': result[2],
                'origin_domain': result[3],
                'is_active': result[4],
                'message_count': result[5] or 0,
                'first_message': result[6]
            }
        return None

# Dependencies
async def rate_limit_dependency(request: Request):
    client_ip = get_client_ip(request)
    if not await check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    return client_ip

# Routes
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "storage": "sqlite",
        "database": DB_PATH,
        "features": {
            "lightweight_db": True,
            "browser_first": True,
            "session_tracking": True
        }
    }

@app.post("/api/v1/session/create")
async def create_session_endpoint(
    request: Request,
    session_data: SessionCreate,
    client_ip: str = Depends(rate_limit_dependency)
):
    """Create lightweight session"""
    session_id = await create_session(session_data.origin_domain)
    
    # Create simple JWT token
    payload = {
        'session_id': session_id,
        'created_at': datetime.utcnow().isoformat(),
        'exp': datetime.utcnow() + timedelta(days=30)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    
    response = {
        "session_id": session_id,
        "created_at": payload['created_at'],
        "storage_type": "hybrid",  # SQLite + Browser
        "lightweight": True
    }
    
    # Set cookie
    http_response = Response(content=str(response), media_type="application/json")
    http_response.set_cookie(
        key="chat_session",
        value=token,
        max_age=30 * 24 * 60 * 60,
        httponly=True,
        samesite="lax"
    )
    
    return response

@app.post("/api/v1/chat/stream")
async def stream_chat_sqlite(
    request: Request,
    message_data: ChatMessage,
    client_ip: str = Depends(rate_limit_dependency)
):
    """Stream chat with lightweight SQLite tracking"""
    session_id = message_data.session_id
    
    # Validate/get session from SQLite
    if session_id:
        session_info = await get_session_info(session_id)
        if not session_info:
            # Create ephemeral session
            session_id = await create_session()
    else:
        session_id = await create_session()
    
    # Update session activity
    await update_session_activity(session_id, message_data.message)
    
    # Create n8n token (matching stateless format)
    n8n_payload = {
        'session_id': session_id,
        'timestamp': datetime.utcnow().isoformat(),
        'message_history': [],  # Empty for SQLite version
        'session_metadata': {},  # Empty for SQLite version
        'exp': datetime.utcnow() + timedelta(seconds=30)
    }
    n8n_token = jwt.encode(n8n_payload, SESSION_SECRET, algorithm='HS256')
    
    async def stream_response():
        
        try:
            headers = {
                'Content-Type': 'application/json'
            }
            
            payload = {
                'message': message_data.message,
                'timestamp': datetime.utcnow().isoformat(),
                'jwt_token': n8n_token,
                'session': {
                    'session_id': session_id,
                    'origin_domain': message_data.page_url.split('/')[2] if message_data.page_url else 'unknown',
                    'page_url': message_data.page_url,
                    'client_ip': client_ip,
                    'timestamp': time.time()
                }
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream('POST', N8N_WEBHOOK_URL, headers=headers, json=payload) as response:
                    if response.status_code == 200:
                        async for chunk in response.aiter_text():
                            if chunk.strip():
                                yield f"data: {chunk}\n\n"
                        yield "data: [DONE]\n\n"
                    else:
                        yield f"data: Error: Service unavailable\n\n"
                        yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/v1/chat/stream")
async def stream_chat_sqlite_get(
    request: Request,
    message: str,
    page_url: str = "",
    session_id: str = None,
    client_ip: str = Depends(rate_limit_dependency)
):
    """Stream chat via GET for EventSource compatibility"""
    # Convert GET parameters to POST-like data
    message_data = ChatMessage(
        message=message,
        page_url=page_url,
        session_id=session_id
    )
    
    # Reuse the POST logic
    return await stream_chat_sqlite(request, message_data, client_ip)

@app.get("/api/v1/session/stats")
async def get_session_stats():
    """Get basic session statistics"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Active sessions
        cursor = await db.execute("SELECT COUNT(*) FROM sessions WHERE is_active = 1")
        active_sessions = (await cursor.fetchone())[0]
        
        # Total messages today
        cursor = await db.execute("""
            SELECT SUM(message_count) FROM session_summary ss
            JOIN sessions s ON ss.session_id = s.id
            WHERE date(s.created_at) = date('now')
        """)
        messages_today = (await cursor.fetchone())[0] or 0
        
        # Database size
        db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
        
        return {
            "active_sessions": active_sessions,
            "messages_today": messages_today,
            "database_size_bytes": db_size,
            "storage_type": "sqlite"
        }

# Cleanup task
async def cleanup_old_data():
    """Clean up old sessions and rate limit data"""
    while True:
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            async with aiosqlite.connect(DB_PATH) as db:
                # Deactivate old sessions
                await db.execute("""
                    UPDATE sessions SET is_active = 0 
                    WHERE last_activity < ?
                """, (cutoff_date,))
                
                # Clean old rate limit data
                await db.execute("""
                    DELETE FROM rate_limits 
                    WHERE minute_bucket < ?
                """, (int(time.time() // 60) - 1440,))  # Keep 24 hours
                
                await db.commit()
                
            await asyncio.sleep(3600)  # Run every hour
        except Exception as e:
            print(f"Cleanup error: {e}")
            await asyncio.sleep(3600)

@app.on_event("startup")
async def startup_event():
    await init_database()
    # Start cleanup task
    asyncio.create_task(cleanup_old_data())
    print(f"🚀 SQLite Chat Proxy started on {API_HOST}:{API_PORT}")
    print(f"💾 Database: {DB_PATH}")

if __name__ == "__main__":
    uvicorn.run(
        "main_sqlite:app",
        host=API_HOST,
        port=API_PORT,
        reload=False
    )