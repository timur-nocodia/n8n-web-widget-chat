#!/bin/bash
# Simple console log removal for production

echo "Removing console logs from JavaScript files..."

# Remove from embed.js
sed -i.bak '/console\./d' apps/chat-widget/public/embed.js
echo "✓ Cleaned apps/chat-widget/public/embed.js"

# Remove from modern-widget.html (JavaScript sections)
sed -i.bak '/console\./d' apps/chat-widget/modern-widget.html  
echo "✓ Cleaned apps/chat-widget/modern-widget.html"

# Clean up backup files
rm -f apps/chat-widget/public/embed.js.bak apps/chat-widget/modern-widget.html.bak

echo "✅ Console logs removed for production"