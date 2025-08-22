import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from models.session import Session as SessionModel
from services.rate_limiter import rate_limiter
from core.exceptions import InvalidSessionError, RateLimitExceededError


class SessionSecurityManager:
    """Enhanced session security with threat detection"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    @staticmethod
    def generate_enhanced_fingerprint(
        user_agent: str,
        ip_address: str,
        accept_language: Optional[str] = None,
        screen_resolution: Optional[str] = None
    ) -> str:
        """Generate enhanced browser fingerprint"""
        fingerprint_data = f"{user_agent}:{ip_address}"
        
        if accept_language:
            fingerprint_data += f":{accept_language}"
        
        if screen_resolution:
            fingerprint_data += f":{screen_resolution}"
        
        # Add timestamp component for session tracking
        timestamp_component = str(int(time.time() // 3600))  # Hour-based
        fingerprint_data += f":{timestamp_component}"
        
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]
    
    async def detect_suspicious_activity(
        self, 
        session: SessionModel,
        current_ip: str,
        current_user_agent: str
    ) -> Dict[str, Any]:
        """Detect suspicious session activity"""
        suspicious_indicators = []
        risk_score = 0
        
        # IP address change detection
        if session.ip_address and session.ip_address != current_ip:
            suspicious_indicators.append("ip_change")
            risk_score += 30
        
        # User agent change detection
        if session.user_agent and session.user_agent != current_user_agent:
            suspicious_indicators.append("user_agent_change")
            risk_score += 20
        
        # Check for rapid session creation from same IP
        recent_sessions = await self._count_recent_sessions_by_ip(current_ip)
        if recent_sessions > 5:  # More than 5 sessions in last hour
            suspicious_indicators.append("rapid_session_creation")
            risk_score += 40
        
        # Check message frequency
        if session.message_count > 100:  # High message count
            session_age = (datetime.utcnow() - session.created_at).total_seconds() / 3600
            if session_age < 1:  # More than 100 messages in 1 hour
                suspicious_indicators.append("high_message_frequency")
                risk_score += 25
        
        # Check for session duration anomalies
        session_duration = (datetime.utcnow() - session.created_at).total_seconds() / 3600
        if session_duration > 48:  # Session older than 48 hours
            suspicious_indicators.append("long_session_duration")
            risk_score += 15
        
        return {
            "suspicious_indicators": suspicious_indicators,
            "risk_score": risk_score,
            "is_suspicious": risk_score > 50,
            "action_required": risk_score > 75
        }
    
    async def _count_recent_sessions_by_ip(self, ip_address: str) -> int:
        """Count sessions created from IP in last hour"""
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        stmt = select(SessionModel).where(
            SessionModel.ip_address == ip_address,
            SessionModel.created_at >= one_hour_ago
        )
        
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()
        return len(sessions)
    
    async def validate_session_security(
        self,
        session: SessionModel,
        current_ip: str,
        current_user_agent: str,
        origin_domain: str
    ) -> None:
        """Comprehensive session security validation"""
        
        # Basic session validation
        if not session.is_active:
            raise InvalidSessionError("Session is inactive")
        
        if session.expires_at < datetime.utcnow():
            raise InvalidSessionError("Session has expired")
        
        # Origin validation
        if session.origin_domain != origin_domain:
            raise InvalidSessionError("Origin domain mismatch")
        
        # Suspicious activity detection
        security_check = await self.detect_suspicious_activity(
            session, current_ip, current_user_agent
        )
        
        if security_check["action_required"]:
            # Immediately deactivate session
            await self.deactivate_session(session.session_id, "Suspicious activity detected")
            raise InvalidSessionError("Session terminated due to security concerns")
        
        if security_check["is_suspicious"]:
            # Log suspicious activity (in production, send to monitoring)
            await self._log_suspicious_activity(session, security_check, current_ip)
        
        # Rate limiting checks
        await self._check_session_rate_limits(session.session_id, current_ip)
    
    async def _check_session_rate_limits(self, session_id: str, ip_address: str):
        """Check various rate limits"""
        
        # IP-based rate limiting
        ip_limit_result = await rate_limiter.check_ip_rate_limit(ip_address)
        if not ip_limit_result["allowed"]:
            raise RateLimitExceededError(
                f"IP rate limit exceeded. Retry after {ip_limit_result['retry_after']} seconds"
            )
        
        # Session-based rate limiting
        session_limit_result = await rate_limiter.check_session_rate_limit(session_id)
        if not session_limit_result["allowed"]:
            raise RateLimitExceededError(
                f"Session rate limit exceeded. Retry after {session_limit_result['retry_after']} seconds"
            )
        
        # Check if IP is blocked
        if await rate_limiter.is_blocked(f"ip:{ip_address}"):
            raise RateLimitExceededError("IP address is temporarily blocked")
        
        # Check if session is blocked
        if await rate_limiter.is_blocked(f"session:{session_id}"):
            raise RateLimitExceededError("Session is temporarily blocked")
    
    async def _log_suspicious_activity(
        self,
        session: SessionModel,
        security_check: Dict[str, Any],
        current_ip: str
    ):
        """Log suspicious activity for monitoring"""
        # In production, this would send to logging/monitoring service
        # For now, we'll store in database or log file
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session.session_id,
            "ip_address": current_ip,
            "origin_domain": session.origin_domain,
            "risk_score": security_check["risk_score"],
            "indicators": security_check["suspicious_indicators"],
            "user_agent": session.user_agent,
            "message_count": session.message_count,
            "session_age_hours": (datetime.utcnow() - session.created_at).total_seconds() / 3600
        }
        
        # In a real implementation, send to logging service
        print(f"SECURITY_ALERT: {log_entry}")  # Temporary logging
    
    async def deactivate_session(self, session_id: str, reason: str = "Security violation"):
        """Deactivate session for security reasons"""
        stmt = (
            update(SessionModel)
            .where(SessionModel.session_id == session_id)
            .values(
                is_active=False,
                updated_at=datetime.utcnow()
            )
        )
        
        await self.db.execute(stmt)
        await self.db.commit()
        
        # Block session temporarily
        await rate_limiter.block_key(f"session:{session_id}", 3600)  # 1 hour block
    
    async def update_session_security_info(
        self,
        session_id: str,
        ip_address: str,
        user_agent: str
    ):
        """Update session with current security info"""
        fingerprint = self.generate_enhanced_fingerprint(user_agent, ip_address)
        
        stmt = (
            update(SessionModel)
            .where(SessionModel.session_id == session_id)
            .values(
                ip_address=ip_address,
                user_agent=user_agent,
                fingerprint=fingerprint,
                updated_at=datetime.utcnow()
            )
        )
        
        await self.db.execute(stmt)
        await self.db.commit()


class ThreatDetector:
    """Advanced threat detection system"""
    
    @staticmethod
    def detect_bot_patterns(user_agent: str, message_content: str) -> Dict[str, Any]:
        """Detect potential bot activity"""
        bot_indicators = []
        confidence_score = 0
        
        # User agent analysis
        bot_user_agents = [
            'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget', 'python-requests',
            'postman', 'insomnia', 'httpie'
        ]
        
        if any(bot_ua in user_agent.lower() for bot_ua in bot_user_agents):
            bot_indicators.append("suspicious_user_agent")
            confidence_score += 40
        
        # Message pattern analysis
        if len(message_content) < 5:
            bot_indicators.append("very_short_message")
            confidence_score += 10
        
        # Repeated character patterns
        if len(set(message_content.lower())) < len(message_content) * 0.3:
            bot_indicators.append("repeated_characters")
            confidence_score += 20
        
        # Common bot test messages
        bot_test_messages = [
            'test', 'hello', 'hi', '123', 'abc', 'test message',
            'automated test', 'bot test'
        ]
        
        if message_content.lower().strip() in bot_test_messages:
            bot_indicators.append("bot_test_message")
            confidence_score += 30
        
        return {
            "indicators": bot_indicators,
            "confidence_score": confidence_score,
            "is_likely_bot": confidence_score > 50
        }
    
    @staticmethod
    def detect_spam_patterns(message_content: str) -> Dict[str, Any]:
        """Detect potential spam messages"""
        spam_indicators = []
        confidence_score = 0
        
        # URL detection
        url_patterns = ['http://', 'https://', 'www.', '.com', '.org', '.net']
        url_count = sum(1 for pattern in url_patterns if pattern in message_content.lower())
        
        if url_count > 2:
            spam_indicators.append("multiple_urls")
            confidence_score += 30
        
        # Excessive capitalization
        if len([c for c in message_content if c.isupper()]) > len(message_content) * 0.5:
            spam_indicators.append("excessive_caps")
            confidence_score += 20
        
        # Spam keywords
        spam_keywords = [
            'free', 'win', 'prize', 'money', 'cash', 'discount', 'offer',
            'limited time', 'act now', 'click here', 'buy now'
        ]
        
        keyword_count = sum(1 for keyword in spam_keywords if keyword in message_content.lower())
        if keyword_count > 2:
            spam_indicators.append("spam_keywords")
            confidence_score += 25
        
        # Excessive punctuation
        punct_count = len([c for c in message_content if c in '!?.,;:'])
        if punct_count > len(message_content) * 0.3:
            spam_indicators.append("excessive_punctuation")
            confidence_score += 15
        
        return {
            "indicators": spam_indicators,
            "confidence_score": confidence_score,
            "is_likely_spam": confidence_score > 40
        }