from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime


class CreateSessionRequest(BaseModel):
    origin_domain: str = Field(..., description="Domain of the website")
    page_url: Optional[str] = Field(None, description="Current page URL")
    user_agent: Optional[str] = Field(None, description="User agent string")
    
    @validator('origin_domain')
    def validate_domain(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Domain cannot be empty')
        return v.strip().lower()


class CreateSessionResponse(BaseModel):
    session_id: str
    expires_at: datetime


class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000, description="Chat message")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    
    @validator('message')
    def validate_message(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Message cannot be empty')
        return v.strip()


class ChatMessage(BaseModel):
    id: str
    role: str  # 'user' or 'assistant'
    content: str
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessage]
    total_count: int
    session_id: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None