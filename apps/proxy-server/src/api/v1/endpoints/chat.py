import json
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from db.base import get_db
from models.session import Session as SessionModel
from models.chat import ChatMessage as ChatMessageModel
from core.session import SessionManager
from core.security import SessionSecurityManager, ThreatDetector
from core.validation import InputValidator
from services.jwt_service import jwt_service
from services.sse_manager import sse_manager, optimized_n8n_client
from api.v1.schemas import SendMessageRequest, ChatMessage, ChatHistoryResponse
from api.v1.deps import get_current_session, get_session_manager, get_client_ip
from core.exceptions import ValidationError, RateLimitExceededError


router = APIRouter()


@router.post("/message")
async def send_message(
    message_data: SendMessageRequest,
    request: Request,
    session: SessionModel = Depends(get_current_session),
    session_manager: SessionManager = Depends(get_session_manager),
    db: AsyncSession = Depends(get_db)
):
    """Send a message and get streaming response with enhanced security"""
    try:
        client_ip = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # Enhanced security validation
        security_manager = SessionSecurityManager(db)
        await security_manager.validate_session_security(
            session, client_ip, user_agent, session.origin_domain
        )
        
        # Input validation and sanitization
        validated_content, validated_context = InputValidator.validate_chat_message(
            message_data.message, message_data.context
        )
        
        # Threat detection
        bot_detection = ThreatDetector.detect_bot_patterns(user_agent, validated_content)
        spam_detection = ThreatDetector.detect_spam_patterns(validated_content)
        
        if bot_detection["is_likely_bot"] or spam_detection["is_likely_spam"]:
            raise ValidationError("Message rejected by security filters")
        
        # Create SSE connection
        connection_id = await sse_manager.create_connection(session.session_id, client_ip)
        
        # Save user message with validated content
        user_message = ChatMessageModel(
            session_id=session.id,
            role="user",
            content=validated_content,
            metadata={
                "context": validated_context,
                "security_check": {
                    "bot_score": bot_detection["confidence_score"],
                    "spam_score": spam_detection["confidence_score"]
                },
                "client_ip": client_ip,
                "user_agent_hash": security_manager.generate_enhanced_fingerprint(user_agent, client_ip)[:16]
            }
        )
        db.add(user_message)
        await db.commit()
        
        # Update session activity and security info
        await session_manager.update_session_activity(session.session_id)
        await security_manager.update_session_security_info(
            session.session_id, client_ip, user_agent
        )
        
        # Create enhanced context for n8n
        context = {
            "session_id": session.session_id,
            "origin_domain": session.origin_domain,
            "page_url": session.page_url,
            "user_agent": user_agent,
            "ip_address": client_ip,
            "message_count": session.message_count,
            "security_context": {
                "fingerprint": session.fingerprint,
                "verified": True
            }
        }
        
        if validated_context:
            context["user_context"] = validated_context
        
        # Generate JWT for n8n
        jwt_token = jwt_service.create_chat_token(
            session_id=session.session_id,
            origin_domain=session.origin_domain,
            user_context=context
        )
        
        # Create optimized SSE response with connection management
        async def enhanced_sse_stream():
            try:
                async for response_data in optimized_n8n_client.send_message_with_retry(
                    message=validated_content,
                    session_id=session.session_id,
                    jwt_token=jwt_token,
                    context=context,
                    connection_manager=sse_manager,
                    connection_id=connection_id
                ):
                    # Format for SSE with proper content extraction
                    if response_data["event"] == "message":
                        data = response_data['data']
                        if isinstance(data, dict):
                            # Extract content from n8n response
                            if 'delta' in data and 'content' in data['delta']:
                                content = data['delta']['content']
                            elif 'content' in data:
                                content = data['content']
                            else:
                                content = str(data)
                            
                            # Format as expected by frontend
                            formatted_data = json.dumps({"content": content})
                        else:
                            # Handle string data
                            formatted_data = json.dumps({"content": str(data)})
                        
                        yield f"data: {formatted_data}\n\n"
                    elif response_data["event"] == "complete":
                        yield f"data: [DONE]\n\n"
                        break
                    elif response_data["event"] == "error":
                        error_data = response_data['data'] if isinstance(response_data['data'], dict) else {"error": str(response_data['data'])}
                        yield f"data: {json.dumps(error_data)}\n\n"
                        break
                        
            except Exception as e:
                error_data = {"error": str(e), "code": "STREAM_ERROR"}
                yield f"data: {json.dumps(error_data)}\n\n"
            finally:
                await sse_manager.close_connection(connection_id)
        
        from sse_starlette import EventSourceResponse
        return EventSourceResponse(
            enhanced_sse_stream(),
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Connection-ID": connection_id
            }
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RateLimitExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    session: SessionModel = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """Get chat history for current session"""
    try:
        # Get messages with pagination
        stmt = (
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session.id)
            .order_by(ChatMessageModel.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        
        result = await db.execute(stmt)
        messages = result.scalars().all()
        
        # Get total count
        count_stmt = select(ChatMessageModel).where(ChatMessageModel.session_id == session.id)
        count_result = await db.execute(count_stmt)
        total_count = len(count_result.scalars().all())
        
        # Convert to response models
        message_responses = [
            ChatMessage(
                id=str(msg.id),
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
                metadata=msg.metadata
            )
            for msg in messages
        ]
        
        return ChatHistoryResponse(
            messages=message_responses,
            total_count=total_count,
            session_id=session.session_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chat history: {str(e)}"
        )