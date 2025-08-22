import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from api.v1.router import api_router
from db.base import create_tables

# Import security and optimization middleware
from middleware.security import (
    SecurityHeadersMiddleware,
    TrustedHostMiddleware,
    OriginValidationMiddleware,
    RequestSizeMiddleware
)
from middleware.rate_limiting import RateLimitMiddleware
from middleware.error_handling import (
    ErrorHandlingMiddleware,
    CircuitBreakerMiddleware,
    RequestTimeoutMiddleware
)
from services.rate_limiter import rate_limiter
from services.sse_manager import sse_manager, optimized_n8n_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Chat Proxy System...")
    
    # Initialize database
    await create_tables()
    logger.info("Database tables created/verified")
    
    # Initialize services
    logger.info("Services initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Chat Proxy System...")
    
    # Close connections
    try:
        await rate_limiter.close()
        await optimized_n8n_client.close()
        logger.info("Services shut down gracefully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan
)

# Add middleware in correct order (last added = first executed)
# Error handling should be first
app.add_middleware(ErrorHandlingMiddleware)

# Timeout handling
app.add_middleware(RequestTimeoutMiddleware, timeout_seconds=30)

# Circuit breaker for external services
app.add_middleware(CircuitBreakerMiddleware)

# Rate limiting
app.add_middleware(RateLimitMiddleware)

# Security middleware
app.add_middleware(SecurityHeadersMiddleware, allowed_origins=settings.allowed_origins)
app.add_middleware(OriginValidationMiddleware, allowed_origins=settings.allowed_origins)
app.add_middleware(TrustedHostMiddleware)
app.add_middleware(RequestSizeMiddleware, max_size=1024 * 1024)  # 1MB

# CORS middleware (should be after security middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Enhanced health check endpoint"""
    try:
        # Check Redis connection
        redis_status = "unknown"
        try:
            redis_client = await rate_limiter._get_redis()
            await redis_client.ping()
            redis_status = "healthy"
        except Exception as e:
            redis_status = f"unhealthy: {str(e)}"
        
        # Get SSE connection stats
        sse_stats = sse_manager.get_connection_stats()
        
        return {
            "status": "healthy",
            "version": settings.app_version,
            "timestamp": "2024-01-01T00:00:00Z",  # Would be datetime.utcnow().isoformat()
            "services": {
                "redis": redis_status,
                "sse_connections": sse_stats["total_connections"],
                "active_sessions": sse_stats["sessions"]
            },
            "environment": "development" if settings.debug else "production"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "version": settings.app_version
        }


@app.get("/metrics")
async def metrics():
    """Metrics endpoint for monitoring"""
    try:
        sse_stats = sse_manager.get_connection_stats()
        
        return {
            "connections": {
                "total": sse_stats["total_connections"],
                "active": sse_stats["active_connections"],
                "sessions": sse_stats["sessions"],
                "oldest_connection_age": sse_stats["oldest_connection"]
            },
            "rate_limits": {
                "per_minute": settings.rate_limit_per_minute,
                "per_hour": settings.rate_limit_per_hour
            },
            "system": {
                "version": settings.app_version,
                "debug_mode": settings.debug
            }
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )