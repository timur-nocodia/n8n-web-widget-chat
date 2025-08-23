# Complete n8n Chat Widget Setup Guide

This is the definitive guide for deploying and configuring the n8n chat widget system. Everything you need to know is in this document.

## 🚀 Quick Start (5 Minutes)

### 1. Choose Your Deployment Mode

**Stateless Mode (Recommended)** - Zero dependencies, instant deployment:
```bash
cd apps/proxy-server
pip install -r requirements-stateless.txt
python main_stateless.py
```

**SQLite Mode** - Lightweight with basic analytics:
```bash
cd apps/proxy-server  
pip install -r requirements-sqlite.txt
python main_sqlite.py
```

### 2. Configure Environment

Create `/apps/proxy-server/.env`:
```bash
# Required Configuration
N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/chat
JWT_SECRET_KEY=generate-secure-random-string-here
SESSION_SECRET_KEY=generate-another-secure-random-string
ALLOWED_ORIGINS=https://yourwebsite.com

# Optional Configuration  
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=WARNING
RATE_LIMIT_PER_MINUTE=60
SQLITE_DB_PATH=chat_sessions.db  # SQLite mode only
```

### 3. Test the Widget

Visit: `http://localhost:8000/widget/modern-widget.html`

---

## 📋 Complete Setup Process

### Step 1: n8n Workflow Setup

1. **Import the Workflow**
   - Use `/docs/n8n-integration/chat-workflow.json`
   - Import via n8n interface: Workflows → Import from file

2. **Configure OpenAI Credential**
   - Go to Settings → Credentials
   - Add OpenAI credential with your API key
   - Name it `OpenAI API`

3. **Get Webhook URL**
   - Click the Chat Webhook node in your workflow
   - Copy the webhook URL (e.g., `https://n8n.example.com/webhook/chat`)

### Step 2: Server Configuration

1. **Environment Setup**
   ```bash
   # Copy example configuration
   cp apps/proxy-server/.env.example apps/proxy-server/.env
   
   # Edit with your values
   nano apps/proxy-server/.env
   ```

2. **Generate Secure Keys**
   ```bash
   # Generate JWT secret
   openssl rand -base64 32
   
   # Generate session secret  
   openssl rand -base64 32
   ```

3. **Start the Server**
   ```bash
   cd apps/proxy-server
   
   # For stateless mode (recommended)
   python main_stateless.py
   
   # For SQLite mode (with analytics)
   python main_sqlite.py
   ```

### Step 3: Widget Integration

**Method 1: Direct Embed (Simplest)**
```html
<iframe src="https://your-server.com/widget/modern-widget.html" 
        width="400" height="600" 
        style="border: none; position: fixed; bottom: 20px; right: 20px; z-index: 1000;">
</iframe>
```

**Method 2: JavaScript Embed (Dynamic)**
```html
<script>
  (function() {
    var script = document.createElement('script');
    script.src = 'https://your-server.com/widget/embed.js';
    script.async = true;
    document.head.appendChild(script);
  })();
</script>
```

---

## 🔧 Detailed Configuration

### Deployment Modes Comparison

| Feature | Stateless Mode | SQLite Mode |
|---------|----------------|-------------|
| **Setup Time** | Instant | < 1 minute |
| **Dependencies** | None | SQLite (built-in) |
| **Chat Storage** | Browser only | Browser + server metadata |
| **Analytics** | None | Basic session tracking |
| **Scalability** | Unlimited | Single instance |
| **Maintenance** | Zero | Minimal |
| **Backup** | User exports | Copy .db file |
| **Privacy** | Maximum | High |

### Environment Variables Reference

**Required for both modes:**
```bash
N8N_WEBHOOK_URL=https://n8n.example.com/webhook/chat
JWT_SECRET_KEY=your-32-char-secret
SESSION_SECRET_KEY=your-n8n-validation-secret  
ALLOWED_ORIGINS=https://site1.com,https://site2.com
```

**Optional configuration:**
```bash
API_HOST=0.0.0.0                 # Server bind address
API_PORT=8000                    # Server port
LOG_LEVEL=WARNING                # DEBUG, INFO, WARNING, ERROR
RATE_LIMIT_PER_MINUTE=60         # Rate limit per IP
```

**SQLite mode only:**
```bash
SQLITE_DB_PATH=chat_sessions.db  # Database file location
```

### JWT Token System

The system uses dual JWT tokens:

1. **Internal Tokens (JWT_SECRET_KEY)** 
   - Used for browser ↔ proxy authentication
   - Contains session ID and browser fingerprint
   - 24-hour expiration

2. **n8n Validation Tokens (SESSION_SECRET_KEY)**
   - Used for proxy → n8n authentication
   - Contains session metadata for n8n
   - 30-second expiration (short-lived)

---

## 🔒 Security Configuration

### CORS Setup
```bash
# Development
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Production  
ALLOWED_ORIGINS=https://yoursite.com,https://www.yoursite.com
```

### Rate Limiting
- **Stateless Mode**: In-memory limits (resets on restart)
- **SQLite Mode**: Persistent limits (survives restart)
- Default: 60 requests per minute per IP

### Input Validation
- Automatic XSS protection
- Message length limits (10,000 characters)
- Domain validation for origins
- JWT token validation

---

## 🚀 Production Deployment

### Docker Deployment

**Stateless Mode:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements-stateless.txt main_stateless.py ./
RUN pip install -r requirements-stateless.txt
EXPOSE 8000
CMD ["python", "main_stateless.py"]
```

**SQLite Mode:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements-sqlite.txt main_sqlite.py ./
RUN pip install -r requirements-sqlite.txt
VOLUME /app/data
EXPOSE 8000
CMD ["python", "main_sqlite.py"]
```

### Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name chat.yoursite.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # Critical for SSE streaming
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

### Horizontal Scaling

**Stateless Mode** (scales infinitely):
```bash
# Run multiple instances
python main_stateless.py --port 8001 &
python main_stateless.py --port 8002 &
python main_stateless.py --port 8003 &

# Load balance with nginx upstream
```

**SQLite Mode** (single instance recommended):
- SQLite doesn't support concurrent writes across instances
- Use for single-server deployments only

---

## 🧪 Testing and Debugging

### Basic Functionality Test
```bash
# Health check
curl http://localhost:8000/health

# Create session  
curl -X POST http://localhost:8000/api/v1/session/create \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3000" \
  -d '{"origin_domain":"localhost","page_url":"http://localhost:3000/test"}' \
  -c cookies.txt

# Send message
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3000" \
  -d '{"message":"Hello world"}' \
  -b cookies.txt
```

### Security Testing
Run the included security test suite:
```bash
./scripts/test-security.sh
```

### Debug Mode
```bash
# Enable detailed logging
export LOG_LEVEL=DEBUG
python main_stateless.py
```

---

## 🔧 n8n Workflow Customization

### Basic AI Configuration

In the n8n workflow, modify the **Prepare AI Context** node:

```javascript
// Set custom system message
const systemMessage = {
  role: 'system',
  content: `You are a helpful assistant for ${input.origin_domain}.
  
  Guidelines:
  - Be professional and helpful
  - Keep responses concise but informative  
  - Ask clarifying questions when needed
  - Current context: ${JSON.stringify(input.context)}`
};

return [{
  json: {
    messages: [systemMessage, ...input.messages],
    session_id: input.session_id
  }
}];
```

### Response Formatting

Modify the **Process AI Response** node:

```javascript
if (response.delta && response.delta.content) {
  let content = response.delta.content;
  
  // Add markdown formatting
  content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  content = content.replace(/\*(.*?)\*/g, '<em>$1</em>');
  
  return [{
    json: {
      event: 'message', 
      data: JSON.stringify({
        content: content,
        session_id: sessionId,
        timestamp: new Date().toISOString()
      })
    }
  }];
}
```

### Error Handling

Add an error handler node:

```javascript
const error = $input.first().json;

return [{
  json: {
    event: 'error',
    data: JSON.stringify({
      error: 'AI service temporarily unavailable',
      code: 'AI_ERROR',
      retry_after: 30
    })
  }
}];
```

---

## 📊 Monitoring and Analytics

### Health Endpoints

- **Health Check**: `GET /health`
- **Metrics**: `GET /metrics`  
- **Widget File**: `GET /widget/modern-widget.html`

### SQLite Analytics

In SQLite mode, you can query session data:

```sql
-- Session analytics
SELECT 
  DATE(created_at) as date,
  COUNT(*) as sessions,
  AVG(message_count) as avg_messages
FROM chat_sessions 
WHERE created_at > datetime('now', '-7 days')
GROUP BY DATE(created_at);

-- Popular domains
SELECT 
  origin_domain,
  COUNT(*) as sessions
FROM chat_sessions 
GROUP BY origin_domain
ORDER BY sessions DESC;
```

### Browser Storage

Users can export their chat history:

```javascript
// In browser console
const data = await chatPersistence.exportChatHistory('json');
console.log(data); // Download or save
```

---

## 🛠 Maintenance

### Log Management
```bash
# Remove console logs for production
./scripts/remove-console-logs.sh
```

### Database Maintenance (SQLite Mode)
```sql
-- Clean old sessions (auto-runs, but manual option)
DELETE FROM chat_sessions 
WHERE created_at < datetime('now', '-30 days');

-- Vacuum database
VACUUM;
```

### Backup Procedures

**Stateless Mode:**
- No server-side data to backup
- Users can export chat history from browser

**SQLite Mode:**
```bash
# Backup database
cp chat_sessions.db backup-$(date +%Y%m%d).db

# Restore database
cp backup-20240115.db chat_sessions.db
```

---

## 🐛 Troubleshooting

### Common Issues

1. **Widget Not Loading**
   - Check CORS origins in `.env`
   - Verify server is running on correct port
   - Check browser console for errors

2. **n8n Not Responding**
   - Verify webhook URL is correct
   - Check n8n workflow is activated
   - Validate JWT secrets match

3. **Rate Limiting Issues**
   - Increase `RATE_LIMIT_PER_MINUTE`
   - Check if testing from same IP
   - Wait for rate limit reset

4. **Database Errors (SQLite)**
   - Check file permissions on `chat_sessions.db`
   - Verify disk space available
   - Try deleting corrupted database file

### Debug Steps

1. **Check server logs** for error messages
2. **Test health endpoint**: `curl http://localhost:8000/health`
3. **Verify environment variables** are set correctly
4. **Check n8n workflow** execution logs
5. **Test without rate limiting** by increasing limits

---

## 🎯 Performance Optimization

### Stateless Mode Optimization
- Runs immediately with zero overhead
- No database queries to optimize
- Scales infinitely behind load balancer

### SQLite Mode Optimization
```sql
-- Add indexes for better performance
CREATE INDEX idx_sessions_created ON chat_sessions(created_at);
CREATE INDEX idx_sessions_domain ON chat_sessions(origin_domain);
```

### Frontend Optimization
- Widget is served as static files (fast)
- Browser storage reduces server requests
- Streaming responses for real-time feel

---

## 📚 FAQ

**Q: Which mode should I use?**
A: Start with stateless mode. It's faster, requires zero maintenance, and scales infinitely. Use SQLite mode only if you need server-side analytics.

**Q: How do I scale this system?**
A: Stateless mode scales horizontally behind any load balancer. SQLite mode runs single instance but handles thousands of concurrent users.

**Q: Is user data secure?**
A: Yes. In stateless mode, all data stays in user's browser. In SQLite mode, only session metadata is stored server-side, not actual messages.

**Q: Can I customize the widget appearance?**
A: The widget is a standalone HTML file. Edit `apps/chat-widget/modern-widget.html` directly to customize styling.

**Q: How do I backup user conversations?**
A: Users can export their chat history from the browser. No server-side backup needed for conversations.

**Q: What if n8n is down?**
A: The widget will show an error message. Chat history remains in browser and works again when n8n is restored.

---

## 🔗 Quick Reference

- **Widget URL**: `http://your-server:8000/widget/modern-widget.html`
- **Health Check**: `http://your-server:8000/health`
- **API Base**: `http://your-server:8000/api/v1/`
- **Security Test**: `./scripts/test-security.sh`
- **Log Cleanup**: `./scripts/remove-console-logs.sh`

This guide contains everything needed to deploy and maintain the n8n chat widget system. For additional support, check the server logs and n8n workflow execution logs.