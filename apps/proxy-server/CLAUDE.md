# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the proxy-server backend code.

## IMPORTANT RULES

YOU ARE NOT ALLOWED TO DO SIMPLIFICATION OR COMPLICATION WITHOUT USER'S PERMISSION!!!
No 'more robust solutions' and such. YOU ALWAYS ASK BEFORE DOING THINGS ANOTHER WAY!

## Backend Overview

This is a FastAPI-based secure chat proxy server that handles authentication, rate limiting, and forwards requests to n8n workflows for AI processing. It serves as a secure intermediary between embedded chat widgets and n8n.

## Architecture

The backend supports multiple deployment modes:

### Stateless Mode (Recommended)
- **FastAPI** with async/await for high performance
- **No database dependencies** - all session data in browser
- **In-memory rate limiting** (resets on restart)
- **JWT tokens** with dual-key system (JWT_SECRET_KEY for internal, SESSION_SECRET_KEY for n8n)
- **SSE (Server-Sent Events)** for real-time streaming responses

### SQLite Mode (Optional)
- Lightweight **SQLite** database for session tracking
- **Persistent rate limiting** across restarts
- **Aiosqlite** for async database operations
- Simple backup (single .db file)

### Production Mode
- Optimized for production deployment
- Simplified dependencies for stability
- Multi-worker support

## Project Structure

```
apps/proxy-server/
├── main_stateless.py            # Stateless server (no database)
├── main_sqlite.py              # SQLite server (lightweight database)
├── main_production.py          # Production-optimized server
├── requirements-stateless.txt  # Minimal dependencies for stateless mode
├── requirements-sqlite.txt     # Dependencies for SQLite mode
├── requirements.txt            # Full dependencies (legacy)
├── chat_sessions.db           # SQLite database file (SQLite mode only)
└── README.md                   # Backend documentation
```

## Development Commands

### Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies based on deployment mode
pip install -r requirements-stateless.txt  # For stateless mode (recommended)
# OR
pip install -r requirements-sqlite.txt     # For SQLite mode

# Copy and configure environment (from root directory)
cp .env.example .env
# Edit .env with your configuration
```

### Storage Setup
```bash
# No database setup needed for stateless mode
# SQLite mode: Database file is auto-created on first run
# Production mode: Follow deployment-specific configuration
```

### Running the Server
```bash
# Stateless mode (recommended - no database)
python main_stateless.py

# SQLite mode (with lightweight database)
python main_sqlite.py

# Production mode (optimized)
python main_production.py

# With specific environment variables
LOG_LEVEL=DEBUG python main_stateless.py

# Using Docker
docker-compose up
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

### Environment Variables

All environment variables are configured in the root `.env` file. See `.env.example` in the project root for complete configuration options.

Key variables include:
- `DEPLOYMENT_MODE`: Choose between stateless, sqlite, or production
- `N8N_WEBHOOK_URL`: Your n8n webhook endpoint
- `JWT_SECRET_KEY` and `SESSION_SECRET_KEY`: Security tokens
- `ALLOWED_ORIGINS`: Domains that can embed the widget
- `RATE_LIMIT_PER_MINUTE`: Request throttling

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
- **Stateless Mode**: In-memory rate limiting (resets on restart)
- **SQLite Mode**: Persistent rate limiting in database
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

1. **Quick Start**: Use stateless mode for instant development
2. **Error Handling**: All exceptions logged, graceful fallbacks
3. **Testing SSE**: Use `curl -N http://localhost:8000/api/v1/chat/stream`
4. **Debug Mode**: Set `LOG_LEVEL=DEBUG` for detailed logging
5. **Rate Limits**: Can be tested with `./scripts/test-security.sh`

## Production Considerations

1. **Secrets**: Use strong, unique keys for JWT_SECRET_KEY and SESSION_SECRET_KEY
2. **Deployment Mode**: Choose appropriate mode based on requirements
3. **Workers**: Run with multiple uvicorn workers for production mode
4. **Monitoring**: Enable metrics endpoint, use APM tools
5. **HTTPS**: Always use TLS in production
6. **CORS**: Restrict ALLOWED_ORIGINS to actual domains
7. **Backup**: For SQLite mode, backup the .db file regularly

## Common Issues & Solutions

### SSE Not Streaming
- Check `X-Accel-Buffering: no` header
- Ensure nginx has `proxy_buffering off`
- Verify chunked transfer encoding

### Rate Limiting Too Aggressive
- Adjust RATE_LIMIT_PER_MINUTE in .env
- For stateless mode: Rate limits reset on server restart
- For SQLite mode: Check database file permissions

### Storage Issues
- **Stateless Mode**: Check browser storage (IndexedDB/localStorage)
- **SQLite Mode**: Verify write permissions for .db file
- **Production Mode**: Check deployment-specific configuration

### CORS Errors
- Add origin to ALLOWED_ORIGINS
- Ensure credentials are included in requests

## Important Implementation Notes

- All user inputs are sanitized for security
- JWT tokens expire and auto-refresh
- **Stateless Mode**: Sessions stored entirely in browser
- **SQLite Mode**: Sessions tracked in lightweight database
- Circuit breaker prevents cascade failures
- All async operations are properly handled
- Production server (`main_production.py`) has simplified dependencies for stability