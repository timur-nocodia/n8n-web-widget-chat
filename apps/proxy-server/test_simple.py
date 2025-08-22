#!/usr/bin/env python3

import sys
import os
sys.path.append('src')

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Chat Proxy Test")

@app.get("/")
async def root():
    return {"message": "Chat Proxy Test Server"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "version": "test",
        "message": "Basic server is working!"
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting test server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")