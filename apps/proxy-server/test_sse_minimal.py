#!/usr/bin/env python3
"""
Minimal SSE test server to isolate buffering issues.
Sends one character per second with explicit flushing.
"""

from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import uvicorn
from datetime import datetime

app = FastAPI()

# Add CORS middleware to allow file:// origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins including file://
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def character_generator():
    """Generate one character per second with timing info"""
    test_message = "Hello World! This is a test of character-by-character streaming."
    
    print(f"[{datetime.now().isoformat()}] Starting character stream")
    
    for i, char in enumerate(test_message):
        timestamp = datetime.now().isoformat()
        
        # Send character with timestamp
        chunk = f"data: {char}\n\n"
        
        print(f"[{timestamp}] Sending char #{i}: '{char}' (ASCII: {ord(char)})")
        
        # Yield the chunk
        yield chunk.encode('utf-8')
        
        # Wait 1 second before next character
        await asyncio.sleep(1.0)
    
    # Send completion
    yield b"data: [DONE]\n\n"
    print(f"[{datetime.now().isoformat()}] Stream complete")

@app.get("/stream")
async def stream_test():
    """SSE endpoint that sends 1 character per second"""
    return StreamingResponse(
        character_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",  # Allow all origins
        }
    )

@app.get("/")
async def index():
    """Simple HTML page to test SSE"""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SSE Test</title>
    </head>
    <body>
        <h1>SSE Character Stream Test</h1>
        <div id="output" style="font-family: monospace; font-size: 20px; padding: 20px; border: 1px solid #ccc;"></div>
        <div id="log" style="margin-top: 20px; padding: 10px; background: #f0f0f0; height: 300px; overflow-y: auto;"></div>
        
        <script>
            const output = document.getElementById('output');
            const log = document.getElementById('log');
            
            function addLog(message) {
                const timestamp = new Date().toISOString();
                log.innerHTML += `[${timestamp}] ${message}<br>`;
                log.scrollTop = log.scrollHeight;
            }
            
            addLog('Starting SSE connection...');
            const eventSource = new EventSource('/stream');
            
            let charCount = 0;
            let startTime = Date.now();
            
            eventSource.onmessage = (event) => {
                const data = event.data;
                const elapsed = Date.now() - startTime;
                charCount++;
                
                if (data === '[DONE]') {
                    addLog(`Stream complete. Received ${charCount} chunks in ${elapsed}ms`);
                    eventSource.close();
                    return;
                }
                
                // Add character to output
                output.textContent += data;
                
                // Log timing
                addLog(`Chunk #${charCount}: "${data}" at ${elapsed}ms`);
            };
            
            eventSource.onerror = (error) => {
                addLog('Error: ' + JSON.stringify(error));
                eventSource.close();
            };
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    print("Starting minimal SSE test server on http://localhost:8002")
    print("Visit http://localhost:8002 to test character streaming")
    print("Or use: curl -N http://localhost:8002/stream")
    uvicorn.run(app, host="0.0.0.0", port=8002)