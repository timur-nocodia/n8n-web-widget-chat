# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## IMPORTANT RULES

YOU ARE NOT ALLOWED TO DO SIMPLIFICATION OR COMPLICATION WITHOUT USER'S PERMISSION!!!
No 'more robust solutions' and such. YOU ALWAYS ASK BEFORE DOING THINGS ANOTHER WAY!

## Project Overview

This is a secure chat proxy system for e-commerce platforms, built with a standalone HTML frontend and FastAPI Python backend. The system acts as a secure intermediary between embedded chat widgets and n8n workflows for AI-powered customer support.

## Architecture

The project has two main components:

- **chat-widget** (`apps/chat-widget/`): Standalone HTML chat widget that embeds via iframe on websites
- **proxy-server** (`apps/proxy-server/`): FastAPI Python server that handles authentication, rate limiting, and n8n integration

### Deployment Modes

The proxy server supports two deployment modes:

1. **Stateless Mode** (`main_stateless.py`) - Recommended for most use cases:
   - Zero database dependencies
   - All session data stored browser-side (IndexedDB + localStorage)  
   - Ultra-fast performance with <10ms latency
   - Horizontally scalable with no shared state
   - In-memory rate limiting (resets on server restart)

2. **SQLite Mode** (`main_sqlite.py`) - Lightweight with analytics:
   - Single SQLite file for session metadata
   - Browser-first storage with server-side session tracking
   - Persistent rate limiting across restarts
   - Auto-cleanup of old data
   - Easy backup (single .db file)

### Common Components

All modes use:
- n8n workflows for AI processing
- JWT tokens with dual-key system (JWT_SECRET_KEY for internal, SESSION_SECRET_KEY for n8n)
- Server-sent events (SSE) for real-time chat streaming
- Browser fingerprinting for session validation

## Common Development Commands

### Project Setup
```bash
# Docker-based setup (recommended)
./scripts/setup.sh

# Manual setup (if not using Docker)
npm install  # Install root dependencies
cd apps/chat-widget && npm install
cd apps/proxy-server && pip install -r requirements.txt
```

### Development
```bash
# Backend modes (choose one):
cd apps/proxy-server && python main_stateless.py    # Stateless mode (no dependencies)
cd apps/proxy-server && python main_sqlite.py       # SQLite mode (minimal dependencies)

# Widget is served automatically by the backend at /widget/modern-widget.html

# Docker Compose (optional - if using containerized development)
cd infrastructure/docker
docker-compose up --build
```

### Production Server
```bash
# Production deployment options:
cd apps/proxy-server && pip install -r requirements-stateless.txt && python main_stateless.py  # Stateless (recommended)
cd apps/proxy-server && pip install -r requirements-sqlite.txt && python main_sqlite.py        # SQLite

# Production server (if exists):
cd apps/proxy-server && python main_production.py  # Check if this file exists

# Or with Docker
docker-compose up -d  # Root directory docker-compose.yml
```

### Building and Testing
```bash
# Backend linting
cd apps/proxy-server && ruff check . && black --check .

# Security testing
./scripts/test-security.sh
```

## Key File Structure

### Frontend (Standalone HTML)
- `apps/chat-widget/modern-widget.html`: Complete standalone chat widget with SSE streaming
- `apps/chat-widget/public/embed.js`: JavaScript embed script for websites
- `apps/chat-widget/widget-config.json`: Widget configuration file

### Backend (FastAPI Python)

**Entry Points:**
- `apps/proxy-server/main_stateless.py`: Stateless server (no database dependencies)
- `apps/proxy-server/main_sqlite.py`: SQLite server (lightweight single-file database)
- `apps/proxy-server/main_production.py`: Production server entry point (if exists)

## Configuration

### Environment Files
- `apps/proxy-server/.env`: Backend configuration (create from .env.example)
- Docker Compose passes environment variables for containerized development

### Key Environment Variables

**Common (All Modes):**
```bash
# n8n Integration
N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/chat
N8N_API_KEY=<optional-api-key>

# Security
JWT_SECRET_KEY=<secure-secret>    # For internal session tokens
SESSION_SECRET_KEY=<secure-secret>  # For n8n validation tokens
ALLOWED_ORIGINS=https://yoursite.com,http://localhost:8000

# Server
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=WARNING  # INFO for development, WARNING for production

# Rate Limiting  
RATE_LIMIT_PER_MINUTE=60
```

**SQLite Mode Additional:**
```bash
SQLITE_DB_PATH=chat_sessions.db  # Database file path
```


## Widget Integration

### Embed on website
```html
<script>
  (function() {
    var script = document.createElement('script');
    script.src = 'https://yourchatserver.com/widget/embed.js';
    script.async = true;
    document.head.appendChild(script);
  })();
</script>
```

### Direct iframe
```html
<iframe src="https://yourchatserver.com/widget/modern-widget.html" 
        width="400" height="600" style="border: none;">
</iframe>
```

## API Endpoints

### Core Endpoints
- `GET /health`: Detailed health status with service checks
- `GET /metrics`: System metrics and connection stats
- `POST /api/v1/session/create`: Create secure chat session
- `GET /api/v1/session/validate`: Validate existing session
- `POST /api/v1/chat/message`: Send message (SSE stream response)
- `GET /api/v1/chat/stream/{session_id}`: SSE endpoint for real-time updates
- `GET /widget/*`: Serve widget static files

## n8n Integration

The system integrates with n8n for AI processing:
- Configure webhook URL in n8n workflow
- Enable streaming response in webhook settings
- JWT tokens passed in request body as `jwt_token` field (not Authorization header)
- Supports SSE for real-time streaming responses

### JWT Token Format for n8n
All modes send JWT tokens with this payload structure to n8n:
```json
{
  "session_id": "sess_1234567890_abcd1234",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "message_history": [],
  "session_metadata": {},
  "exp": 1704105630
}
```

## Security Features

- JWT-based authentication with browser fingerprinting
- Multi-tier rate limiting (IP, session, domain)
- Input sanitization and XSS protection
- Comprehensive security headers and CORS
- Bot and spam detection
- Circuit breaker pattern for external services
- Session validation and expiry
- Request signature validation

## Deployment Mode Selection

### When to Use Each Mode

- **Stateless Mode**: Recommended for most use cases
  - Zero maintenance, instant deployment
  - Scales infinitely, no database overhead
  - Perfect for startups and high-traffic sites
  - Users retain chat history in browser storage

- **SQLite Mode**: When you need basic server-side analytics  
  - Single file database, easy backup
  - Session tracking and usage analytics
  - Still lightweight with browser-first storage
  - Good middle ground option

## Development Tips

1. **Quick Testing**: Start with stateless mode (`python main_stateless.py`) - no setup required
2. **Testing Widget**: Visit `http://localhost:8000/widget/modern-widget.html`
3. **EventSource Compatibility**: All modes support both POST and GET endpoints for SSE streaming
4. **Logs**: Check server console output or use `docker-compose logs -f [service]` if using Docker
5. **Rate Limits**: Can be tested with `./scripts/test-security.sh`

## Important Implementation Notes

- Widget embeds via iframe for security isolation
- All user inputs are sanitized for XSS/injection protection  
- JWT tokens use dual-key system: JWT_SECRET_KEY (internal) + SESSION_SECRET_KEY (n8n validation)
- n8n integration requires `jwt_token` field in request body (not Authorization header)
- EventSource/SSE streaming requires GET endpoints for browser compatibility
- Stateless mode: Rate limiting is in-memory (resets on server restart)
- SQLite mode: Uses aiosqlite for async database operations with persistent rate limiting
- SSE connections managed with heartbeat and cleanup

### Critical Architecture Patterns

- **Browser-First Storage**: Even SQLite mode prioritizes browser storage for chat history
- **Dual JWT System**: Internal tokens for session validation, short-lived tokens for n8n
- **Multi-Mode Compatibility**: All modes share the same JWT payload format for n8n
- **EventSource Support**: GET endpoints wrap POST logic for browser EventSource API

### Rules from user