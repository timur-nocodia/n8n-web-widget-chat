import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Dict, Any, Optional, Set
from dataclasses import dataclass
from fastapi import HTTPException, status
from sse_starlette import EventSourceResponse
import httpx
from core.config import settings
from core.exceptions import N8NConnectionError

logger = logging.getLogger(__name__)


@dataclass
class SSEConnection:
    """Represents an active SSE connection"""
    session_id: str
    client_ip: str
    created_at: float
    last_activity: float
    is_active: bool = True


class SSEConnectionManager:
    """Manage SSE connections with optimization and monitoring"""
    
    def __init__(self):
        self.active_connections: Dict[str, SSEConnection] = {}
        self.connection_queues: Dict[str, asyncio.Queue] = {}
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        self.max_connections = 10000
        self.heartbeat_interval = 30  # seconds
        self.connection_timeout = 300  # 5 minutes
        
        # Start background tasks
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background tasks for connection management"""
        if not self.heartbeat_task:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        if not self.cleanup_task:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def create_connection(self, session_id: str, client_ip: str) -> str:
        """Create a new SSE connection"""
        connection_id = f"{session_id}:{int(time.time())}"
        
        # Check connection limits
        if len(self.active_connections) >= self.max_connections:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Too many active connections"
            )
        
        # Create connection
        connection = SSEConnection(
            session_id=session_id,
            client_ip=client_ip,
            created_at=time.time(),
            last_activity=time.time()
        )
        
        self.active_connections[connection_id] = connection
        self.connection_queues[connection_id] = asyncio.Queue()
        
        logger.info(f"Created SSE connection {connection_id} for session {session_id}")
        return connection_id
    
    async def close_connection(self, connection_id: str):
        """Close an SSE connection"""
        if connection_id in self.active_connections:
            self.active_connections[connection_id].is_active = False
            
            # Clean up queue
            if connection_id in self.connection_queues:
                del self.connection_queues[connection_id]
            
            del self.active_connections[connection_id]
            logger.info(f"Closed SSE connection {connection_id}")
    
    async def send_message(self, connection_id: str, message: Dict[str, Any]):
        """Send message to specific connection"""
        if connection_id in self.connection_queues:
            await self.connection_queues[connection_id].put(message)
            
            # Update last activity
            if connection_id in self.active_connections:
                self.active_connections[connection_id].last_activity = time.time()
    
    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        """Broadcast message to all connections for a session"""
        for connection_id, connection in self.active_connections.items():
            if connection.session_id == session_id and connection.is_active:
                await self.send_message(connection_id, message)
    
    async def get_connection_stream(self, connection_id: str) -> AsyncGenerator[str, None]:
        """Get message stream for a connection"""
        try:
            queue = self.connection_queues.get(connection_id)
            if not queue:
                return
            
            # Send initial connection confirmation
            yield self._format_sse_message("connected", {"status": "connected"})
            
            while True:
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(queue.get(), timeout=self.heartbeat_interval)
                    
                    if message is None:  # Connection close signal
                        break
                    
                    yield self._format_sse_message(message["event"], message["data"])
                    
                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield self._format_sse_message("heartbeat", {"timestamp": time.time()})
                    
                except Exception as e:
                    logger.error(f"Error in SSE stream {connection_id}: {e}")
                    break
        
        finally:
            await self.close_connection(connection_id)
    
    def _format_sse_message(self, event: str, data: Any) -> str:
        """Format message for SSE protocol"""
        if isinstance(data, dict):
            data = json.dumps(data)
        
        return f"event: {event}\ndata: {data}\n\n"
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to maintain connections"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                current_time = time.time()
                heartbeat_message = {"event": "heartbeat", "data": {"timestamp": current_time}}
                
                # Send heartbeat to all active connections
                for connection_id in list(self.connection_queues.keys()):
                    try:
                        await self.send_message(connection_id, heartbeat_message)
                    except Exception as e:
                        logger.error(f"Failed to send heartbeat to {connection_id}: {e}")
                
                logger.debug(f"Sent heartbeat to {len(self.active_connections)} connections")
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    async def _cleanup_loop(self):
        """Clean up inactive connections"""
        while True:
            try:
                await asyncio.sleep(60)  # Run cleanup every minute
                
                current_time = time.time()
                inactive_connections = []
                
                for connection_id, connection in self.active_connections.items():
                    if (current_time - connection.last_activity) > self.connection_timeout:
                        inactive_connections.append(connection_id)
                
                for connection_id in inactive_connections:
                    await self.close_connection(connection_id)
                
                if inactive_connections:
                    logger.info(f"Cleaned up {len(inactive_connections)} inactive connections")
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        current_time = time.time()
        
        stats = {
            "total_connections": len(self.active_connections),
            "active_connections": len([c for c in self.active_connections.values() if c.is_active]),
            "sessions": len(set(c.session_id for c in self.active_connections.values())),
            "oldest_connection": 0,
            "connections_by_ip": {}
        }
        
        if self.active_connections:
            oldest = min(c.created_at for c in self.active_connections.values())
            stats["oldest_connection"] = current_time - oldest
        
        # Count connections by IP
        for connection in self.active_connections.values():
            ip = connection.client_ip
            if ip not in stats["connections_by_ip"]:
                stats["connections_by_ip"][ip] = 0
            stats["connections_by_ip"][ip] += 1
        
        return stats


class OptimizedN8NClient:
    """Optimized n8n client with connection pooling and retry logic"""
    
    def __init__(self):
        self.webhook_url = settings.n8n_webhook_url
        self.api_key = settings.n8n_api_key
        self.timeout = httpx.Timeout(30.0, connect=5.0)
        self.limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
        self.retry_attempts = 3
        self.retry_delay = 1.0
        
        # Create persistent HTTP client
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=self.limits,
                headers=self._get_headers()
            )
        return self._client
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for n8n requests"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "chat-proxy/1.0",
            "Accept": "text/event-stream"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        return headers
    
    async def send_message_with_retry(
        self,
        message: str,
        session_id: str,
        jwt_token: str,
        context: Optional[Dict[str, Any]] = None,
        connection_manager: Optional[SSEConnectionManager] = None,
        connection_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Send message to n8n with retry logic and optimized streaming"""
        
        payload = {
            "message": message,
            "session_id": session_id,
            "jwt_token": jwt_token,
            "timestamp": time.time(),
        }
        
        if context:
            payload["context"] = context
        
        last_exception = None
        
        for attempt in range(self.retry_attempts):
            try:
                async for response_data in self._stream_request(payload, attempt):
                    # Send to connection manager if provided
                    if connection_manager and connection_id:
                        await connection_manager.send_message(connection_id, response_data)
                    
                    yield response_data
                
                return  # Success, exit retry loop
                
            except Exception as e:
                last_exception = e
                logger.warning(f"N8N request attempt {attempt + 1} failed: {e}")
                
                if attempt < self.retry_attempts - 1:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    
                    # Send retry notification
                    retry_message = {
                        "event": "retry",
                        "data": {
                            "attempt": attempt + 1,
                            "max_attempts": self.retry_attempts,
                            "delay": delay
                        }
                    }
                    
                    if connection_manager and connection_id:
                        await connection_manager.send_message(connection_id, retry_message)
                    
                    yield retry_message
        
        # All retries failed
        error_message = {
            "event": "error",
            "data": {
                "error": "N8N service unavailable",
                "detail": str(last_exception),
                "retry_attempts": self.retry_attempts
            }
        }
        
        if connection_manager and connection_id:
            await connection_manager.send_message(connection_id, error_message)
        
        yield error_message
        raise N8NConnectionError(f"Failed after {self.retry_attempts} attempts: {last_exception}")
    
    async def _stream_request(self, payload: Dict[str, Any], attempt: int) -> AsyncGenerator[Dict[str, Any], None]:
        """Make streaming request to n8n"""
        client = await self._get_client()
        
        try:
            async with client.stream("POST", self.webhook_url, json=payload) as response:
                if response.status_code != 200:
                    raise N8NConnectionError(f"N8N returned status {response.status_code}")
                
                buffer = ""
                
                async for chunk in response.aiter_bytes():
                    if not chunk:
                        continue
                    
                    buffer += chunk.decode('utf-8')
                    
                    # Process complete SSE messages
                    while '\n\n' in buffer:
                        message, buffer = buffer.split('\n\n', 1)
                        
                        if message.strip():
                            parsed_message = self._parse_sse_message(message)
                            if parsed_message:
                                yield parsed_message
                
                # Process any remaining buffer
                if buffer.strip():
                    parsed_message = self._parse_sse_message(buffer)
                    if parsed_message:
                        yield parsed_message
                        
        except httpx.RequestError as e:
            raise N8NConnectionError(f"Request failed: {str(e)}")
    
    def _parse_sse_message(self, message: str) -> Optional[Dict[str, Any]]:
        """Parse SSE message format"""
        try:
            lines = message.strip().split('\n')
            event = "message"
            data = ""
            
            for line in lines:
                if line.startswith('event: '):
                    event = line[7:]
                elif line.startswith('data: '):
                    data = line[6:]
            
            if data:
                return {
                    "event": event,
                    "data": json.loads(data) if data.startswith('{') else data
                }
            
        except Exception as e:
            logger.error(f"Failed to parse SSE message: {e}")
        
        return None
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None


# Global instances
sse_manager = SSEConnectionManager()
optimized_n8n_client = OptimizedN8NClient()