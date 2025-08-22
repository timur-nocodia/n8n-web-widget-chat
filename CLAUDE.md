# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a secure chat proxy system for e-commerce platforms, built with a React TypeScript frontend and FastAPI Python backend. The system acts as a secure intermediary between embedded chat widgets and n8n workflows for AI-powered customer support.

## Architecture

The project consists of two main applications in a monorepo:

- **chat-widget** (`apps/chat-widget/`): React TypeScript chat widget that can be embedded on websites
- **proxy-server** (`apps/proxy-server/`): FastAPI Python server that handles authentication, rate limiting, and n8n integration

The system uses:
- PostgreSQL for session storage
- Redis for rate limiting and caching  
- n8n workflows for AI processing
- JWT tokens for secure authentication
- Server-sent events (SSE) for real-time chat streaming

## Common Development Commands

### Project Setup
```bash
# Initial setup with Docker
./scripts/setup.sh

# Manual development setup
npm run setup      # Root level setup
```

### Development
```bash
# Start all services in development
npm run dev        # Uses turbo to run all apps
turbo dev          # Alternative turbo command

# Individual services
cd apps/chat-widget && npm run dev    # Frontend on port 5173
cd apps/proxy-server && python src/main.py  # Backend on port 8000

# Using Docker Compose
cd infrastructure/docker
docker-compose up --build
```

### Building and Testing
```bash
# Build all apps
npm run build
turbo build

# Individual builds
cd apps/chat-widget && npm run build && npm run type-check
cd apps/proxy-server && python -m pytest

# Linting
npm run lint
turbo lint

cd apps/chat-widget && npm run lint
```

### Security Testing
```bash
./scripts/test-security.sh
```

## Key Components

### Frontend (React TypeScript)
- **Embed script** (`apps/chat-widget/src/embed.ts`): Creates iframe-based widget for embedding
- **Chat components** in `apps/chat-widget/src/components/`: Modular React components
- **API integration** (`apps/chat-widget/src/services/api.ts`): Handles backend communication
- **SSE streaming** (`apps/chat-widget/src/hooks/useSSE.ts`): Real-time message streaming

### Backend (FastAPI Python)
- **Main application** (`apps/proxy-server/src/main.py`): FastAPI app with comprehensive middleware
- **Security layer** (`apps/proxy-server/src/core/security.py`): JWT, session management, threat detection
- **Rate limiting** (`apps/proxy-server/src/services/rate_limiter.py`): Redis-based sliding window rate limits
- **n8n client** (`apps/proxy-server/src/services/n8n_client.py`): Handles n8n webhook integration with streaming
- **Database models** in `apps/proxy-server/src/models/`: SQLAlchemy models for sessions and chats

### Security Features
- JWT-based authentication with browser fingerprinting
- Multi-tier rate limiting (IP, session, domain)
- Input sanitization and XSS protection
- Comprehensive security headers and CORS
- Bot and spam detection
- Circuit breaker pattern for external services

## Configuration

### Environment Files
- `apps/proxy-server/.env`: Backend configuration (JWT secrets, database URLs, n8n integration)
- Environment variables are passed through Docker Compose for containerized development

### Key Environment Variables
```bash
# Required for backend
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/chat_proxy
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=<secure-secret>
SESSION_SECRET_KEY=<secure-secret>
N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/chat
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Optional
N8N_API_KEY=<api-key>
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
```

## n8n Integration

The system integrates with n8n for AI processing:
- Workflow template: `docs/n8n-integration/chat-workflow.json`
- Setup guide: `docs/n8n-integration/setup-guide.md`
- JWT tokens are passed to n8n for secure communication
- Supports streaming responses via SSE

## Development Workflow

1. **Local Development**: Use `./scripts/setup.sh` for Docker-based setup, or individual `npm run dev` commands
2. **Testing**: Run security tests with `./scripts/test-security.sh`
3. **Database**: PostgreSQL runs in Docker, with automatic table creation on startup
4. **Hot Reloading**: Both frontend (Vite) and backend (uvicorn --reload) support hot reloading

## Key APIs

### Session Management
- `POST /api/v1/session/create`: Create secure chat session
- `GET /api/v1/session/validate`: Validate existing session

### Chat
- `POST /api/v1/chat/message`: Send message (returns SSE stream)
- `GET /api/v1/chat/stream/{session_id}`: SSE endpoint for real-time updates

### Monitoring  
- `GET /health`: Health check with service status
- `GET /metrics`: System metrics and connection stats

## Important Implementation Notes

- The widget embeds via iframe for security isolation
- All user inputs are sanitized for XSS/injection protection  
- Rate limiting uses sliding window algorithm with Redis
- SSE connections are managed with heartbeat and cleanup
- JWT tokens include browser fingerprinting for security
- Database uses async SQLAlchemy with connection pooling