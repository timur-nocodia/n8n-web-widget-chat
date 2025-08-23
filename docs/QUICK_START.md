# 🚀 Quick Start Guide

Get your chat widget running in 5 minutes!

## Prerequisites
- Python 3.8+
- n8n webhook URL ready

## Fastest Setup (Stateless Mode)

### 1️⃣ Clone & Navigate
```bash
git clone https://github.com/timur-nocodia/n8n-web-widget-chat.git
cd n8n-web-widget-chat
```

### 2️⃣ Run Automatic Setup
```bash
./scripts/setup-production.sh
```

When prompted:
- Choose option 1 (Stateless mode)
- Enter your n8n webhook URL
- Enter domains where widget will be embedded (or press Enter for localhost)

### 3️⃣ Start the Server
```bash
cd apps/proxy-server
source venv/bin/activate
python main_stateless.py
```

### 4️⃣ Test the Widget
Open your browser and visit:
```
http://localhost:8000/widget/modern-widget.html
```

You should see the chat widget! Try sending a message.

## Manual Setup (If script doesn't work)

### 1️⃣ Create Environment File
```bash
cp .env.development.example .env
```

### 2️⃣ Edit Configuration
Open `.env` and update:
```bash
N8N_WEBHOOK_URL=https://your-n8n.com/webhook/xxx/chat
ALLOWED_ORIGINS=http://localhost:8000
```

### 3️⃣ Install & Run Backend
```bash
cd apps/proxy-server
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-stateless.txt
python main_stateless.py
```

### 4️⃣ Test Widget
Visit: http://localhost:8000/widget/modern-widget.html

## Embedding on Your Website

### Option 1: Simple iframe
```html
<iframe 
  src="http://localhost:8000/widget/modern-widget.html"
  style="position: fixed; bottom: 20px; right: 20px; 
         width: 400px; height: 600px; border: none; z-index: 10000;">
</iframe>
```

### Option 2: Script Embed (coming soon)
```html
<script src="http://localhost:8000/widget/embed.js"></script>
```

## Customization

### Change Widget Appearance
Edit `apps/chat-widget/widget-config.json`:
```json
{
  "appearance": {
    "theme": {
      "primaryColor": "#007bff"
    }
  },
  "texts": {
    "messages": {
      "welcomeMessage": "Hello! How can I help?"
    }
  }
}
```

### Change Server Port
Edit `.env`:
```bash
API_PORT=3000  # Change from 8000 to 3000
```

## Troubleshooting

### "Cannot connect to server"
- Check your n8n webhook URL is correct
- Ensure n8n is running and accessible
- Check ALLOWED_ORIGINS includes your domain

### "Rate limit exceeded"
- Increase limits in `.env`:
  ```bash
  RATE_LIMIT_PER_MINUTE=100
  ```

### Widget doesn't appear
- Check browser console for errors
- Verify server is running: `curl http://localhost:8000/health`
- Clear browser cache

## Production Deployment

### For Production Use:
1. Change to production config:
   ```bash
   cp .env.production.example .env
   ```

2. Generate secure keys:
   ```bash
   openssl rand -hex 32  # For JWT_SECRET_KEY
   openssl rand -hex 32  # For SESSION_SECRET_KEY
   ```

3. Update ALLOWED_ORIGINS with your actual domain

4. Use a process manager like systemd or supervisor

5. Put behind a reverse proxy (nginx/Apache)

## Next Steps

- 📖 Read the [full documentation](README.md)
- 🎨 [Customize the widget](apps/chat-widget/WIDGET_CONFIGURATION.md)
- 🚀 [Deploy to production](apps/proxy-server/LIGHTWEIGHT_DEPLOYMENT.md)
- 🔒 Review [security settings](.env.production.example)

## Need Help?

- Check [README.md](README.md) for detailed docs
- Open an [issue on GitHub](https://github.com/timur-nocodia/n8n-web-widget-chat/issues)
- Review [example configurations](.env.development.example)

---

**Remember**: The stateless mode needs NO database - it just works! 🎉