from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from db.base import get_db
from core.session import SessionManager
from api.v1.schemas import CreateSessionRequest, CreateSessionResponse, ErrorResponse
from api.v1.deps import get_session_manager, get_client_ip, validate_origin
from core.config import settings


router = APIRouter()


@router.post("/create", response_model=CreateSessionResponse)
async def create_session(
    request_data: CreateSessionRequest,
    request: Request,
    response: Response,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Create a new chat session"""
    try:
        # Validate origin
        origin_domain = validate_origin(request)
        
        # Get client info
        ip_address = get_client_ip(request)
        user_agent = request.headers.get("user-agent")
        
        # Create session
        session = await session_manager.create_session(
            origin_domain=origin_domain,
            page_url=request_data.page_url,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        # Set secure cookie
        response.set_cookie(
            key=settings.session_cookie_name,
            value=session.session_id,
            max_age=settings.session_cookie_max_age,
            httponly=True,
            secure=not settings.debug,  # HTTPS in production
            samesite="lax"
        )
        
        return CreateSessionResponse(
            session_id=session.session_id,
            expires_at=session.expires_at
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )


@router.delete("/destroy")
async def destroy_session(
    request: Request,
    response: Response,
    session_manager: SessionManager = Depends(get_session_manager),
    chat_session_id: str = Depends(lambda r: r.cookies.get(settings.session_cookie_name))
):
    """Destroy current session"""
    if not chat_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active session"
        )
    
    try:
        await session_manager.deactivate_session(chat_session_id)
        
        # Clear cookie
        response.delete_cookie(
            key=settings.session_cookie_name,
            httponly=True,
            secure=not settings.debug,
            samesite="lax"
        )
        
        return {"message": "Session destroyed"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to destroy session: {str(e)}"
        )