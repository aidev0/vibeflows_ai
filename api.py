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
from flows.user_interface_orchestrator import run_flow
from pymongo import MongoClient
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
import threading

# Import user interface
from user_interface import process_user_message

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
        "https://vibeflows-c28a3602302a.herokuapp.com",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserQuery(BaseModel):
    chatId: str
    text: str
    user_id: str

class FlowCreateRequest(BaseModel):
    requirements: str
    user_id: Optional[str] = None

class FlowRunRequest(BaseModel):
    flow_id: str
    input_data: Optional[dict] = {}
    user_id: Optional[str] = None

class AgentRunRequest(BaseModel):
    agent_id: str
    input_data: Optional[dict] = {}

class AIRequest(BaseModel):
    user_query: Optional[str] = ""
    chat_id: Optional[str] = None
    user_id: Optional[str] = None

class ChatCreateRequest(BaseModel):
    user_id: str
    title: Optional[str] = None

class MessageCreateRequest(BaseModel):
    chat_id: Optional[str] = None
    role: Optional[str] = "user"  # "user" or "assistant" or "system"
    type: Optional[str] = "text"  # "text", "image", "file", etc.
    text: Optional[str] = ""
    content: Optional[Union[dict, str]] = {}  # JSON object or text string
    user_id: Optional[str] = None

class SessionCreateRequest(BaseModel):
    user_id: str

# Thread pool for CPU-intensive tasks
thread_pool = ThreadPoolExecutor(max_workers=3)

async def run_in_thread(func, *args, **kwargs):
    """Run a potentially blocking function in a thread pool"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(thread_pool, func, *args, **kwargs)

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

async def process_ai_request_background(job_id: str, user_query: str, chat_id: str, user_id: str):
    """Process AI request in the background and update job status"""
    try:
        print(f"🚀 Starting background AI processing for job {job_id}")
        
        # Update job status to processing
        db.jobs.update_one(
            {'_id': job_id},
            {
                '$set': {
                    'status': 'processing',
                    'updated_at': datetime.now()
                },
                '$push': {
                    'steps': {
                        'step': 'started',
                        'message': 'Background processing started',
                        'timestamp': datetime.now()
                    }
                }
            }
        )
        
        # Process through user interface
        result = await process_user_message(
            user_query=user_query,
            chat_id=chat_id,
            user_id=user_id
        )
        
        # Update job with successful result
        db.jobs.update_one(
            {'_id': job_id},
            {
                '$set': {
                    'status': 'completed',
                    'result': make_json_serializable(result),
                    'updated_at': datetime.now()
                },
                '$push': {
                    'steps': {
                        'step': 'completed',
                        'message': 'Processing completed successfully',
                        'timestamp': datetime.now()
                    }
                }
            }
        )
        
        print(f"✅ Background job {job_id} completed successfully")
        
    except Exception as e:
        # Update job with error
        error_message = str(e)
        print(f"❌ Background job {job_id} failed: {error_message}")
        
        db.jobs.update_one(
            {'_id': job_id},
            {
                '$set': {
                    'status': 'failed',
                    'error': error_message,
                    'updated_at': datetime.now()
                },
                '$push': {
                    'steps': {
                        'step': 'failed',
                        'message': f'Processing failed: {error_message}',
                        'timestamp': datetime.now()
                    }
                }
            }
        )
        traceback.print_exc()

@app.post("/api/message")
async def process_message(user_query: UserQuery):
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
        
        # Start the workflow in a detached background task (non-blocking)
        asyncio.create_task(run_workflow_background(user_query.dict()))
        
        # Return the saved message document immediately
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
                "role": "assistant",
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
    """Health check endpoint"""
    try:
        # Test database connection
        db.command('ping')
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

@app.get("/api/flows")
async def get_flows(user_id: Optional[str] = Query(None, description="Filter flows by user_id")):
    """Get flows, optionally filtered by user_id."""
    
    try:
        # Build query
        query = {}
        if user_id:
            query["user_id"] = user_id
        
        # Get flows from database
        flows = list(db.flows.find(query).sort("created_at", -1).limit(100))
        
        # Make JSON serializable and return directly
        return make_json_serializable(flows)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents")
async def get_agents(user_id: Optional[str] = Query(None, description="Filter agents by user_id")):
    """Get agents, optionally filtered by user_id."""
    
    try:
        # Build query
        query = {}
        if user_id:
            query["user_id"] = user_id
        
        # Get agents from database
        agents = list(db.agents.find(query).sort("created_at", -1).limit(100))
        
        # Make JSON serializable and return directly
        return make_json_serializable(agents)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/create/flow")
async def create_flow(request: FlowCreateRequest):
    """Create a complete flow: flow_designer -> flow_developer -> n8n_developer"""
    
    try:
        # Import the required functions
        from flow_designer import flow_designer
        from flow_developer import flow_developer
        from n8n_developer import n8n_developer
        
        result = {
            'flow_id': None,
            'n8n_workflow': None,
            'agents_created': [],
            'status': 'in_progress'
        }
        
        # Step 1: Flow Designer - Create workflow architecture
        design_result = flow_designer({'requirements': request.requirements})
        result['flow_id'] = design_result.get('_id')
        result['design_result'] = design_result
        
        # Step 2: Flow Developer - Create agents for nodes
        if result['flow_id']:
            developer_input = {
                'flow_id': result['flow_id']
            }
            developer_result = flow_developer(developer_input)
            result['agents_created'] = developer_result.get('agents_created', [])
            result['developer_result'] = developer_result
        
        # Step 3: N8N Developer - Create and deploy n8n workflow
        n8n_input = {
            'requirements': request.requirements,
            'user_id': request.user_id
        }
        n8n_result = n8n_developer(n8n_input)
        result['n8n_workflow'] = n8n_result.get('workflow_json')
        result['n8n_status'] = n8n_result.get('status')
        result['n8n_message'] = n8n_result.get('message')
        result['n8n_result'] = n8n_result
        
        # Extract N8N URL and workflow ID if published successfully
        if n8n_result.get('status') == 'published' and request.user_id:
            n8n_response = n8n_result.get('n8n_response', {})
            workflow_id = n8n_response.get('id')
            
            if workflow_id:
                # Get N8N_URL from user credentials
                n8n_url_cred = db.credentials.find_one({'user_id': request.user_id, 'name': 'N8N_URL'})
                if n8n_url_cred:
                    n8n_base_url = n8n_url_cred.get('value', '').rstrip('/')
                    workflow_url = f"{n8n_base_url}/workflow/{workflow_id}"
                    result['n8n_workflow_url'] = workflow_url
        
        # Final status
        result['status'] = 'created'
        
        # Return the complete result
        return make_json_serializable(result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/run/flow")
async def run_flow(request: FlowRunRequest):
    """Run an existing flow by flow_id"""
    
    try:
        # Import the flow_runner function
        from flow_runner import flow_runner
        
        # Prepare input for flow_runner
        runner_input = {
            'flow_id': request.flow_id,
            'input_data': request.input_data or {},
            'user_id': request.user_id
        }
        
        # Execute the flow
        result = flow_runner(runner_input)
        
        # Return the raw result
        return make_json_serializable(result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/run/agent")
async def run_agent_endpoint(request: AgentRunRequest):
    """Run an existing agent by agent_id"""
    
    try:
        # Import the agent runner function
        from agent_runner import run_agent
        
        # Execute the agent
        result = run_agent(request.agent_id, request.input_data or {})
        
        # Return the raw result
        return make_json_serializable(result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/create/flow/stream")
async def create_flow_stream(request: FlowCreateRequest):
    """Create a complete flow with streaming partial responses (SSE)"""
    
    async def generate_stream():
        try:
            # Import the required functions
            from flow_designer import flow_designer
            from flow_developer import flow_developer
            from n8n_developer import n8n_developer
            
            result = {
                'flow_id': None,
                'n8n_workflow': None,
                'agents_created': [],
                'status': 'in_progress'
            }
            
            # Step 1: Flow Designer
            yield f"data: {json.dumps({'step': 1, 'status': 'starting', 'message': 'Creating workflow architecture...'})}\n\n"
            
            design_result = flow_designer({'requirements': request.requirements})
            result['flow_id'] = design_result.get('_id')
            result['design_result'] = design_result
            
            yield f"data: {json.dumps({'step': 1, 'status': 'completed', 'result': make_json_serializable(design_result)})}\n\n"
            
            # Step 2: Flow Developer
            if result['flow_id']:
                yield f"data: {json.dumps({'step': 2, 'status': 'starting', 'message': 'Creating agents for workflow nodes...'})}\n\n"
                
                developer_input = {'flow_id': result['flow_id']}
                developer_result = flow_developer(developer_input)
                result['agents_created'] = developer_result.get('agents_created', [])
                result['developer_result'] = developer_result
                
                yield f"data: {json.dumps({'step': 2, 'status': 'completed', 'result': make_json_serializable(developer_result)})}\n\n"
            
            # Step 3: N8N Developer
            yield f"data: {json.dumps({'step': 3, 'status': 'starting', 'message': 'Generating and deploying n8n workflow...'})}\n\n"
            
            n8n_input = {
                'requirements': request.requirements,
                'user_id': request.user_id
            }
            n8n_result = n8n_developer(n8n_input)
            result['n8n_workflow'] = n8n_result.get('workflow_json')
            result['n8n_status'] = n8n_result.get('status')
            result['n8n_message'] = n8n_result.get('message')
            result['n8n_result'] = n8n_result
            
            # Extract N8N URL if published
            if n8n_result.get('status') == 'published' and request.user_id:
                n8n_response = n8n_result.get('n8n_response', {})
                workflow_id = n8n_response.get('id')
                
                if workflow_id:
                    n8n_url_cred = db.credentials.find_one({'user_id': request.user_id, 'name': 'N8N_URL'})
                    if n8n_url_cred:
                        n8n_base_url = n8n_url_cred.get('value', '').rstrip('/')
                        workflow_url = f"{n8n_base_url}/workflow/{workflow_id}"
            
            yield f"data: {json.dumps({'step': 3, 'status': 'completed', 'result': make_json_serializable(n8n_result)})}\n\n"
            
            # Final result
            result['status'] = 'created'
            yield f"data: {json.dumps({'step': 'final', 'status': 'completed', 'result': make_json_serializable(result)})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'step': 'error'})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@app.post("/api/ai/process")
async def process_ai_simple(request: AIRequest):
    """Simple AI processing with job tracking - returns immediately"""
    
    try:
        # Validate and set defaults
        user_query = request.user_query or ""
        chat_id = request.chat_id or str(uuid.uuid4())
        user_id = request.user_id or "anonymous"
        
        # Create job ID
        job_id = str(uuid.uuid4())
        
        # Create job in database
        job_doc = {
            '_id': job_id,
            'user_id': user_id,
            'chat_id': chat_id,
            'user_query': user_query,
            'status': 'processing',
            'progress': 0,
            'current_step': 'starting',
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'result': None,
            'error': None
        }
        
        db.jobs.insert_one(job_doc)
        
        # Process in background thread (truly non-blocking)
        def background_ai_process():
            try:
                print(f"🚀 Starting AI processing job: {job_id}")
                
                # Update progress: Analysis
                db.jobs.update_one({'_id': job_id}, {'$set': {'current_step': 'analyzing', 'progress': 10}})
                
                from user_interface import execute_query_analyzer
                analysis_result = execute_query_analyzer(user_query, chat_id, user_id)
                action_type = analysis_result.get('action_type', 'respond')
                
                # Update progress: Action
                db.jobs.update_one({'_id': job_id}, {'$set': {'current_step': f'executing_{action_type}', 'progress': 30}})
                
                action_result = {}
                if action_type == 'create_flow':
                    from user_interface import execute_flow_creator
                    action_result = execute_flow_creator(analysis_result, chat_id, user_id)
                elif action_type == 'run_flow':
                    from user_interface import execute_flow_runner
                    action_result = execute_flow_runner(analysis_result, chat_id, user_id)
                else:
                    action_result = {"routed_to": "response_generator", "analysis": analysis_result}
                
                # Update progress: Response
                db.jobs.update_one({'_id': job_id}, {'$set': {'current_step': 'generating_response', 'progress': 70}})
                
                from user_interface import execute_response_generator
                final_response = execute_response_generator(user_query, analysis_result, action_result, chat_id, user_id)
                response_text = final_response.get('response', 'Process completed')
                
                # Save messages
                from user_interface import save_message
                save_message(chat_id, user_query, "user", "text")
                save_message(chat_id, response_text, "assistant", "text")
                
                # Complete job
                db.jobs.update_one(
                    {'_id': job_id}, 
                    {
                        '$set': {
                            'status': 'completed',
                            'current_step': 'completed',
                            'progress': 100,
                            'result': {
                                'response': response_text,
                                'action_type': action_type,
                                'analysis': make_json_serializable(analysis_result),
                                'action_result': make_json_serializable(action_result)
                            },
                            'updated_at': datetime.now()
                        }
                    }
                )
                
                print(f"✅ AI job {job_id} completed")
                
            except Exception as e:
                error_msg = str(e)
                print(f"❌ AI job {job_id} failed: {error_msg}")
                traceback.print_exc()
                
                db.jobs.update_one(
                    {'_id': job_id},
                    {
                        '$set': {
                            'status': 'failed',
                            'current_step': 'failed',
                            'error': error_msg,
                            'updated_at': datetime.now()
                        }
                    }
                )
        
        # Run in thread pool to avoid blocking
        thread_pool.submit(background_ai_process)
        
        # Return immediately
        return JSONResponse(
            status_code=202,
            content={
                "success": True,
                "job_id": job_id,
                "status": "processing",
                "message": "AI processing started",
                "poll_url": f"/api/jobs/{job_id}",
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        print(f"❌ Error starting AI process: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "success": False}
        )

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of a background job"""
    try:
        job = db.jobs.find_one({'_id': job_id})
        
        if not job:
            return JSONResponse(
                status_code=404,
                content={"error": "Job not found", "job_id": job_id}
            )
        
        # Convert ObjectIds and datetime objects for JSON serialization
        job = make_json_serializable(job)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "job": job,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "job_id": job_id}
        )

@app.get("/api/jobs")
async def get_jobs(user_id: Optional[str] = Query(None), status: Optional[str] = Query(None), limit: int = Query(10, le=100)):
    """Get list of jobs, optionally filtered by user_id and status"""
    try:
        query_filter = {}
        if user_id:
            query_filter['user_id'] = user_id
        if status:
            query_filter['status'] = status
            
        jobs = list(
            db.jobs.find(query_filter)
            .sort('created_at', -1)
            .limit(limit)
        )
        
        # Convert ObjectIds and datetime objects for JSON serialization
        jobs = make_json_serializable(jobs)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "jobs": jobs,
                "count": len(jobs),
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/api/chats")
async def get_chats(user_id: Optional[str] = Query(None), limit: int = Query(50, le=100)):
    """Get list of chats, optionally filtered by user_id"""
    try:
        query_filter = {}
        if user_id:
            query_filter['user_id'] = user_id
            
        # Get unique chats from messages collection
        pipeline = [
            {"$match": query_filter if user_id else {}},
            {"$group": {
                "_id": "$chat_id",
                "user_id": {"$first": "$role"},  # Get first role as user_id approximation
                "last_message": {"$last": "$text"},
                "last_updated": {"$max": "$timestamp"},
                "message_count": {"$sum": 1},
                "created_at": {"$min": "$timestamp"}
            }},
            {"$sort": {"last_updated": -1}},
            {"$limit": limit}
        ]
        
        chats = list(db.messages.aggregate(pipeline))
        
        # Convert to more user-friendly format
        formatted_chats = []
        for chat in chats:
            formatted_chats.append({
                "chat_id": chat["_id"],
                "user_id": user_id if user_id else chat.get("user_id"),
                "title": f"Chat {chat['_id'][:8]}...",  # Default title
                "last_message": chat["last_message"],
                "last_updated": chat["last_updated"],
                "message_count": chat["message_count"],
                "created_at": chat["created_at"]
            })
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "chats": make_json_serializable(formatted_chats),
                "count": len(formatted_chats),
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/api/chats")
async def create_chat(request: ChatCreateRequest):
    """Create a new chat"""
    try:
        # Create chat document - MongoDB auto-generates _id
        chat_doc = {
            "user_id": request.user_id,
            "title": request.title or "New Chat",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "message_count": 0
        }
        
        result = db.chats.insert_one(chat_doc)
        chat_doc['_id'] = str(result.inserted_id)
        
        return JSONResponse(
            status_code=201,
            content=make_json_serializable(chat_doc)
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/api/chats/{chat_id}")
async def get_chat(chat_id: str):
    """Get specific chat details"""
    try:
        # Try to get from chats collection first using ObjectId
        try:
            chat_object_id = ObjectId(chat_id)
            chat = db.chats.find_one({"_id": chat_object_id})
        except:
            chat = None
        
        if not chat:
            # Fallback: get chat info from messages
            pipeline = [
                {"$match": {"chat_id": chat_id}},
                {"$group": {
                    "_id": "$chat_id",
                    "message_count": {"$sum": 1},
                    "created_at": {"$min": "$timestamp"},
                    "updated_at": {"$max": "$timestamp"},
                    "participants": {"$addToSet": "$role"}
                }}
            ]
            
            result = list(db.messages.aggregate(pipeline))
            if not result:
                return JSONResponse(
                    status_code=404,
                    content={"error": "Chat not found", "chat_id": chat_id}
                )
            
            chat_info = result[0]
            chat = {
                "chat_id": chat_id,
                "title": f"Chat {chat_id[:8]}",
                "message_count": chat_info["message_count"],
                "created_at": chat_info["created_at"],
                "updated_at": chat_info["updated_at"],
                "participants": chat_info["participants"]
            }
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "chat": make_json_serializable(chat),
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "chat_id": chat_id}
        )

@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str):
    """Delete a chat and all its messages"""
    try:
        # Delete all messages for this chat
        messages_result = db.messages.delete_many({"chat_id": chat_id})
        
        # Delete chat document if exists
        chat_result = db.chats.delete_one({"chat_id": chat_id})
        
        if messages_result.deleted_count == 0 and chat_result.deleted_count == 0:
            return JSONResponse(
                status_code=404,
                content={"error": "Chat not found", "chat_id": chat_id}
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "chat_id": chat_id,
                "messages_deleted": messages_result.deleted_count,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "chat_id": chat_id}
        )

@app.get("/api/messages")
async def get_messages(
    chat_id: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    message_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    skip: int = Query(0, ge=0)
):
    """Get messages with optional filters"""
    try:
        query_filter = {}
        if chat_id:
            query_filter['chat_id'] = chat_id
        if role:
            query_filter['role'] = role
        if message_type:
            query_filter['type'] = message_type
            
        messages = list(
            db.messages.find(query_filter)
            .sort('timestamp', 1)  # Chronological order
            .skip(skip)
            .limit(limit)
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "messages": make_json_serializable(messages),
                "count": len(messages),
                "has_more": len(messages) == limit,
                "next_skip": skip + limit if len(messages) == limit else None,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/api/messages")
async def create_message(request: MessageCreateRequest):
    """Create a new message"""
    try:
        message_doc = {
            'chat_id': request.chat_id,
            'role': request.role,
            'type': request.type,
            'text': request.text,
            'content': request.content,
            'user_id': request.user_id,
            'timestamp': datetime.now(),
            'created_at': datetime.now()
        }
        
        result = db.messages.insert_one(message_doc)
        message_doc['_id'] = str(result.inserted_id)
        
        # Update chat's last activity (if chat exists in chats collection)
        db.chats.update_one(
            {"chat_id": request.chat_id},
            {
                "$set": {
                    "updated_at": datetime.now(),
                    "user_id": request.user_id
                },
                "$inc": {"message_count": 1}
            }
        )
        
        return JSONResponse(
            status_code=201,
            content=make_json_serializable(message_doc)
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/api/chats/{chat_id}/messages")
async def get_chat_messages(
    chat_id: str,
    limit: int = Query(100, le=200),
    skip: int = Query(0, ge=0),
    order: str = Query("asc", regex="^(asc|desc)$")
):
    """Get messages for a specific chat"""
    try:
        sort_order = 1 if order == "asc" else -1
        
        messages = list(
            db.messages.find({"chat_id": chat_id})
            .sort('timestamp', sort_order)
            .skip(skip)
            .limit(limit)
        )
        
        if not messages and skip == 0:
            # Check if chat exists
            chat_exists = db.chats.find_one({"_id": ObjectId(chat_id)}) or db.messages.find_one({"chat_id": chat_id})
            if not chat_exists:
                return JSONResponse(
                    status_code=404,
                    content={"error": "Chat not found", "chat_id": chat_id}
                )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "chat_id": chat_id,
                "messages": make_json_serializable(messages),
                "count": len(messages),
                "has_more": len(messages) == limit,
                "next_skip": skip + limit if len(messages) == limit else None,
                "order": order,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "chat_id": chat_id}
        )

@app.post("/api/chats/{chat_id}/messages")
async def create_chat_message(chat_id: str, request: MessageCreateRequest):
    """Create a new message in a specific chat"""
    try:
        # Override chat_id with path parameter
        message_doc = {
            'chat_id': chat_id,
            'role': request.role,
            'type': request.type,
            'text': request.text,
            'content': request.content,
            'timestamp': datetime.now(),
            'created_at': datetime.now()
        }
        
        result = db.messages.insert_one(message_doc)
        message_doc['_id'] = str(result.inserted_id)
        
        # Update chat's last activity
        db.chats.update_one(
            {"chat_id": chat_id},
            {
                "$set": {
                    "updated_at": datetime.now(),
                    "user_id": request.user_id
                },
                "$inc": {"message_count": 1}
            }
        )
        
        return JSONResponse(
            status_code=201,
            content=make_json_serializable(message_doc)
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "chat_id": chat_id}
        )

@app.delete("/api/messages/{message_id}")
async def delete_message(message_id: str):
    """Delete a specific message"""
    try:
        # Convert string to ObjectId for MongoDB
        from bson import ObjectId
        
        try:
            object_id = ObjectId(message_id)
        except:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid message ID format", "message_id": message_id}
            )
        
        result = db.messages.delete_one({"_id": object_id})
        
        if result.deleted_count == 0:
            return JSONResponse(
                status_code=404,
                content={"error": "Message not found", "message_id": message_id}
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message_id": message_id,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "message_id": message_id}
        )

@app.post("/api/sessions")
async def create_session(request: SessionCreateRequest):
    """Create a simple session_id for user_id"""
    try:
        session_doc = {
            'user_id': request.user_id,
            'created_at': datetime.now()
        }
        
        result = db.sessions.insert_one(session_doc)
        session_id = str(result.inserted_id)
        
        # Add session_id to the document for the response
        session_doc['session_id'] = session_id
        session_doc['_id'] = session_id
        
        return JSONResponse(
            status_code=201,
            content=make_json_serializable(session_doc)
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/api/test")
async def test_endpoint():
    """Simple test endpoint to verify server responsiveness"""
    return {"status": "ok", "message": "Server is responsive", "timestamp": datetime.now().isoformat()}

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