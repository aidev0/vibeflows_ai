from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
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

class UserQuery(BaseModel):
    chatId: str
    text: str
    sender_id: str

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
    
    The response will be a MongoDB message document with the following fields:
    - id: Unique message ID (format: "sender-timestamp")
    - chatId: Chat identifier
    - text: Message content
    - mermaid: Optional mermaid diagram
    - sender: Message sender ("ai" or "user")
    - timestamp: ISO format timestamp in PST timezone
    - type: Message type ("user_understanding_json", "mermaid", or "simple_text")
    - json: Optional additional JSON data
    """
    try:
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
    
    The endpoint streams Server-Sent Events (SSE) containing MongoDB message documents.
    Each message will have the following structure:
    
    ```json
    {
        "id": "ai-1234567890",
        "chatId": "chat123",
        "text": "Message content",
        "mermaid": null,
        "sender": "ai",
        "timestamp": "2024-03-21T10:30:00-08:00",
        "type": "simple_text",
        "json": null
    }
    ```
    
    Message types:
    - user_understanding_json: Contains analysis of user's request
    - mermaid: Contains workflow diagram
    - simple_text: Regular text response
    
    Args:
        user_query: UserQuery object containing chatId, text, and sender_id
        
    Returns:
        StreamingResponse: Server-Sent Events stream of AI responses
    """
    return StreamingResponse(
        stream_flow_responses(user_query.dict()),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "message": "VibeFlows AI API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
