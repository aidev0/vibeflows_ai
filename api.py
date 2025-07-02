from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Query, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, Any, List, Union
import json
from datetime import datetime, timedelta
from bson import ObjectId
import asyncio
import traceback
from pymongo import MongoClient
import os
import uuid

# Database connection
client = MongoClient(os.getenv('MONGODB_URI'))
db = client.vibeflows

app = FastAPI(
    title="VibeFlows AI API",
    description="API for running VibeFlows AI workflow",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://vibeflows.app",
        "https://vibeflows-c28a3602302a.herokuapp.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class AIRequest(BaseModel):
    user_query: Optional[str] = ""
    chat_id: Optional[str] = None
    user_id: Optional[str] = None

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "message": "VibeFlows AI API is running"}

@app.post("/api/ai/stream")
async def process_ai_request_stream(request: AIRequest):
    """Process AI request with Claude 4 streaming - truly non-blocking with real-time streaming"""
    
    # Validate and set defaults for optional fields
    user_query = request.user_query or ""
    chat_id = request.chat_id or str(uuid.uuid4())
    user_id = request.user_id or "anonymous"
    
    # Create queue for real-time communication
    stream_queue = asyncio.Queue()
    
    async def claude_background_task():
        """Run Claude agent in background and feed queue"""
        try:
            from user_interface_claude4 import run_claude_agent_flow
            
            async for message in run_claude_agent_flow(user_query, chat_id, user_id):
                await stream_queue.put(message)
                
        except Exception as e:
            error_msg = f"data: {json.dumps({'type': 'error', 'message': f'❌ Claude agent error: {str(e)}', 'final': True})}\n\n"
            await stream_queue.put(error_msg)
        finally:
            # Signal completion
            await stream_queue.put(None)
    
    async def generate_stream():
        """Stream messages from queue in real-time"""
        # Start Claude agent in background (non-blocking)
        background_task = asyncio.create_task(claude_background_task())
        
        try:
            while True:
                # Get next message from queue (non-blocking)
                try:
                    message = await asyncio.wait_for(stream_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    # Send keepalive to prevent connection timeout
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
                    continue
                
                # None signals completion
                if message is None:
                    break
                    
                # Stream the message immediately
                yield message
                await asyncio.sleep(0.01)  # Small delay to prevent overwhelming
                
        except asyncio.CancelledError:
            print("🔌 Client disconnected")
            background_task.cancel()
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Stream error: {str(e)}', 'final': True})}\n\n"
        finally:
            # Cleanup background task
            if not background_task.done():
                background_task.cancel()
                try:
                    await background_task
                except asyncio.CancelledError:
                    pass
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)