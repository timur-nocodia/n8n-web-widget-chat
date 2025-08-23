from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from jose import jwt, JWTError
from core.config import settings
from core.exceptions import ValidationError
import socket


def get_server_ip():
    """Get the server's external IP address for n8n validation"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "unknown"


class JWTService:
    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.session_secret_key = settings.session_secret_key  # For n8n JWT validation
        self.algorithm = settings.jwt_algorithm
        self.expiration_seconds = 30  # Short expiration for n8n tokens (security)
        self.server_ip = get_server_ip()

    def create_token(self, payload: Dict[str, Any], use_session_key: bool = False) -> str:
        """Create a JWT token"""
        to_encode = payload.copy()
        # Use short expiration for n8n tokens
        if use_session_key:
            expire = datetime.utcnow() + timedelta(seconds=self.expiration_seconds)
        else:
            expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        
        # Use session key for n8n tokens
        secret = self.session_secret_key if use_session_key else self.secret_key
        
        try:
            encoded_jwt = jwt.encode(to_encode, secret, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            raise ValidationError(f"Failed to create token: {str(e)}")

    def verify_token(self, token: str, use_session_key: bool = False) -> Dict[str, Any]:
        """Verify and decode a JWT token"""
        secret = self.session_secret_key if use_session_key else self.secret_key
        try:
            payload = jwt.decode(token, secret, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            raise ValidationError(f"Invalid token: {str(e)}")

    def create_n8n_token(
        self,
        session_id: str,
        origin_domain: str,
        page_url: Optional[str] = None,
        client_ip: str = "unknown",
        user_agent: str = ""
    ) -> str:
        """Create a token specifically for n8n webhook validation"""
        payload = {
            "session_id": session_id,
            "origin_domain": origin_domain,
            "page_url": page_url,
            "client_ip": client_ip,
            "server_ip": self.server_ip,
            "user_agent": user_agent,
            "timestamp": datetime.utcnow().timestamp(),
            "type": "n8n_chat"
        }
        
        # Use SESSION_SECRET_KEY for n8n tokens
        return self.create_token(payload, use_session_key=True)

    def verify_n8n_token(self, token: str) -> Dict[str, Any]:
        """Verify an n8n token and return payload"""
        # Use SESSION_SECRET_KEY for n8n tokens
        payload = self.verify_token(token, use_session_key=True)
        
        if payload.get("type") != "n8n_chat":
            raise ValidationError("Invalid token type for n8n")
            
        return payload


jwt_service = JWTService()