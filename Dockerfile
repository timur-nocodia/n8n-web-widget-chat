FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY apps/proxy-server/requirements*.txt ./

# Install Python dependencies based on deployment mode
# Default to stateless mode for minimal dependencies
ARG DEPLOYMENT_MODE=stateless
RUN if [ "$DEPLOYMENT_MODE" = "sqlite" ]; then \
        pip install --no-cache-dir -r requirements-sqlite.txt; \
    else \
        pip install --no-cache-dir -r requirements-stateless.txt; \
    fi

# Copy application code
COPY apps/proxy-server/*.py ./

# Copy widget files
COPY apps/chat-widget /app/chat-widget

# Create data directory for SQLite mode
RUN mkdir -p /app/data

# Set environment variable defaults
ENV DEPLOYMENT_MODE=${DEPLOYMENT_MODE:-stateless} \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    LOG_LEVEL=WARNING

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application based on deployment mode
CMD if [ "$DEPLOYMENT_MODE" = "production" ]; then \
        python main_production.py; \
    elif [ "$DEPLOYMENT_MODE" = "sqlite" ]; then \
        python main_sqlite.py; \
    else \
        python main_stateless.py; \
    fi