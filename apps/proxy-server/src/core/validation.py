import re
import html
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, validator
from core.exceptions import ValidationError


class MessageValidator:
    """Comprehensive message validation and sanitization"""
    
    # Suspicious patterns that might indicate attacks
    SUSPICIOUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript URLs
        r'vbscript:',  # VBScript URLs
        r'on\w+\s*=',  # Event handlers (onclick, onload, etc.)
        r'data:text/html',  # Data URLs with HTML
        r'<iframe[^>]*>',  # Iframes
        r'<object[^>]*>',  # Object tags
        r'<embed[^>]*>',  # Embed tags
        r'<link[^>]*>',  # Link tags
        r'<meta[^>]*>',  # Meta tags
        r'<base[^>]*>',  # Base tags
    ]
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
        r"(--|#|\/\*|\*\/)",  # SQL comments
        r"(\bor\b.*?=.*?=|\band\b.*?=.*?=)",  # Boolean injections
        r"(char\(|ascii\(|substring\(|length\()",  # SQL functions
        r"(\bxp_|\bsp_)",  # SQL Server extended procedures
    ]
    
    @classmethod
    def validate_message_content(cls, content: str) -> str:
        """Validate and sanitize message content"""
        if not content or not isinstance(content, str):
            raise ValidationError("Message content is required")
        
        # Length validation
        if len(content) > 10000:
            raise ValidationError("Message too long (max 10,000 characters)")
        
        if len(content.strip()) == 0:
            raise ValidationError("Message cannot be empty")
        
        # Check for suspicious patterns
        content_lower = content.lower()
        for pattern in cls.SUSPICIOUS_PATTERNS:
            if re.search(pattern, content_lower, re.IGNORECASE | re.DOTALL):
                raise ValidationError("Message contains potentially harmful content")
        
        # Check for SQL injection patterns
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, content_lower, re.IGNORECASE):
                raise ValidationError("Message contains potentially harmful SQL patterns")
        
        # HTML entity encoding for safety
        sanitized_content = html.escape(content)
        
        # Remove null bytes and control characters (except newlines and tabs)
        sanitized_content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized_content)
        
        return sanitized_content.strip()
    
    @classmethod
    def validate_context(cls, context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate context data"""
        if not context:
            return None
        
        if not isinstance(context, dict):
            raise ValidationError("Context must be a dictionary")
        
        # Limit context size
        if len(str(context)) > 5000:
            raise ValidationError("Context data too large")
        
        # Validate context keys and values
        validated_context = {}
        allowed_keys = {
            'user_id', 'page_title', 'page_section', 'product_id', 
            'category', 'search_query', 'user_intent', 'language',
            'timezone', 'custom_data'
        }
        
        for key, value in context.items():
            if not isinstance(key, str):
                continue
                
            # Only allow alphanumeric keys with underscores
            if not re.match(r'^[a-zA-Z0-9_]+$', key):
                continue
                
            if key not in allowed_keys:
                continue
            
            # Validate and sanitize values
            if isinstance(value, str):
                if len(value) > 1000:
                    continue
                validated_context[key] = html.escape(value)
            elif isinstance(value, (int, float, bool)):
                validated_context[key] = value
            elif isinstance(value, list):
                # Only allow simple lists of strings/numbers
                if len(value) > 100:
                    continue
                clean_list = []
                for item in value[:100]:  # Limit list size
                    if isinstance(item, str) and len(item) <= 500:
                        clean_list.append(html.escape(item))
                    elif isinstance(item, (int, float)):
                        clean_list.append(item)
                if clean_list:
                    validated_context[key] = clean_list
        
        return validated_context if validated_context else None


class DomainValidator:
    """Domain and URL validation"""
    
    @classmethod
    def validate_domain(cls, domain: str) -> str:
        """Validate domain format"""
        if not domain or not isinstance(domain, str):
            raise ValidationError("Domain is required")
        
        domain = domain.strip().lower()
        
        # Remove protocol if present
        domain = re.sub(r'^https?://', '', domain)
        
        # Remove port if present
        domain = re.sub(r':\d+$', '', domain)
        
        # Remove path if present
        domain = domain.split('/')[0]
        
        # Basic domain format validation
        if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', domain):
            raise ValidationError("Invalid domain format")
        
        # Check for suspicious domains
        suspicious_tlds = ['.tk', '.ml', '.ga', '.cf']
        if any(domain.endswith(tld) for tld in suspicious_tlds):
            raise ValidationError("Domain not allowed")
        
        return domain
    
    @classmethod
    def validate_url(cls, url: str) -> Optional[str]:
        """Validate URL format"""
        if not url:
            return None
        
        if not isinstance(url, str):
            return None
        
        url = url.strip()
        
        # Must be HTTP/HTTPS
        if not re.match(r'^https?://', url):
            return None
        
        # Length check
        if len(url) > 2000:
            return None
        
        # No suspicious patterns
        suspicious_patterns = ['javascript:', 'data:', 'vbscript:', 'file:']
        if any(pattern in url.lower() for pattern in suspicious_patterns):
            return None
        
        return url


class SessionValidator:
    """Session-related validation"""
    
    @classmethod
    def validate_session_id(cls, session_id: str) -> str:
        """Validate session ID format"""
        if not session_id or not isinstance(session_id, str):
            raise ValidationError("Session ID is required")
        
        session_id = session_id.strip()
        
        # Session ID should be URL-safe base64
        if not re.match(r'^[A-Za-z0-9_-]+$', session_id):
            raise ValidationError("Invalid session ID format")
        
        # Length check (should be consistent with our generation)
        if len(session_id) < 20 or len(session_id) > 50:
            raise ValidationError("Invalid session ID length")
        
        return session_id
    
    @classmethod
    def validate_user_agent(cls, user_agent: Optional[str]) -> Optional[str]:
        """Validate and sanitize user agent"""
        if not user_agent:
            return None
        
        if not isinstance(user_agent, str):
            return None
        
        user_agent = user_agent.strip()
        
        # Length check
        if len(user_agent) > 500:
            user_agent = user_agent[:500]
        
        # Remove potentially harmful characters
        user_agent = re.sub(r'[<>"\'\x00-\x1f]', '', user_agent)
        
        return user_agent if user_agent else None
    
    @classmethod
    def validate_ip_address(cls, ip_address: str) -> str:
        """Validate IP address format"""
        if not ip_address or not isinstance(ip_address, str):
            raise ValidationError("IP address is required")
        
        ip_address = ip_address.strip()
        
        # IPv4 pattern
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        
        # IPv6 pattern (simplified)
        ipv6_pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|^::1$|^::(ffff:)?(\d{1,3}\.){3}\d{1,3}$'
        
        if re.match(ipv4_pattern, ip_address):
            # Validate IPv4 octets
            octets = ip_address.split('.')
            for octet in octets:
                if not (0 <= int(octet) <= 255):
                    raise ValidationError("Invalid IP address")
            return ip_address
        elif re.match(ipv6_pattern, ip_address):
            return ip_address
        else:
            raise ValidationError("Invalid IP address format")


class InputValidator:
    """Combined input validation class"""
    
    @classmethod
    def validate_chat_message(
        cls,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[str, Optional[Dict[str, Any]]]:
        """Validate chat message input"""
        validated_content = MessageValidator.validate_message_content(content)
        validated_context = MessageValidator.validate_context(context)
        
        return validated_content, validated_context
    
    @classmethod
    def validate_session_creation(
        cls,
        domain: str,
        page_url: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: str = "unknown"
    ) -> Dict[str, Any]:
        """Validate session creation input"""
        validated_domain = DomainValidator.validate_domain(domain)
        validated_url = DomainValidator.validate_url(page_url)
        validated_user_agent = SessionValidator.validate_user_agent(user_agent)
        
        # Validate IP if not unknown
        if ip_address != "unknown":
            validated_ip = SessionValidator.validate_ip_address(ip_address)
        else:
            validated_ip = ip_address
        
        return {
            'domain': validated_domain,
            'page_url': validated_url,
            'user_agent': validated_user_agent,
            'ip_address': validated_ip
        }