from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any, AsyncGenerator
import asyncio
import json
from flows.user_interface_orchestrator import run_flow

app = FastAPI(
    title="VibeFlows AI API",
    description="API for running VibeFlows AI workflow",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Add error handling middleware
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"type": "error", "text": str(e)}
        )

class UserQuery(BaseModel):
    chatId: str
    text: str

class MessageResponse(BaseModel):
    """Response message format that will be streamed to the client."""
    id: str  # Unique message ID in format "sender-timestamp"
    chatId: str  # Chat ID
    text: str  # Message text content
    mermaid: Optional[str] = None  # Mermaid diagram if present
    sender: str  # Message sender ("ai" or "user")
    timestamp: str  # ISO format timestamp in PST timezone
    type: str  # Message type: "user_understanding_json", "mermaid", or "simple_text"
    json: Optional[dict] = None  # Additional JSON data if present

async def stream_flow_responses(user_query: dict) -> AsyncGenerator[str, None]:
    """
    Stream responses from the flow as they are generated.
    
    Each response will be a Server-Sent Event (SSE) with the following format:
    data: {"id": "ai-1234567890", "chatId": "chat123", "text": "Message text", ...}
    """
    try:
        # Validate required fields
        if not user_query.get("chatId"):
            yield f"data: {json.dumps({'type': 'error', 'text': 'chatId is required'})}\n\n"
            return
        if not user_query.get("text"):
            yield f"data: {json.dumps({'type': 'error', 'text': 'text is required'})}\n\n"
            return

        # Convert to dict and run the workflow
        async for response in run_flow(user_query):
            # Format the SSE message
            yield f"data: {json.dumps(response)}\n\n"
            # Add a small delay to prevent overwhelming the client
            await asyncio.sleep(0.1)
    except Exception as e:
        error_response = {
            "type": "error",
            "text": str(e)
        }
        yield f"data: {json.dumps(error_response)}\n\n"

@app.post("/api/message")
async def process_message(user_query: UserQuery):
    """
    Process a user message and stream responses from the VibeFlows workflow.
    """
    try:
        return StreamingResponse(
            stream_flow_responses(user_query.dict()),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"type": "error", "text": str(e)}
        )

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "message": "VibeFlows AI API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
