import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.config import settings
from models.session import Session as SessionModel
from core.exceptions import SessionNotFoundError, InvalidSessionError


class SessionManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def generate_session_id() -> str:
        """Generate a secure session ID"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_fingerprint(user_agent: str, ip_address: str) -> str:
        """Generate a browser fingerprint"""
        fingerprint_data = f"{user_agent}:{ip_address}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]

    async def create_session(
        self,
        origin_domain: str,
        page_url: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> SessionModel:
        """Create a new session"""
        session_id = self.generate_session_id()
        fingerprint = None
        
        if user_agent and ip_address:
            fingerprint = self.generate_fingerprint(user_agent, ip_address)

        expires_at = datetime.utcnow() + timedelta(seconds=settings.session_cookie_max_age)

        session = SessionModel(
            session_id=session_id,
            origin_domain=origin_domain,
            page_url=page_url,
            user_agent=user_agent,
            ip_address=ip_address,
            fingerprint=fingerprint,
            expires_at=expires_at,
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: str) -> SessionModel:
        """Get session by session_id"""
        stmt = select(SessionModel).where(SessionModel.session_id == session_id)
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            raise SessionNotFoundError("Session not found")

        if not session.is_active or session.expires_at < datetime.utcnow():
            raise InvalidSessionError("Session expired or inactive")

        return session

    async def update_session_activity(self, session_id: str) -> None:
        """Update session last activity"""
        session = await self.get_session(session_id)
        session.updated_at = datetime.utcnow()
        session.message_count += 1
        await self.db.commit()

    async def deactivate_session(self, session_id: str) -> None:
        """Deactivate a session"""
        session = await self.get_session(session_id)
        session.is_active = False
        await self.db.commit()