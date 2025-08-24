# n8n Web Widget Chat System

A production-ready, lightweight chat widget system that connects to n8n workflows for AI-powered customer support. Features browser-first storage, real-time streaming, and multiple deployment options.

## 🚀 Quick Start (5 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/timur-nocodia/n8n-web-widget-chat.git
cd n8n-web-widget-chat

# 2. Copy environment configuration
cp .env.development.example .env

# 3. Edit .env with your n8n webhook URL
# Update N8N_WEBHOOK_URL with your actual webhook

# 4. Start the backend (stateless mode - no database required!)
cd apps/proxy-server
pip install -r requirements-stateless.txt
python main_stateless.py

# 5. Open the widget demo
# Visit: http://localhost:8000/widget/modern-widget.html
```

That's it! Your chat widget is running. 🎉

## 📦 What's Included

### **Chat Widget** (Frontend)
- 🎨 **Fully customizable** via JSON configuration
- 💾 **Browser-first storage** using IndexedDB
- 🔄 **Real-time streaming** with Server-Sent Events
- 📱 **Responsive design** for mobile and desktop
- 🔒 **Production-ready** with console management
- 🌐 **Multi-language support** ready

### **Proxy Server** (Backend)
- 🏃 **Three deployment modes**: Stateless, SQLite, or Production
- 🔐 **JWT-based security** with session management
- ⚡ **Rate limiting** and DDoS protection
- 🔄 **n8n integration** with streaming support
- 📊 **Built-in metrics** and health checks
- 🚀 **Production optimized** with minimal dependencies

## 🎯 Deployment Options

### Option 1: **Stateless Mode** (Recommended) ⭐
- **Zero database** - runs immediately
- **Infinite scale** - completely stateless
- **Browser storage** - chat history in IndexedDB

### Option 2: **SQLite Mode** (Lightweight + Analytics)
- **Single file database** - easy backup
- **Basic analytics** - track usage
- **Still browser-first** - for chat history

### Option 3: **Production Mode** (Optimized)
- **Multi-worker support** - handles high traffic
- **Production tuned** - optimized performance
- **Enterprise ready** - for production deployments

## Configuration

### Required Environment Variables

- `N8N_WEBHOOK_URL`: Your n8n webhook URL for chat processing
- `JWT_SECRET_KEY`: Secret key for JWT tokens (generate with: `openssl rand -hex 32`)
- `SESSION_SECRET_KEY`: Secret key for n8n session validation
- `ALLOWED_ORIGINS`: Comma-separated list of allowed domains

### Quick Configuration

```bash
# Development
cp .env.development.example .env

# Production
cp .env.production.example .env
# Edit with your values
```

## Widget Integration

### Embed the chat widget on your website:

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

Or directly link to the widget:
```html
<iframe src="https://yourchatserver.com/widget/modern-widget.html" 
        width="400" 
        height="600"
        style="border: none;">
</iframe>
```

## n8n Workflow Setup

1. Create a new workflow in n8n
2. Add a Webhook node with method POST
3. Configure your AI processing (OpenAI, local LLM, etc.)
4. Enable streaming response in the webhook settings
5. Copy the webhook URL to your `.env` file

## API Endpoints

- `GET /` - Health check
- `GET /health` - Detailed health status
- `POST /api/v1/session/create` - Create chat session
- `GET /api/v1/session/validate` - Validate session
- `POST /api/v1/chat/message` - Send message (non-streaming)
- `GET /api/v1/chat/stream` - SSE streaming endpoint
- `GET /widget/*` - Serve widget files

## Security Features

- JWT token validation with expiration
- Session-based authentication
- Rate limiting per IP and session
- CORS protection
- Input sanitization
- XSS protection

## Development

### Local Development
```bash
cd apps/proxy-server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main_production.py
```

### Testing
Visit `http://localhost:8000/widget/modern-widget.html` to test the widget.

## Production Deployment

### Using Docker
```bash
docker build -t chat-proxy .
docker run -d -p 8000:8000 --env-file .env chat-proxy
```

### Using Docker Compose (Recommended)
```bash
docker-compose up -d
```

### Reverse Proxy Configuration (Nginx)
```nginx
location / {
    proxy_pass http://localhost:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # SSE specific
    proxy_set_header Cache-Control no-cache;
    proxy_set_header X-Accel-Buffering no;
    proxy_read_timeout 86400;
}
```

## License

MIT

## Support

For issues and questions, please open an issue on GitHub.