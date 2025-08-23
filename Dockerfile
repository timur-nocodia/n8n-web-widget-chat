FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY apps/proxy-server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY apps/proxy-server/*.py ./
COPY apps/proxy-server/.env .env

# Copy widget files
COPY apps/chat-widget /app/chat-widget

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main_production:app", "--host", "0.0.0.0", "--port", "8000"]