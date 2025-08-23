# n8n Chat Widget Proxy

A production-ready chat proxy system that connects web chat widgets to n8n workflows for AI-powered customer support.

## Features

- 🔒 **Secure JWT-based authentication**
- 🚀 **Real-time streaming responses** via Server-Sent Events (SSE)
- 🛡️ **Built-in rate limiting and security**
- 📦 **Single Docker container deployment**
- 🎨 **Modern, responsive chat widget**
- 🔌 **Easy n8n integration**

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/n8n_embed_chat.git
cd n8n_embed_chat
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Run with Docker Compose
```bash
docker-compose up -d
```

The service will be available at `http://localhost:8000`

## Configuration

### Required Environment Variables

- `JWT_SECRET_KEY`: Secret key for JWT tokens (generate a strong random key)
- `SESSION_SECRET_KEY`: Secret key for n8n session validation
- `N8N_WEBHOOK_URL`: Your n8n webhook URL for chat processing
- `ALLOWED_ORIGINS`: Comma-separated list of allowed domains

### Optional Configuration

- `DATABASE_URL`: PostgreSQL connection string (for session persistence)
- `REDIS_URL`: Redis connection string (for rate limiting)
- `LOG_LEVEL`: Logging level (WARNING recommended for production)

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