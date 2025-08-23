#!/bin/bash

# Production Setup Script for n8n Web Widget Chat
# This script helps you set up the production environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   n8n Web Widget Chat - Production Setup${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Function to generate secure random keys
generate_secret_key() {
    if command -v openssl &> /dev/null; then
        openssl rand -hex 32
    else
        # Fallback to /dev/urandom
        head -c 32 /dev/urandom | base64 | tr -d "=+/" | cut -c1-32
    fi
}

# Check if we're in the right directory
if [ ! -f "package.json" ] || [ ! -d "apps" ]; then
    echo -e "${RED}Error: This script must be run from the project root directory${NC}"
    exit 1
fi

# Step 1: Choose deployment mode
echo -e "${YELLOW}Step 1: Choose Deployment Mode${NC}"
echo "1) Stateless (Recommended - No database required)"
echo "2) SQLite (Lightweight with basic analytics)"
echo "3) PostgreSQL (Full featured with complete persistence)"
echo ""
read -p "Enter your choice (1-3): " deployment_choice

case $deployment_choice in
    1)
        DEPLOYMENT_MODE="stateless"
        REQUIREMENTS_FILE="requirements-stateless.txt"
        MAIN_FILE="main_stateless.py"
        echo -e "${GREEN}✓ Selected: Stateless Mode${NC}"
        ;;
    2)
        DEPLOYMENT_MODE="sqlite"
        REQUIREMENTS_FILE="requirements-sqlite.txt"
        MAIN_FILE="main_sqlite.py"
        echo -e "${GREEN}✓ Selected: SQLite Mode${NC}"
        ;;
    3)
        DEPLOYMENT_MODE="postgresql"
        REQUIREMENTS_FILE="requirements.txt"
        MAIN_FILE="src/main.py"
        echo -e "${GREEN}✓ Selected: PostgreSQL Mode${NC}"
        echo -e "${YELLOW}Note: You'll need to set up PostgreSQL and Redis separately${NC}"
        ;;
    *)
        echo -e "${RED}Invalid choice. Exiting.${NC}"
        exit 1
        ;;
esac

# Step 2: Create .env file
echo ""
echo -e "${YELLOW}Step 2: Configure Environment${NC}"

if [ -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file already exists${NC}"
    read -p "Do you want to overwrite it? (y/n): " overwrite_env
    if [ "$overwrite_env" != "y" ]; then
        echo "Keeping existing .env file"
    else
        cp .env.production.example .env
    fi
else
    cp .env.production.example .env
fi

# Step 3: Get n8n webhook URL
echo ""
echo -e "${YELLOW}Step 3: n8n Integration${NC}"
read -p "Enter your n8n webhook URL: " n8n_webhook_url

if [ -z "$n8n_webhook_url" ]; then
    echo -e "${RED}Error: n8n webhook URL is required${NC}"
    exit 1
fi

# Step 4: Get allowed origins
echo ""
echo -e "${YELLOW}Step 4: Allowed Origins${NC}"
echo "Enter the domains where your widget will be embedded"
echo "Example: https://example.com,https://www.example.com"
read -p "Allowed origins (comma-separated): " allowed_origins

if [ -z "$allowed_origins" ]; then
    echo -e "${YELLOW}Warning: No origins specified. Using localhost only${NC}"
    allowed_origins="http://localhost:8000"
fi

# Step 5: Generate security keys
echo ""
echo -e "${YELLOW}Step 5: Generating Security Keys${NC}"

JWT_SECRET=$(generate_secret_key)
SESSION_SECRET=$(generate_secret_key)

echo -e "${GREEN}✓ Generated JWT secret key${NC}"
echo -e "${GREEN}✓ Generated session secret key${NC}"

# Step 6: Update .env file
echo ""
echo -e "${YELLOW}Step 6: Updating Configuration${NC}"

# Use sed to update the .env file
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s|DEPLOYMENT_MODE=.*|DEPLOYMENT_MODE=$DEPLOYMENT_MODE|" .env
    sed -i '' "s|N8N_WEBHOOK_URL=.*|N8N_WEBHOOK_URL=$n8n_webhook_url|" .env
    sed -i '' "s|ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=$allowed_origins|" .env
    sed -i '' "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_SECRET|" .env
    sed -i '' "s|SESSION_SECRET_KEY=.*|SESSION_SECRET_KEY=$SESSION_SECRET|" .env
    sed -i '' "s|DEBUG=.*|DEBUG=false|" .env
    sed -i '' "s|LOG_LEVEL=.*|LOG_LEVEL=WARNING|" .env
else
    # Linux
    sed -i "s|DEPLOYMENT_MODE=.*|DEPLOYMENT_MODE=$DEPLOYMENT_MODE|" .env
    sed -i "s|N8N_WEBHOOK_URL=.*|N8N_WEBHOOK_URL=$n8n_webhook_url|" .env
    sed -i "s|ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=$allowed_origins|" .env
    sed -i "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_SECRET|" .env
    sed -i "s|SESSION_SECRET_KEY=.*|SESSION_SECRET_KEY=$SESSION_SECRET|" .env
    sed -i "s|DEBUG=.*|DEBUG=false|" .env
    sed -i "s|LOG_LEVEL=.*|LOG_LEVEL=WARNING|" .env
fi

echo -e "${GREEN}✓ Configuration updated${NC}"

# Step 7: Set up Python environment
echo ""
echo -e "${YELLOW}Step 7: Setting up Python Environment${NC}"

cd apps/proxy-server

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r $REQUIREMENTS_FILE
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Step 8: Build the widget
echo ""
echo -e "${YELLOW}Step 8: Building Chat Widget${NC}"
cd ../chat-widget

if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi

echo "Building production widget..."
npm run build
echo -e "${GREEN}✓ Widget built successfully${NC}"

# Step 9: Create systemd service (optional)
cd ../..
echo ""
echo -e "${YELLOW}Step 9: System Service Setup${NC}"
read -p "Do you want to create a systemd service? (y/n): " create_service

if [ "$create_service" == "y" ]; then
    SERVICE_NAME="n8n-chat-proxy"
    SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
    
    cat > ${SERVICE_NAME}.service << EOF
[Unit]
Description=n8n Chat Proxy Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)/apps/proxy-server
Environment="PATH=$(pwd)/apps/proxy-server/venv/bin"
ExecStart=$(pwd)/apps/proxy-server/venv/bin/python $MAIN_FILE
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    echo -e "${YELLOW}Systemd service file created: ${SERVICE_NAME}.service${NC}"
    echo "To install the service, run:"
    echo "  sudo cp ${SERVICE_NAME}.service /etc/systemd/system/"
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl enable ${SERVICE_NAME}"
    echo "  sudo systemctl start ${SERVICE_NAME}"
fi

# Step 10: Summary
echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✅ Production Setup Complete!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${YELLOW}Configuration Summary:${NC}"
echo "  Deployment Mode: $DEPLOYMENT_MODE"
echo "  n8n Webhook: $n8n_webhook_url"
echo "  Allowed Origins: $allowed_origins"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "1. Start the server:"
echo "   cd apps/proxy-server"
echo "   source venv/bin/activate"
echo "   python $MAIN_FILE"
echo ""
echo "2. Test the widget:"
echo "   Visit: http://localhost:8000/widget/modern-widget.html"
echo ""
echo "3. Embed on your website:"
echo "   See README.md for embedding instructions"
echo ""
echo -e "${YELLOW}Security Notes:${NC}"
echo "• Your JWT and session keys have been generated securely"
echo "• Keep your .env file private and never commit it to git"
echo "• Use HTTPS in production for all origins"
echo "• Review rate limiting settings in .env"
echo ""
echo -e "${GREEN}Happy chatting! 🚀${NC}"