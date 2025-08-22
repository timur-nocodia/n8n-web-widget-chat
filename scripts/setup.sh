#!/bin/bash

set -e

echo "🚀 Setting up Chat Proxy System..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env files if they don't exist
echo "📝 Creating environment files..."

if [ ! -f apps/proxy-server/.env ]; then
    cp apps/proxy-server/.env.example apps/proxy-server/.env
    echo "✅ Created apps/proxy-server/.env from example"
fi

# Generate secure keys
if [ -f apps/proxy-server/.env ]; then
    # Generate JWT secret if not set
    if ! grep -q "JWT_SECRET_KEY=" apps/proxy-server/.env || grep -q "your-secret-key-change-this-in-production" apps/proxy-server/.env; then
        JWT_SECRET=$(openssl rand -base64 32)
        sed -i.bak "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$JWT_SECRET/" apps/proxy-server/.env
        echo "✅ Generated secure JWT secret"
    fi
    
    # Generate session secret if not set
    if ! grep -q "SESSION_SECRET_KEY=" apps/proxy-server/.env || grep -q "your-session-secret-change-this" apps/proxy-server/.env; then
        SESSION_SECRET=$(openssl rand -base64 32)
        sed -i.bak "s/SESSION_SECRET_KEY=.*/SESSION_SECRET_KEY=$SESSION_SECRET/" apps/proxy-server/.env
        echo "✅ Generated secure session secret"
    fi
    
    # Clean up backup files
    rm -f apps/proxy-server/.env.bak
fi

# Build and start services
echo "🐳 Building and starting Docker services..."
cd infrastructure/docker

# Stop any existing services
docker-compose down 2>/dev/null || true

# Build and start services
docker-compose up --build -d

echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service health
echo "🔍 Checking service status..."

# Check PostgreSQL
if docker-compose exec -T postgres pg_isready -U postgres -d chat_proxy >/dev/null 2>&1; then
    echo "✅ PostgreSQL is running"
else
    echo "❌ PostgreSQL is not ready"
fi

# Check Redis
if docker-compose exec -T redis redis-cli ping | grep -q PONG; then
    echo "✅ Redis is running"
else
    echo "❌ Redis is not ready"
fi

# Check Proxy Server
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ Proxy Server is running"
else
    echo "❌ Proxy Server is not ready"
fi

# Check Chat Widget
if curl -s http://localhost:5173 >/dev/null 2>&1; then
    echo "✅ Chat Widget is running"
else
    echo "❌ Chat Widget is not ready"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Service URLs:"
echo "   • Proxy Server: http://localhost:8000"
echo "   • Chat Widget: http://localhost:5173"
echo "   • API Health: http://localhost:8000/health"
echo "   • PostgreSQL: localhost:5432 (chat_proxy/postgres/postgres)"
echo "   • Redis: localhost:6379"
echo ""
echo "📖 Next steps:"
echo "   1. Configure your n8n webhook URL in apps/proxy-server/.env"
echo "   2. Test the integration with: curl http://localhost:8000/health"
echo "   3. Open http://localhost:5173 to see the chat widget"
echo ""
echo "🛠 Development commands:"
echo "   • View logs: docker-compose logs -f [service]"
echo "   • Stop services: docker-compose down"
echo "   • Restart: docker-compose restart [service]"
echo ""