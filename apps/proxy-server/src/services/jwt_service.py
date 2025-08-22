from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from jose import jwt, JWTError
from core.config import settings
from core.exceptions import ValidationError


class JWTService:
    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.expiration_hours = settings.jwt_expiration_hours

    def create_token(self, payload: Dict[str, Any]) -> str:
        """Create a JWT token"""
        to_encode = payload.copy()
        expire = datetime.utcnow() + timedelta(hours=self.expiration_hours)
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            raise ValidationError(f"Failed to create token: {str(e)}")

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            raise ValidationError(f"Invalid token: {str(e)}")

    def create_chat_token(
        self,
        session_id: str,
        origin_domain: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a token specifically for chat requests to n8n"""
        payload = {
            "session_id": session_id,
            "origin_domain": origin_domain,
            "type": "chat",
        }
        
        if user_context:
            payload["user_context"] = user_context
            
        return self.create_token(payload)

    def verify_chat_token(self, token: str) -> Dict[str, Any]:
        """Verify a chat token and return payload"""
        payload = self.verify_token(token)
        
        if payload.get("type") != "chat":
            raise ValidationError("Invalid token type")
            
        return payload


jwt_service = JWTService()