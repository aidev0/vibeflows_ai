from fastapi import FastAPI, HTTPException
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
        "http://localhost:3000",
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

@app.post("/api/message")
async def process_message(user_query: UserQuery):
    """Process a user message and run it through the VibeFlows workflow."""
    
    print(f"🔥 === API CALL START ===")
    print(f"📨 Received: {user_query.dict()}")
    
    try:
        # Add timeout to workflow execution
        print(f"⏱️ Starting workflow with 300s timeout...")
        responses = await asyncio.wait_for(
            run_flow(user_query.dict()), 
            timeout=300.0  # 5 minutes
        )
        
        print(f"✅ Workflow completed, got {len(responses) if responses else 0} responses")
        
        if not responses:
            print(f"⚠️ No responses from workflow")
            return JSONResponse(
                status_code=200,
                content={"error": "No responses from workflow", "success": False}
            )
        
        # Clean and test serialization
        print(f"🧹 Cleaning responses for serialization...")
        clean_responses = make_json_serializable(responses)
        
        # Test serialization
        try:
            serialized = json.dumps(clean_responses)
            print(f"✅ Serialization test passed, response size: {len(serialized)} chars")
        except Exception as e:
            print(f"❌ Serialization test failed: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Response serialization failed", 
                    "details": str(e),
                    "success": False
                }
            )
        
        print(f"📤 Sending response with {len(clean_responses)} items")
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": clean_responses,
                "count": len(clean_responses)
            }
        )
        
    except asyncio.TimeoutError:
        print(f"⏰ Workflow timed out after 300 seconds")
        return JSONResponse(
            status_code=408,
            content={
                "error": "Workflow execution timed out after 5 minutes", 
                "success": False,
                "timeout": True
            }
        )
    except Exception as e:
        print(f"❌ Error in API: {str(e)}")
        print(f"📚 Full traceback:")
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