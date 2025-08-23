# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the proxy-server backend code.

## IMPORTANT RULES

YOU ARE NOT ALLOWED TO DO SIMPLIFICATION OR COMPLICATION WITHOUT USER'S PERMISSION!!!
No 'more robust solutions' and such. YOU ALWAYS ASK BEFORE DOING THINGS ANOTHER WAY!

## Backend Overview

This is a FastAPI-based secure chat proxy server that handles authentication, rate limiting, and forwards requests to n8n workflows for AI processing. It serves as a secure intermediary between embedded chat widgets and n8n.

## Architecture

The backend uses:
- **FastAPI** with async/await for high performance
- **PostgreSQL** (async via asyncpg) for session persistence
- **Redis** for rate limiting and caching
- **JWT tokens** with dual-key system (JWT_SECRET_KEY for internal, SESSION_SECRET_KEY for n8n)
- **SSE (Server-Sent Events)** for real-time streaming responses
- **SQLAlchemy** with async support for ORM
- **Alembic** for database migrations

## Project Structure

```
apps/proxy-server/
├── src/
│   ├── main.py                 # Main FastAPI app with middleware setup
│   ├── api/v1/
│   │   ├── router.py           # API route aggregation
│   │   ├── deps.py             # Dependency injection
│   │   ├── schemas.py          # Pydantic models
│   │   └── endpoints/
│   │       ├── chat.py         # Chat endpoints (message, stream)
│   │       └── session.py      # Session management endpoints
│   ├── core/
│   │   ├── config.py           # Settings via pydantic-settings
│   │   ├── security.py         # JWT, encryption, threat detection
│   │   ├── session.py          # Session management logic
│   │   ├── validation.py       # Input validation and sanitization
│   │   └── exceptions.py       # Custom exception classes
│   ├── db/
│   │   └── base.py             # Database setup and connection
│   ├── middleware/
│   │   ├── security.py         # Security headers, CORS, origin validation
│   │   ├── rate_limiting.py    # Rate limiting middleware
│   │   └── error_handling.py   # Error handling, circuit breaker
│   ├── models/
│   │   ├── session.py          # Session SQLAlchemy model
│   │   └── chat.py             # Chat message model
│   └── services/
│       ├── jwt_service.py      # JWT token generation/validation
│       ├── n8n_client.py       # n8n webhook communication
│       ├── rate_limiter.py     # Redis-based rate limiting
│       └── sse_manager.py      # SSE connection management
├── main.py                      # Development entry point
├── main_production.py           # Production-optimized server
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container configuration
├── .env.example                 # Environment template
└── README.md                    # Backend documentation
```

## Development Commands

### Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your configuration
```

### Database Setup
```bash
# No database setup needed for stateless/SQLite modes
# SQLite schema is auto-created on startup
```

### Running the Server
```bash
# Development mode with hot reload
python src/main.py

# Production mode (simplified, no complex dependencies)
python main_production.py

# Production with multiple workers
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4

# With specific environment
LOG_LEVEL=DEBUG python src/main.py
```


### Code Quality
```bash
# Format code
black .
black --check .  # Check only

# Lint
ruff check .
ruff check . --fix  # Auto-fix issues

# Type checking
mypy src/
```

## Configuration

### Environment Variables (.env)

```bash
# Server Configuration
APP_NAME=chat-proxy
DEBUG=True                      # Set False for production
LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/chat_proxy

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT Configuration
JWT_SECRET_KEY=<generate-secure-key>      # For internal JWT
SESSION_SECRET_KEY=<generate-secure-key>  # For n8n JWT validation
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24                   # Session duration

# n8n Integration
N8N_WEBHOOK_URL=https://your-n8n.com/webhook/chat
N8N_API_KEY=<optional-api-key>

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
CORS_ALLOW_CREDENTIALS=True

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Session
SESSION_COOKIE_NAME=chat_session_id
SESSION_COOKIE_MAX_AGE=86400
```

## API Endpoints

### Session Management
```bash
POST /api/v1/session/create
# Body: {"origin_domain": "example.com", "page_url": "https://example.com/page"}
# Response: {"session_id": "...", "expires_at": ...}
# Sets HttpOnly cookie: chat_session_id

GET /api/v1/session/validate
# Requires: chat_session_id cookie
# Response: {"valid": true, "session_id": "...", "origin_domain": "..."}
```

### Chat Operations
```bash
POST /api/v1/chat/message
# Body: {"message": "Hello", "page_url": "https://example.com"}
# Requires: chat_session_id cookie
# Response: SSE stream with real-time chunks

POST /api/v1/chat/stream
# Alternative streaming endpoint
# Same as /message but explicit streaming

GET /api/v1/chat/history/{session_id}
# Get chat history for session
```

### Health & Monitoring
```bash
GET /health
# Response: {"status": "healthy", "services": {...}, "config": {...}}

GET /metrics
# Response: {"connections": {...}, "rate_limits": {...}}
```

## Key Components

### JWT Token System
- **JWT_SECRET_KEY**: Used for internal session tokens
- **SESSION_SECRET_KEY**: Used for n8n validation tokens
- Tokens include browser fingerprinting for security
- 30-second expiration for n8n tokens (configurable)

### SSE Streaming
- Real-time message streaming from n8n
- Handles chunked responses byte-by-byte
- Automatic reconnection and heartbeat
- Custom SSEResponse class forces immediate flushing

### Rate Limiting
- Redis-based sliding window algorithm
- Multi-tier: IP-based, session-based, domain-based
- Configurable limits per minute/hour
- Automatic cleanup of expired entries

### Security Middleware Stack
1. **SecurityHeadersMiddleware**: CSP, XSS protection, frame options
2. **TrustedHostMiddleware**: Host header validation
3. **OriginValidationMiddleware**: CORS origin checking
4. **RequestSizeMiddleware**: Payload size limits
5. **RateLimitMiddleware**: Request throttling
6. **CircuitBreakerMiddleware**: External service protection

### n8n Integration
- Webhook-based communication
- JWT token passed in request for validation
- Supports both streaming and non-streaming responses
- Handles n8n JSON chunks: `{"type": "item", "content": "..."}`

## Development Tips

1. **Database Connections**: Uses async SQLAlchemy with connection pooling
2. **Error Handling**: All exceptions logged, graceful fallbacks
3. **Testing SSE**: Use `curl -N http://localhost:8000/api/v1/chat/stream`
4. **Debug Mode**: Set `DEBUG=True` for detailed logging
5. **Rate Limits**: Can be tested with `./scripts/test-security.sh`

## Production Considerations

1. **Secrets**: Use strong, unique keys for JWT_SECRET_KEY and SESSION_SECRET_KEY
2. **Database**: Configure connection pooling (max_overflow, pool_size)
3. **Redis**: Use Redis Sentinel or Cluster for HA
4. **Workers**: Run with multiple uvicorn workers
5. **Monitoring**: Enable metrics endpoint, use APM tools
6. **HTTPS**: Always use TLS in production
7. **CORS**: Restrict ALLOWED_ORIGINS to actual domains

## Common Issues & Solutions

### SSE Not Streaming
- Check `X-Accel-Buffering: no` header
- Ensure nginx has `proxy_buffering off`
- Verify chunked transfer encoding

### Rate Limiting Too Aggressive
- Adjust RATE_LIMIT_PER_MINUTE in .env
- Check Redis connection and memory

### Database Connection Errors
- Verify PostgreSQL is running
- Check DATABASE_URL format
- No database migrations needed (SQLite schema auto-created)

### CORS Errors
- Add origin to ALLOWED_ORIGINS
- Ensure credentials are included in requests

## Important Implementation Notes

- All user inputs sanitized via `validation.py`
- JWT tokens expire and auto-refresh
- Sessions stored in PostgreSQL, cached in Redis
- Circuit breaker prevents cascade failures
- All async operations use proper connection pooling
- Production server (`main_production.py`) has simplified dependencies for stability