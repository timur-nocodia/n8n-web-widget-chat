import logging
import traceback
import time
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from core.exceptions import (
    ChatProxyException, 
    SessionNotFoundError, 
    InvalidSessionError,
    RateLimitExceededError, 
    N8NConnectionError,
    InvalidOriginError,
    ValidationError
)

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Comprehensive error handling middleware"""
    
    def __init__(self, app):
        super().__init__(app)
        self.error_counts = {}  # In production, use Redis for distributed counting
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Log successful requests in debug mode
            if logger.isEnabledFor(logging.DEBUG):
                processing_time = time.time() - start_time
                logger.debug(f"Request processed: {request.method} {request.url.path} "
                           f"in {processing_time:.3f}s - Status: {response.status_code}")
            
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            return await self._handle_exception(e, request, processing_time)
    
    async def _handle_exception(
        self, 
        exc: Exception, 
        request: Request, 
        processing_time: float
    ) -> JSONResponse:
        """Handle different types of exceptions"""
        
        error_id = self._generate_error_id()
        client_ip = self._get_client_ip(request)
        
        # Log error details
        error_context = {
            "error_id": error_id,
            "path": request.url.path,
            "method": request.method,
            "client_ip": client_ip,
            "processing_time": processing_time,
            "user_agent": request.headers.get("user-agent", "unknown"),
            "origin": request.headers.get("origin"),
            "referer": request.headers.get("referer")
        }
        
        # Handle specific exception types
        if isinstance(exc, RateLimitExceededError):
            return await self._handle_rate_limit_error(exc, error_context)
        
        elif isinstance(exc, (SessionNotFoundError, InvalidSessionError)):
            return await self._handle_session_error(exc, error_context)
        
        elif isinstance(exc, InvalidOriginError):
            return await self._handle_origin_error(exc, error_context)
        
        elif isinstance(exc, ValidationError):
            return await self._handle_validation_error(exc, error_context)
        
        elif isinstance(exc, N8NConnectionError):
            return await self._handle_n8n_error(exc, error_context)
        
        elif isinstance(exc, HTTPException):
            return await self._handle_http_error(exc, error_context)
        
        elif isinstance(exc, StarletteHTTPException):
            return await self._handle_http_error(exc, error_context)
        
        else:
            return await self._handle_internal_error(exc, error_context)
    
    async def _handle_rate_limit_error(
        self, 
        exc: RateLimitExceededError, 
        context: Dict[str, Any]
    ) -> JSONResponse:
        """Handle rate limit exceeded errors"""
        
        logger.warning(f"Rate limit exceeded: {context}", extra=context)
        
        # Track rate limit violations
        await self._track_error("rate_limit", context["client_ip"])
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "detail": str(exc),
                "error_id": context["error_id"],
                "retry_after": 60
            },
            headers={"Retry-After": "60"}
        )
    
    async def _handle_session_error(
        self, 
        exc: Exception, 
        context: Dict[str, Any]
    ) -> JSONResponse:
        """Handle session-related errors"""
        
        logger.info(f"Session error: {exc}", extra=context)
        
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "Session error",
                "detail": "Please refresh the page and try again",
                "error_id": context["error_id"],
                "code": "SESSION_INVALID"
            }
        )
    
    async def _handle_origin_error(
        self, 
        exc: InvalidOriginError, 
        context: Dict[str, Any]
    ) -> JSONResponse:
        """Handle origin validation errors"""
        
        logger.warning(f"Origin validation failed: {exc}", extra=context)
        
        # Track suspicious origin requests
        await self._track_error("invalid_origin", context["client_ip"])
        
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": "Origin not allowed",
                "detail": "Request origin is not authorized",
                "error_id": context["error_id"],
                "code": "INVALID_ORIGIN"
            }
        )
    
    async def _handle_validation_error(
        self, 
        exc: ValidationError, 
        context: Dict[str, Any]
    ) -> JSONResponse:
        """Handle input validation errors"""
        
        logger.info(f"Validation error: {exc}", extra=context)
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Validation error",
                "detail": str(exc),
                "error_id": context["error_id"],
                "code": "VALIDATION_FAILED"
            }
        )
    
    async def _handle_n8n_error(
        self, 
        exc: N8NConnectionError, 
        context: Dict[str, Any]
    ) -> JSONResponse:
        """Handle n8n connection errors"""
        
        logger.error(f"N8N connection error: {exc}", extra=context)
        
        # Track n8n connectivity issues
        await self._track_error("n8n_connection", "system")
        
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "Service temporarily unavailable",
                "detail": "Please try again in a few moments",
                "error_id": context["error_id"],
                "retry_after": 30
            },
            headers={"Retry-After": "30"}
        )
    
    async def _handle_http_error(
        self, 
        exc: HTTPException, 
        context: Dict[str, Any]
    ) -> JSONResponse:
        """Handle HTTP exceptions"""
        
        logger.info(f"HTTP error: {exc.status_code} - {exc.detail}", extra=context)
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "Request error",
                "detail": exc.detail,
                "error_id": context["error_id"],
                "code": f"HTTP_{exc.status_code}"
            }
        )
    
    async def _handle_internal_error(
        self, 
        exc: Exception, 
        context: Dict[str, Any]
    ) -> JSONResponse:
        """Handle unexpected internal errors"""
        
        # Log full traceback for internal errors
        logger.error(
            f"Internal server error: {exc}",
            extra=context,
            exc_info=True
        )
        
        # Track internal errors for monitoring
        await self._track_error("internal_error", "system")
        
        # Don't expose internal error details to client
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "detail": "An unexpected error occurred. Please try again.",
                "error_id": context["error_id"],
                "code": "INTERNAL_ERROR"
            }
        )
    
    def _generate_error_id(self) -> str:
        """Generate unique error ID for tracking"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
            
        return request.client.host if request.client else "unknown"
    
    async def _track_error(self, error_type: str, identifier: str):
        """Track error occurrences for monitoring"""
        # In production, this would send to monitoring service
        key = f"{error_type}:{identifier}"
        
        if key not in self.error_counts:
            self.error_counts[key] = 0
        
        self.error_counts[key] += 1
        
        # Log if error count is high
        if self.error_counts[key] > 10:
            logger.warning(f"High error count for {key}: {self.error_counts[key]}")


class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    """Circuit breaker pattern for external service calls"""
    
    def __init__(self, app, failure_threshold: int = 5, recovery_timeout: int = 60):
        super().__init__(app)
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_counts = {}
        self.last_failure_times = {}
        self.circuit_open = {}
    
    async def dispatch(self, request: Request, call_next):
        # Only apply circuit breaker to n8n-dependent endpoints
        if not request.url.path.startswith('/api/v1/chat/message'):
            return await call_next(request)
        
        service_key = "n8n_service"
        
        # Check if circuit is open
        if await self._is_circuit_open(service_key):
            logger.warning(f"Circuit breaker open for {service_key}")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error": "Service temporarily unavailable",
                    "detail": "AI service is experiencing issues. Please try again later.",
                    "retry_after": self.recovery_timeout
                }
            )
        
        try:
            response = await call_next(request)
            
            # Reset failure count on successful request
            if response.status_code < 500:
                await self._record_success(service_key)
            else:
                await self._record_failure(service_key)
            
            return response
            
        except Exception as e:
            await self._record_failure(service_key)
            raise e
    
    async def _is_circuit_open(self, service_key: str) -> bool:
        """Check if circuit breaker is open"""
        if service_key not in self.circuit_open:
            return False
        
        if not self.circuit_open[service_key]:
            return False
        
        # Check if recovery timeout has passed
        last_failure = self.last_failure_times.get(service_key, 0)
        if time.time() - last_failure > self.recovery_timeout:
            # Reset circuit breaker
            self.circuit_open[service_key] = False
            self.failure_counts[service_key] = 0
            logger.info(f"Circuit breaker reset for {service_key}")
            return False
        
        return True
    
    async def _record_failure(self, service_key: str):
        """Record a service failure"""
        if service_key not in self.failure_counts:
            self.failure_counts[service_key] = 0
        
        self.failure_counts[service_key] += 1
        self.last_failure_times[service_key] = time.time()
        
        # Open circuit if threshold exceeded
        if self.failure_counts[service_key] >= self.failure_threshold:
            self.circuit_open[service_key] = True
            logger.error(f"Circuit breaker opened for {service_key} "
                        f"after {self.failure_counts[service_key]} failures")
    
    async def _record_success(self, service_key: str):
        """Record a successful service call"""
        if service_key in self.failure_counts:
            self.failure_counts[service_key] = max(0, self.failure_counts[service_key] - 1)


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """Add timeout handling for requests"""
    
    def __init__(self, app, timeout_seconds: int = 30):
        super().__init__(app)
        self.timeout_seconds = timeout_seconds
    
    async def dispatch(self, request: Request, call_next):
        try:
            # Use asyncio.wait_for for timeout
            import asyncio
            response = await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout_seconds
            )
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {request.method} {request.url.path}")
            
            return JSONResponse(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                content={
                    "error": "Request timeout",
                    "detail": f"Request took longer than {self.timeout_seconds} seconds",
                    "code": "REQUEST_TIMEOUT"
                }
            )