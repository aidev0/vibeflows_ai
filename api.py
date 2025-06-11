from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Any
import json
from datetime import datetime
from bson import ObjectId
import asyncio
import traceback
from flows.user_interface_orchestrator import run_flow

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

class UserQuery(BaseModel):
    chatId: str
    text: str
    user_id: str

def make_json_serializable(obj):
    """Recursively convert MongoDB/BSON objects to JSON-serializable format"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: make_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return [make_json_serializable(item) for item in obj]
    else:
        return obj

async def run_workflow_background(user_query: dict):
    """Run the workflow in the background"""
    try:
        print(f"🚀 Starting background workflow for chat: {user_query.get('chatId')}")
        responses = await run_flow(user_query)
        print(f"✅ Background workflow completed successfully with {len(responses) if responses else 0} responses")
    except Exception as e:
        print(f"❌ Background workflow failed: {str(e)}")
        traceback.print_exc()

@app.post("/api/message")
async def process_message(user_query: UserQuery, background_tasks: BackgroundTasks):
    """Process a user message and run it through the VibeFlows workflow."""
    
    print(f"🔥 === API CALL START ===")
    print(f"📨 Received: {user_query.dict()}")
    
    try:
        # Import the save_message function
        from flows.user_interface_orchestrator import save_message
        
        # Save the processing message to database immediately
        processing_doc = save_message(
            user_query.chatId,
            "🚀 Your workflow request is under process! This will take 2-3 minutes. We will refresh the page to show you our udnerstanding, a workflow design, and a n8n configuration once it's ready.",
            "ai",
            "simple_text"
        )
        
        # Start the workflow in the background
        background_tasks.add_task(run_workflow_background, user_query.dict())
        
        # Return the saved message document
        print(f"📤 Sending immediate response - workflow running in background")
        if processing_doc:
            return JSONResponse(
                status_code=200,
                content=processing_doc
            )
        else:
            # Fallback if save failed
            processing_message = {
                "id": f"ai-{int(datetime.now().timestamp() * 1000)}",
                "chatId": user_query.chatId,
                "text": "🚀 Your workflow is being processed! Please refresh the page in 2-3 minutes.",
                "sender": "ai",
                "timestamp": datetime.now().isoformat(),
                "type": "simple_text"
            }
            return JSONResponse(
                status_code=200,
                content=processing_message
            )
        
    except Exception as e:
        print(f"❌ Error starting workflow: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e), 
                "success": False,
                "type": type(e).__name__
            }
        )

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "message": "VibeFlows AI API is running"}

@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "service": "VibeFlows AI API"
    }

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)