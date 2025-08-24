# 🤖 n8n Chat Widget - Production Ready

A lightweight, production-ready chat widget system that seamlessly integrates with n8n workflows for AI-powered customer support. Features real-time streaming, unread message notifications, and enterprise-grade security.

## ✨ Key Features

- **🔄 Real-time Streaming**: Server-Sent Events for instant AI responses
- **📱 Mobile-First Design**: Responsive widget that works on all devices  
- **🔔 Smart Notifications**: Unread message system with visual indicators
- **🔒 Enterprise Security**: JWT authentication, rate limiting, CORS protection
- **🎨 Fully Customizable**: JSON-based configuration for complete theming
- **💾 Zero Database**: Browser-first storage with optional SQLite analytics
- **🚀 Production Ready**: Docker deployment with Portainer/stack support

## 🚀 Quick Docker Deployment

### Option 1: Docker Compose (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/timur-nocodia/n8n-web-widget-chat.git
   cd n8n-web-widget-chat
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings (see Configuration section below)
   ```

3. **Deploy with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

4. **Access your widget**:
   - Widget: `http://localhost:8000/widget/modern-widget.html`
   - Health: `http://localhost:8000/health`

### Option 2: Docker Stack (Portainer/Swarm)

```yaml
version: '3.8'
services:
  chat-proxy:
    image: n8n-chat-proxy:latest
    ports:
      - "8000:8000"
    environment:
      - N8N_WEBHOOK_URL=https://your-n8n.com/webhook/your-id/chat
      - JWT_SECRET_KEY=your-jwt-secret-key-here
      - SESSION_SECRET_KEY=your-session-secret-key-here
      - ALLOWED_ORIGINS=https://yoursite.com,https://www.yoursite.com
      - LOG_LEVEL=WARNING
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## ⚙️ Configuration

### Required Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# n8n Integration (REQUIRED)
N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/your-id/chat

# Security Keys (REQUIRED) - Generate with: openssl rand -hex 32
JWT_SECRET_KEY=your-super-secret-jwt-key-min-32-characters
SESSION_SECRET_KEY=your-super-secret-session-key-min-32-characters

# CORS Security (REQUIRED)  
ALLOWED_ORIGINS=https://yoursite.com,https://www.yoursite.com,http://localhost:3000

# Server Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=WARNING

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
```

### Production Security Checklist

- ✅ Use strong, unique 32+ character secrets
- ✅ Set `ALLOWED_ORIGINS` to your actual domains only
- ✅ Use `LOG_LEVEL=WARNING` in production  
- ✅ Enable HTTPS in production (reverse proxy)
- ✅ Set appropriate rate limits for your use case

## 🎨 Widget Customization

The widget appearance is controlled by `apps/chat-widget/widget-config.json`:

### Basic Theming
```json
{
  "api": {
    "baseUrl": "https://your-chat-api.com"
  },
  "appearance": {
    "theme": "modern",
    "primaryColor": "#667eea",
    "secondaryColor": "#764ba2",
    "borderRadius": "16px"
  },
  "texts": {
    "header": {
      "title": "AI Assistant", 
      "subtitle": "Online • Powered by n8n"
    },
    "messages": {
      "welcomeMessage": "👋 Hello! How can I help you today?",
      "placeholderText": "Type your message...",
      "sendButtonText": "Send"
    },
    "button": {
      "openIcon": "💬",
      "closeIcon": "✕"
    }
  },
  "behavior": {
    "autoOpen": false,
    "autoOpenDelay": 0,
    "enableNotifications": true,
    "showTypingIndicator": true
  }
}
```

### Advanced Customization

**Colors & Styling**:
```json
{
  "appearance": {
    "primaryGradient": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    "backgroundDark": "rgba(30, 30, 46, 0.95)",
    "textLight": "#ffffff",
    "borderRadius": "12px",
    "boxShadow": "0 20px 40px rgba(0, 0, 0, 0.15)"
  }
}
```

**Multilingual Support**:
```json
{
  "texts": {
    "messages": {
      "welcomeMessage": "¡Hola! ¿Cómo puedo ayudarte hoy?",
      "placeholderText": "Escribe tu mensaje...",
      "errorMessage": "Lo siento, no pude conectar al servidor."
    }
  }
}
```

**Notifications & Behavior**:
```json
{
  "behavior": {
    "enableNotifications": true,
    "autoOpen": true,
    "autoOpenDelay": 3000,
    "showSuggestions": true,
    "suggestions": [
      "How can I help you?",
      "Tell me about your products",
      "I need technical support"
    ]
  }
}
```

## 🌐 Website Integration

### JavaScript Embed (Recommended)
```html
<script>
(function() {
  var iframe = document.createElement('iframe');
  iframe.src = 'https://your-chat-domain.com/widget/modern-widget.html';
  iframe.style.cssText = 'position: fixed; bottom: 20px; right: 20px; width: 400px; height: 600px; border: none; z-index: 9999; background: transparent;';
  document.body.appendChild(iframe);
})();
</script>
```

### Direct iFrame Embed
```html
<iframe src="https://your-chat-domain.com/widget/modern-widget.html" 
        width="400" height="600" 
        style="border: none; background: transparent;">
</iframe>
```

### WordPress/CMS Integration
Add the JavaScript embed code to your theme's footer or use a custom HTML block.

## 🔗 n8n Workflow Setup

### 1. Create n8n Workflow
1. Add **Webhook** node (POST method)
2. Set **Response Mode**: "Streaming"  
3. Configure your AI processing (OpenAI, Claude, local LLM, etc.)
4. Return streaming response in this format:

```json
{
  "type": "item",
  "content": "Your AI response text here"
}
```

### 2. JWT Token Handling
Your n8n workflow receives JWT tokens in the request body:
```javascript
// Access token in your n8n nodes
const jwtToken = $json.jwt_token;
const sessionData = $json.session;
const userMessage = $json.message;
```

### 3. Streaming Response Format
For streaming responses, send JSON objects:
```json
{"type": "begin"}
{"type": "item", "content": "Hello"}
{"type": "item", "content": " there!"}
{"type": "end"}
```

## 🏗️ Production Deployment

### Docker Compose Production Stack

```yaml
version: '3.8'

services:
  chat-proxy:
    build: .
    container_name: n8n-chat-proxy
    ports:
      - "8000:8000"
    env_file: .env
    environment:
      - API_HOST=0.0.0.0
      - API_PORT=8000
      - LOG_LEVEL=WARNING
    volumes:
      - ./data:/app/data  # For SQLite mode if needed
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - chat-network

networks:
  chat-network:
    driver: bridge
```

### Reverse Proxy (Nginx/Traefik)

**Nginx Configuration**:
```nginx
server {
    listen 443 ssl;
    server_name chat.yoursite.com;

    # SSL configuration
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        
        # Headers
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE/Streaming support
        proxy_set_header Cache-Control no-cache;
        proxy_set_header X-Accel-Buffering no;
        proxy_buffering off;
        proxy_read_timeout 86400;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### Environment-Specific Deployments

**Development**:
```bash
LOG_LEVEL=DEBUG
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

**Staging**: 
```bash
LOG_LEVEL=INFO  
ALLOWED_ORIGINS=https://staging.yoursite.com
```

**Production**:
```bash
LOG_LEVEL=WARNING
ALLOWED_ORIGINS=https://yoursite.com,https://www.yoursite.com
```

## 📊 Monitoring & Health Checks

### Health Endpoint
```bash
curl https://your-chat-domain.com/health
```

**Response**:
```json
{
  "status": "healthy",
  "version": "production-1.0",
  "services": {
    "n8n_webhook": "healthy",
    "jwt_service": "active",
    "sessions_active": 15
  },
  "config": {
    "n8n_url": "https://n8n.example.com/webhook/chat",
    "jwt_expiration": "300s",
    "allowed_origins": 2
  }
}
```

### Metrics Endpoint
```bash
curl https://your-chat-domain.com/metrics
```

## 🛠️ Deployment Modes

The system supports three deployment modes:

### 1. **Stateless Mode** (Default)
- **Use case**: High traffic, horizontal scaling
- **Storage**: Browser-only (IndexedDB)
- **Database**: None required
- **Scaling**: Infinite horizontal scaling

### 2. **SQLite Mode**  
- **Use case**: Basic analytics needed
- **Storage**: Browser + SQLite metadata
- **Database**: Single SQLite file
- **Scaling**: Vertical scaling only

### 3. **Production Mode**
- **Use case**: Enterprise deployment
- **Storage**: Configurable
- **Database**: Optional
- **Scaling**: Multi-worker support

## 🔧 Troubleshooting

### Common Issues

**Widget not loading**:
- Check CORS settings in `ALLOWED_ORIGINS`
- Verify the widget URL is accessible
- Check browser console for errors

**n8n not receiving messages**:
- Verify `N8N_WEBHOOK_URL` is correct
- Check n8n workflow is active
- Verify JWT tokens are being sent

**Session errors**:
- Check JWT secret keys are set
- Verify browser cookies are enabled
- Check session timeout settings

### Debug Mode
Add `?debug=true` to widget URL to enable debug logging:
```
https://your-domain.com/widget/modern-widget.html?debug=true
```

## 📄 API Reference

### Session Management
- `POST /api/v1/session/create` - Create new chat session
- `GET /api/v1/session/validate` - Validate existing session

### Chat Operations  
- `POST /api/v1/chat/message` - Send message (JSON response)
- `POST /api/v1/chat/stream` - Send message (SSE stream)
- `GET /api/v1/chat/stream` - EventSource compatible endpoint

### System
- `GET /health` - Health check with service status
- `GET /metrics` - System metrics and statistics
- `GET /widget/*` - Serve widget static files

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

MIT License - See LICENSE file for details

## 🆘 Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/timur-nocodia/n8n-web-widget-chat/issues)
- **Documentation**: Check `CLAUDE.md` for technical details
- **n8n Community**: [n8n Community Forum](https://community.n8n.io)

---

**Ready to deploy?** 🚀 Follow the Quick Docker Deployment section above and you'll have a production-ready chat widget running in minutes!