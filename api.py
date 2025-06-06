from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Any
from flows.user_interface_orchestrator import run_flow

app = FastAPI(
    title="VibeFlows AI API",
    description="API for running VibeFlows AI workflow",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Changed to False since we're using wildcard origins
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class UserQuery(BaseModel):
    chatId: str
    text: str

@app.post("/api/message")
async def process_message(user_query: UserQuery):
    """
    Process a user message and run it through the VibeFlows workflow.
    """
    try:
        print(f"Received message request: {user_query.dict()}")
        # Run the workflow and get responses
        responses = await run_flow(user_query.dict())
        print(f"Got responses from workflow: {responses}")
        
        if not responses:
            return JSONResponse(
                status_code=200,
                content={"error": "No responses from workflow"}
            )
            
        return JSONResponse(content=responses)
    except Exception as e:
        print(f"Error processing message: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "message": "VibeFlows AI API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)