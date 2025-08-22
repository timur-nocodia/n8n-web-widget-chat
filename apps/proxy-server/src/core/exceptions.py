class ChatProxyException(Exception):
    """Base exception for chat proxy"""
    pass


class SessionNotFoundError(ChatProxyException):
    """Session not found"""
    pass


class InvalidSessionError(ChatProxyException):
    """Invalid session"""
    pass


class RateLimitExceededError(ChatProxyException):
    """Rate limit exceeded"""
    pass


class N8NConnectionError(ChatProxyException):
    """N8N connection error"""
    pass


class InvalidOriginError(ChatProxyException):
    """Invalid origin"""
    pass


class ValidationError(ChatProxyException):
    """Validation error"""
    pass