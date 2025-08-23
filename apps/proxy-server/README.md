# Chat Proxy Server - Production Backend

Secure, production-ready backend for handling chat widget requests and n8n integration.

## Architecture

This is the production backend with:
- **FastAPI** framework with async support
- **PostgreSQL** for session storage
- **Redis** for rate limiting and caching
- **JWT authentication** with dual-key system (SESSION_SECRET_KEY for n8n)
- **SSE streaming** for real-time responses
- **Security middleware** (rate limiting, CORS, threat detection)
- **Connection pooling** and circuit breakers

## Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL running on localhost:5432
- Redis running on localhost:6379
- Virtual environment

### Installation

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head
```

### Configuration

All configuration is in `.env`:
- `JWT_SECRET_KEY`: Internal JWT signing
- `SESSION_SECRET_KEY`: JWT signing for n8n validation
- `N8N_WEBHOOK_URL`: Your n8n webhook endpoint
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string

### Running

```bash
# Production mode
python main.py

# Development mode with hot reload
DEBUG=true python main.py
```

The server runs on `http://localhost:8000` by default.

## API Endpoints

### Session Management
- `POST /api/v1/session/create` - Create new chat session
- `GET /api/v1/session/validate` - Validate existing session

### Chat
- `POST /api/v1/chat/message` - Send message (SSE streaming response)
- `POST /api/v1/chat/stream` - Alternative streaming endpoint
- `GET /api/v1/chat/history/{session_id}` - Get chat history

### Health & Monitoring  
- `GET /health` - Service health with dependency checks
- `GET /metrics` - Connection stats and metrics

## Security Features

- JWT tokens with 30-second expiration for n8n
- Multi-tier rate limiting (IP, session, domain)
- Browser fingerprinting
- Bot and spam detection
- XSS/injection protection
- Security headers middleware

## Project Structure

```
src/
├── api/v1/           # API endpoints
├── core/             # Core functionality (config, security, validation)
├── db/               # Database setup
├── middleware/       # Security and error handling middleware
├── models/           # SQLAlchemy models
├── services/         # Business logic (JWT, n8n client, SSE manager)
└── main.py           # FastAPI application
```

## Production Deployment

For production:
1. Use environment variables instead of .env file
2. Set `DEBUG=false`
3. Use a production WSGI server (uvicorn with workers)
4. Enable HTTPS/TLS
5. Configure proper CORS origins
6. Use strong JWT secrets