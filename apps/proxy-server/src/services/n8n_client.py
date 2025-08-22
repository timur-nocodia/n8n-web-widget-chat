import asyncio
import json
from typing import AsyncGenerator, Dict, Any, Optional
import httpx
from sse_starlette import EventSourceResponse
from core.config import settings
from core.exceptions import N8NConnectionError


class N8NClient:
    def __init__(self):
        self.webhook_url = settings.n8n_webhook_url
        self.api_key = settings.n8n_api_key
        self.timeout = 30.0

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for n8n requests"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "chat-proxy/1.0"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        return headers

    async def send_message(
        self,
        message: str,
        session_id: str,
        jwt_token: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """Send message to n8n and stream response"""
        payload = {
            "message": message,
            "session_id": session_id,
            "jwt_token": jwt_token,
            "timestamp": asyncio.get_event_loop().time(),
        }
        
        if context:
            payload["context"] = context

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    self.webhook_url,
                    json=payload,
                    headers=self._get_headers()
                ) as response:
                    if response.status_code != 200:
                        raise N8NConnectionError(f"N8N returned status {response.status_code}")
                    
                    async for line in response.aiter_lines():
                        if line.strip():
                            # Handle SSE format
                            if line.startswith("data: "):
                                data = line[6:]  # Remove "data: " prefix
                                if data.strip() and data != "[DONE]":
                                    yield data
                            elif line.startswith("{"):
                                # Direct JSON response
                                yield line
                                
        except httpx.RequestError as e:
            raise N8NConnectionError(f"Failed to connect to n8n: {str(e)}")
        except Exception as e:
            raise N8NConnectionError(f"N8N client error: {str(e)}")

    async def create_sse_response(
        self,
        message: str,
        session_id: str,
        jwt_token: str,
        context: Optional[Dict[str, Any]] = None
    ) -> EventSourceResponse:
        """Create SSE response for streaming"""
        
        async def event_stream():
            try:
                async for data in self.send_message(message, session_id, jwt_token, context):
                    yield {
                        "event": "message",
                        "data": data
                    }
                    
                # Send completion event
                yield {
                    "event": "complete",
                    "data": json.dumps({"status": "completed"})
                }
                    
            except Exception as e:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": str(e)})
                }

        return EventSourceResponse(event_stream())


n8n_client = N8NClient()