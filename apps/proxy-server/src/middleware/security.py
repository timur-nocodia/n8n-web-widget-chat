from fastapi import Request, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import Response
from typing import Dict, List
from core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    def __init__(self, app, allowed_origins: List[str] = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or settings.allowed_origins
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        security_headers = {
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # XSS protection
            "X-XSS-Protection": "1; mode=block",
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions policy
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            
            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self' wss: ws:; "
                "frame-ancestors 'none';"
            ),
        }
        
        # Add HSTS in production
        if not settings.debug:
            security_headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        
        # Add headers to response
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response


class TrustedHostMiddleware(BaseHTTPMiddleware):
    """Validate Host header to prevent Host header injection"""
    
    def __init__(self, app, allowed_hosts: List[str] = None):
        super().__init__(app)
        self.allowed_hosts = allowed_hosts or self._get_allowed_hosts()
    
    def _get_allowed_hosts(self) -> List[str]:
        """Extract allowed hosts from origins"""
        hosts = []
        for origin in settings.allowed_origins:
            # Remove protocol
            host = origin.replace('https://', '').replace('http://', '')
            # Remove port if present
            host = host.split(':')[0]
            hosts.append(host)
        
        # Add localhost variants for development
        if settings.debug:
            hosts.extend(['localhost', '127.0.0.1', '0.0.0.0'])
        
        return hosts
    
    async def dispatch(self, request: Request, call_next):
        host = request.headers.get('host', '').split(':')[0]  # Remove port
        
        # Skip validation for health checks
        if request.url.path == "/health":
            return await call_next(request)
        
        if host and self.allowed_hosts and host not in self.allowed_hosts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid host header"
            )
        
        return await call_next(request)


class OriginValidationMiddleware(BaseHTTPMiddleware):
    """Enhanced origin validation beyond CORS"""
    
    def __init__(self, app, allowed_origins: List[str] = None):
        super().__init__(app)
        self.allowed_origins = set(allowed_origins or settings.allowed_origins)
        self.allowed_domains = self._extract_domains()
    
    def _extract_domains(self) -> set:
        """Extract domains from origins for flexible matching"""
        domains = set()
        for origin in self.allowed_origins:
            # Remove protocol and port
            domain = origin.replace('https://', '').replace('http://', '')
            domain = domain.split(':')[0]
            domains.add(domain)
        return domains
    
    async def dispatch(self, request: Request, call_next):
        # Skip validation for preflight requests and health checks
        if (request.method == "OPTIONS" or 
            request.url.path in ["/health", "/docs", "/openapi.json"]):
            return await call_next(request)
        
        origin = request.headers.get('origin')
        referer = request.headers.get('referer')
        
        # For API requests, we need either Origin or Referer
        if request.url.path.startswith('/api/'):
            if not origin and not referer:
                # Allow requests without origin/referer in development
                if settings.debug:
                    return await call_next(request)
                
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Missing origin or referer header"
                )
            
            # Validate origin if present
            if origin and not self._is_origin_allowed(origin):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Origin not allowed"
                )
            
            # Validate referer if present
            if referer and not self._is_referer_allowed(referer):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Referer not allowed"
                )
        
        return await call_next(request)
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed"""
        if origin in self.allowed_origins:
            return True
        
        # Extract domain from origin
        try:
            domain = origin.replace('https://', '').replace('http://', '')
            domain = domain.split(':')[0]
            return domain in self.allowed_domains
        except:
            return False
    
    def _is_referer_allowed(self, referer: str) -> bool:
        """Check if referer domain is allowed"""
        try:
            # Extract domain from referer URL
            domain = referer.replace('https://', '').replace('http://', '')
            domain = domain.split('/')[0].split(':')[0]
            return domain in self.allowed_domains
        except:
            return False


class AntiCSRFMiddleware(BaseHTTPMiddleware):
    """Basic CSRF protection using double-submit cookies"""
    
    CSRF_EXEMPT_METHODS = {'GET', 'HEAD', 'OPTIONS', 'TRACE'}
    CSRF_EXEMPT_PATHS = {'/health', '/docs', '/openapi.json'}
    
    async def dispatch(self, request: Request, call_next):
        # Skip CSRF protection for exempt methods and paths
        if (request.method in self.CSRF_EXEMPT_METHODS or
            request.url.path in self.CSRF_EXEMPT_PATHS):
            return await call_next(request)
        
        # For state-changing requests, validate CSRF token
        if request.url.path.startswith('/api/'):
            csrf_token_header = request.headers.get('x-csrf-token')
            csrf_token_cookie = request.cookies.get('csrf_token')
            
            # In development, be more lenient
            if settings.debug and not csrf_token_header:
                return await call_next(request)
            
            if not csrf_token_header or not csrf_token_cookie:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF token missing"
                )
            
            if csrf_token_header != csrf_token_cookie:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF token mismatch"
                )
        
        return await call_next(request)


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """Limit request body size"""
    
    def __init__(self, app, max_size: int = 1024 * 1024):  # 1MB default
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get('content-length')
        
        if content_length:
            if int(content_length) > self.max_size:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Request body too large (max {self.max_size} bytes)"
                )
        
        return await call_next(request)