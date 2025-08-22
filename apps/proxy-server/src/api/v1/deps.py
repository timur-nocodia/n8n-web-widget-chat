from fastapi import Depends, HTTPException, status, Cookie, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from db.base import get_db
from core.session import SessionManager
from core.exceptions import SessionNotFoundError, InvalidSessionError, InvalidOriginError
from core.config import settings


async def get_session_manager(db: AsyncSession = Depends(get_db)) -> SessionManager:
    """Get session manager dependency"""
    return SessionManager(db)


def get_client_ip(request: Request) -> str:
    """Get client IP address"""
    # Check for forwarded IP first (load balancer/proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
        
    return request.client.host if request.client else "unknown"


def validate_origin(request: Request) -> str:
    """Validate request origin"""
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    
    # Extract domain from origin or referer
    domain = None
    if origin:
        # Remove protocol and path
        domain = origin.replace("https://", "").replace("http://", "").split("/")[0]
    elif referer:
        # Extract domain from referer
        domain = referer.replace("https://", "").replace("http://", "").split("/")[0]
    
    if not domain:
        raise InvalidOriginError("No valid origin found")
    
    # In development, allow any origin
    if settings.debug:
        return domain
    
    # In production, validate against allowed origins
    allowed_domains = [
        origin.replace("https://", "").replace("http://", "").split("/")[0] 
        for origin in settings.allowed_origins
    ]
    
    if domain not in allowed_domains:
        raise InvalidOriginError(f"Origin {domain} not allowed")
    
    return domain


async def get_current_session(
    request: Request,
    session_manager: SessionManager = Depends(get_session_manager),
    chat_session_id: Optional[str] = Cookie(None, alias=settings.session_cookie_name)
):
    """Get current session from cookie"""
    if not chat_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No session found"
        )
    
    try:
        session = await session_manager.get_session(chat_session_id)
        
        # Validate origin matches session
        current_origin = validate_origin(request)
        if session.origin_domain != current_origin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Origin mismatch"
            )
        
        return session
        
    except (SessionNotFoundError, InvalidSessionError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    except InvalidOriginError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )