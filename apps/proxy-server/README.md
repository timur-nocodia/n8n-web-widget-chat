# Chat Proxy Server - Backend

Secure, scalable backend for handling chat widget requests and n8n integration.

## Architecture

This backend supports multiple deployment modes:

### Stateless Mode (Recommended)
- **FastAPI** framework with async support
- **No database dependencies** - all session data in browser
- **In-memory rate limiting** (resets on restart)
- **JWT authentication** with dual-key system (SESSION_SECRET_KEY for n8n)
- **SSE streaming** for real-time responses
- **Minimal dependencies** for maximum compatibility

### SQLite Mode
- Lightweight **SQLite database** for session tracking
- **Persistent rate limiting** across restarts
- **Aiosqlite** for async database operations
- Simple backup (single .db file)

### Production Mode
- Optimized for production deployment
- Multi-worker support
- Enhanced performance tuning

## Quick Start

### Prerequisites
- Python 3.9+
- Virtual environment
- Access to n8n instance with configured webhook

### Installation

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies based on deployment mode
pip install -r requirements-stateless.txt  # Stateless mode (recommended)
# OR
pip install -r requirements-sqlite.txt     # SQLite mode

# Copy environment configuration from root
cp ../.env.example ../.env
# Edit ../.env with your configuration
```

### Configuration

All configuration is in the root `.env` file. Key variables:
- `DEPLOYMENT_MODE`: Choose stateless, sqlite, or production
- `JWT_SECRET_KEY`: Internal JWT signing (generate with `openssl rand -hex 32`)
- `SESSION_SECRET_KEY`: JWT signing for n8n validation
- `N8N_WEBHOOK_URL`: Your n8n webhook endpoint
- `ALLOWED_ORIGINS`: Domains that can embed the widget

See `.env.example` in project root for complete configuration options.

### Running

```bash
# Stateless mode (recommended)
python main_stateless.py

# SQLite mode (with database)
python main_sqlite.py

# Production mode (optimized)
python main_production.py

# Using Docker
cd .. && docker-compose up

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