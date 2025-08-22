from fastapi import Request, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any
from services.rate_limiter import rate_limiter
from core.exceptions import RateLimitExceededError
from api.v1.deps import get_client_ip, validate_origin
import time


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis sliding window"""
    
    def __init__(self, app):
        super().__init__(app)
        self.exempt_paths = {'/health', '/docs', '/openapi.json'}
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # Skip rate limiting for OPTIONS requests
        if request.method == "OPTIONS":
            return await call_next(request)
        
        try:
            # Get client IP
            client_ip = get_client_ip(request)
            
            # Check IP-based rate limits
            await self._check_ip_rate_limits(request, client_ip)
            
            # Check domain-based rate limits for API requests
            if request.url.path.startswith('/api/'):
                await self._check_domain_rate_limits(request)
            
            # Check session-based rate limits for chat endpoints
            if request.url.path.startswith('/api/v1/chat/'):
                await self._check_session_rate_limits(request)
            
            # Proceed with request
            response = await call_next(request)
            
            # Add rate limit headers to response
            response = await self._add_rate_limit_headers(response, client_ip)
            
            return response
            
        except RateLimitExceededError as e:
            return await self._create_rate_limit_response(str(e), request)
        except Exception as e:
            # Don't let rate limiting break the application
            return await call_next(request)
    
    async def _check_ip_rate_limits(self, request: Request, client_ip: str):
        """Check IP-based rate limits"""
        if await rate_limiter.is_blocked(f"ip:{client_ip}"):
            raise RateLimitExceededError("IP address is temporarily blocked")
        
        result = await rate_limiter.check_ip_rate_limit(client_ip)
        if not result["allowed"]:
            # Block IP if they're consistently hitting limits
            if result["count"] > result["limit"] * 1.5:
                await rate_limiter.block_key(f"ip:{client_ip}", 300)  # 5 minute block
            
            raise RateLimitExceededError(
                f"IP rate limit exceeded. Try again in {result['retry_after']} seconds"
            )
    
    async def _check_domain_rate_limits(self, request: Request):
        """Check domain-based rate limits"""
        try:
            origin_domain = validate_origin(request)
            
            result = await rate_limiter.check_domain_rate_limit(origin_domain)
            if not result["allowed"]:
                raise RateLimitExceededError(
                    f"Domain rate limit exceeded. Try again in {result['retry_after']} seconds"
                )
        except Exception:
            # If we can't validate origin, skip domain rate limiting
            pass
    
    async def _check_session_rate_limits(self, request: Request):
        """Check session-based rate limits for chat endpoints"""
        session_id = request.cookies.get('chat_session_id')
        
        if session_id:
            if await rate_limiter.is_blocked(f"session:{session_id}"):
                raise RateLimitExceededError("Session is temporarily blocked")
            
            result = await rate_limiter.check_session_rate_limit(session_id)
            if not result["allowed"]:
                raise RateLimitExceededError(
                    f"Session rate limit exceeded. Try again in {result['retry_after']} seconds"
                )
    
    async def _add_rate_limit_headers(self, response, client_ip: str):
        """Add rate limit information to response headers"""
        try:
            # Get current rate limit info
            ip_info = await rate_limiter.get_rate_limit_info(f"rate_limit:ip:{client_ip}:minute")
            
            if ip_info:
                response.headers["X-RateLimit-Limit"] = "60"
                response.headers["X-RateLimit-Remaining"] = str(max(0, 60 - ip_info["count"]))
                response.headers["X-RateLimit-Reset"] = str(int(time.time()) + ip_info["ttl"])
        except Exception:
            # Don't fail the request if we can't add headers
            pass
        
        return response
    
    async def _create_rate_limit_response(self, message: str, request: Request) -> JSONResponse:
        """Create rate limit exceeded response"""
        client_ip = get_client_ip(request)
        
        # Get retry after time
        retry_after = 60  # Default 1 minute
        
        try:
            ip_info = await rate_limiter.get_rate_limit_info(f"rate_limit:ip:{client_ip}:minute")
            if ip_info and ip_info["ttl"] > 0:
                retry_after = ip_info["ttl"]
        except Exception:
            pass
        
        headers = {
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": "60",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(time.time()) + retry_after)
        }
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "detail": message,
                "retry_after": retry_after
            },
            headers=headers
        )


class AdaptiveRateLimitMiddleware(BaseHTTPMiddleware):
    """Advanced rate limiting with adaptive thresholds"""
    
    def __init__(self, app):
        super().__init__(app)
        self.base_limits = {
            "ip_per_minute": 60,
            "ip_per_hour": 1000,
            "session_per_minute": 30,
            "domain_per_minute": 1000
        }
        self.suspicious_penalty_multiplier = 0.5  # Reduce limits by 50% for suspicious activity
    
    async def dispatch(self, request: Request, call_next):
        # Skip for exempt paths
        if (request.url.path in {'/health', '/docs', '/openapi.json'} or 
            request.method == "OPTIONS"):
            return await call_next(request)
        
        try:
            client_ip = get_client_ip(request)
            
            # Check if IP has suspicious activity history
            is_suspicious = await self._check_suspicious_history(client_ip)
            
            # Apply adaptive limits
            limits = self._calculate_adaptive_limits(is_suspicious)
            
            # Perform rate limit checks with adaptive limits
            await self._check_adaptive_rate_limits(request, client_ip, limits)
            
            response = await call_next(request)
            
            # Track successful requests for reputation scoring
            await self._update_reputation_score(client_ip, "success")
            
            return response
            
        except RateLimitExceededError as e:
            # Track failed requests
            client_ip = get_client_ip(request)
            await self._update_reputation_score(client_ip, "rate_limited")
            
            return await self._create_adaptive_rate_limit_response(str(e))
        except Exception:
            return await call_next(request)
    
    async def _check_suspicious_history(self, client_ip: str) -> bool:
        """Check if IP has history of suspicious activity"""
        try:
            # Check reputation score
            reputation_key = f"reputation:{client_ip}"
            reputation_info = await rate_limiter.get_rate_limit_info(reputation_key)
            
            if reputation_info and reputation_info.get("count", 0) < -10:
                return True  # Negative reputation indicates suspicious activity
            
            # Check recent blocks
            if await rate_limiter.is_blocked(f"ip:{client_ip}"):
                return True
            
            return False
        except Exception:
            return False
    
    def _calculate_adaptive_limits(self, is_suspicious: bool) -> Dict[str, int]:
        """Calculate adaptive rate limits based on reputation"""
        limits = self.base_limits.copy()
        
        if is_suspicious:
            # Reduce limits for suspicious IPs
            for key in limits:
                limits[key] = int(limits[key] * self.suspicious_penalty_multiplier)
        
        return limits
    
    async def _check_adaptive_rate_limits(
        self, 
        request: Request, 
        client_ip: str, 
        limits: Dict[str, int]
    ):
        """Check rate limits with adaptive thresholds"""
        
        # IP minute limit
        result = await rate_limiter.check_rate_limit(
            f"rate_limit:ip:{client_ip}:minute",
            limits["ip_per_minute"],
            60,
            f"ip_{client_ip}"
        )
        
        if not result["allowed"]:
            raise RateLimitExceededError(
                f"IP rate limit exceeded ({limits['ip_per_minute']}/min). "
                f"Try again in {result['retry_after']} seconds"
            )
        
        # IP hour limit
        result = await rate_limiter.check_rate_limit(
            f"rate_limit:ip:{client_ip}:hour",
            limits["ip_per_hour"],
            3600,
            f"ip_{client_ip}"
        )
        
        if not result["allowed"]:
            raise RateLimitExceededError(
                f"IP hourly limit exceeded ({limits['ip_per_hour']}/hour). "
                f"Try again in {result['retry_after']} seconds"
            )
    
    async def _update_reputation_score(self, client_ip: str, event_type: str):
        """Update IP reputation score based on behavior"""
        reputation_key = f"reputation:{client_ip}"
        
        try:
            if event_type == "success":
                # Increment reputation for successful requests (up to max)
                current_score = await rate_limiter.increment_counter(f"{reputation_key}:positive", 3600)
                if current_score > 100:  # Cap positive reputation
                    await rate_limiter.increment_counter(f"{reputation_key}:positive", 0)  # Reset
            
            elif event_type == "rate_limited":
                # Decrease reputation for rate limiting
                await rate_limiter.increment_counter(f"{reputation_key}:negative", 3600)
                
                # If too many negative events, block IP temporarily
                negative_score = await rate_limiter.increment_counter(f"{reputation_key}:negative", 0)
                if negative_score > 10:  # More than 10 rate limit violations in an hour
                    await rate_limiter.block_key(f"ip:{client_ip}", 1800)  # 30 minute block
        
        except Exception:
            # Don't fail the request if reputation tracking fails
            pass
    
    async def _create_adaptive_rate_limit_response(self, message: str) -> JSONResponse:
        """Create adaptive rate limit response"""
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "detail": message,
                "info": "Rate limits are adaptive based on usage patterns"
            }
        )