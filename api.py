from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
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

@app.post("/api/message")
async def process_message(user_query: UserQuery):
    """
    Process a user message and run it through the VibeFlows workflow.
    
    Args:
        user_query: UserQuery object containing chatId, text, and sender_id
        
    Returns:
        dict: Response containing the AI's response
    """
    try:
        # Convert to dict and run the workflow
        response = run_flow(user_query.dict())
        
        return {
            "status": "success",
            "response": response
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing message: {str(e)}"
        )

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "message": "VibeFlows AI API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
