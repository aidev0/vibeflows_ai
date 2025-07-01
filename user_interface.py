import anthropic
import json
import os
from bson import ObjectId
from pymongo import MongoClient
from datetime import datetime
from typing import Dict, Any, Optional

# Database connection
client = MongoClient(os.getenv('MONGODB_URI'))
db = client.vibeflows

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

# Define the flow structure locally
MAIN_FLOW = {
    "name": "user_interface",
    "description": "Main interface handling user queries, routing, and communication",
    "nodes": [
        {
            "id": "query_analyzer",
            "type": "agent",
            "name": "query_analyzer",
            "description": "Analyzes user queries to extract intent, requirements, and context"
        },
        {
            "id": "flow_creator",
            "type": "flow",
            "name": "flow_creator", 
            "description": "Invokes the complete flow creation system"
        },
        {
            "id": "flow_runner",
            "type": "agent",
            "name": "flow_runner",
            "description": "Executes existing flows and workflows"
        },
        {
            "id": "response_generator",
            "type": "agent",
            "name": "response_generator",
            "description": "Generates natural language responses based on actions taken"
        }
    ],
    "edges": [
        {
            "source": "query_analyzer",
            "target": "flow_creator",
            "condition": "output.action_type === 'create_flow'"
        },
        {
            "source": "query_analyzer", 
            "target": "flow_runner",
            "condition": "output.action_type === 'run_flow'"
        },
        {
            "source": "query_analyzer",
            "target": "response_generator",
            "condition": "output.action_type === 'respond' || output.needs_clarification === true"
        },
        {
            "source": "flow_creator",
            "target": "response_generator",
            "condition": ""
        },
        {
            "source": "flow_runner",
            "target": "response_generator",
            "condition": ""
        }
    ]
}

async def process_user_message(user_query: str, chat_id: str, user_id: str) -> Dict[str, Any]:
    """
    Main entry point: Process user message using local agents following the flow
    """
    print(f"🤖 Processing message from user {user_id} in chat {chat_id}")
    
    try:
        # Save user message to database
        save_message(chat_id, user_query, "user", "text")
        
        # Step 1: Query Analyzer
        analysis_result = await execute_query_analyzer(user_query, chat_id, user_id)
        
        # Step 2: Route based on analysis using edges
        next_result = await route_based_on_analysis(analysis_result, chat_id, user_id)
        
        # Step 3: Response Generator (final step)
        final_response = await execute_response_generator(
            user_query, analysis_result, next_result, chat_id, user_id
        )
        
        # Save assistant response
        response_text = final_response.get('response', 'Process completed')
        save_message(chat_id, response_text, "assistant", "text")
        
        return {
            "message": response_text,
            "type": "flow_response",
            "status": "completed",
            "analysis_result": analysis_result,
            "action_result": next_result
        }
        
    except Exception as e:
        error_msg = f"I encountered an error processing your request: {str(e)}"
        save_message(chat_id, error_msg, "assistant", "error")
        return {
            "message": error_msg,
            "type": "error",
            "status": "failed"
        }

async def execute_query_analyzer(user_query: str, chat_id: str, user_id: str) -> Dict[str, Any]:
    """Execute the query_analyzer agent"""
    print("🔍 Executing query_analyzer...")
    try:
        from query_analyzer import query_analyzer
        
        analysis_input = {
            'user_query': user_query,
            'chat_id': chat_id,
            'user_id': user_id,
            'conversation_history': get_recent_conversation(chat_id, limit=5)
        }
        
        result = query_analyzer(analysis_input)
        print(f"📊 Query analysis result: {result.get('action_type', 'unknown')}")
        return result
        
    except Exception as e:
        print(f"❌ Error in query_analyzer: {str(e)}")
        return {
            "action_type": "respond",
            "confidence": 0.0,
            "error": str(e)
        }

async def route_based_on_analysis(analysis_result: Dict[str, Any], chat_id: str, user_id: str) -> Dict[str, Any]:
    """Route to the appropriate agent based on analysis result"""
    action_type = analysis_result.get('action_type', 'respond')
    needs_clarification = analysis_result.get('needs_clarification', False)
    
    print(f"🔀 Routing based on action_type: {action_type}, needs_clarification: {needs_clarification}")
    
    # Check for clarification first - if needed, ask questions before proceeding
    if needs_clarification:
        print("❓ Clarification needed - routing to response_generator")
        return {"routed_to": "response_generator", "analysis": analysis_result, "action": "clarification_needed"}
    
    # Proceed with the intended action only if no clarification is needed
    if action_type == 'create_flow':
        return await execute_flow_creator(analysis_result, chat_id, user_id)
    elif action_type == 'run_flow':
        return await execute_flow_runner(analysis_result, chat_id, user_id)
    else:
        # For 'respond' actions
        return {"routed_to": "response_generator", "analysis": analysis_result}

async def execute_flow_creator(analysis_result: Dict[str, Any], chat_id: str, user_id: str) -> Dict[str, Any]:
    """Execute the flow creation pipeline"""
    print("🏗️ Executing flow_creator...")
    
    try:
        requirements = analysis_result.get('requirements', {})
        requirements_str = json.dumps(requirements) if isinstance(requirements, dict) else str(requirements)
        
        # Step 1: Flow Designer
        from flow_designer import flow_designer
        design_result = flow_designer({'requirements': requirements_str})
        flow_id = design_result.get('_id')
        
        # Step 2: Flow Developer
        from flow_developer import flow_developer
        developer_result = flow_developer({'flow_id': flow_id})
        
        # Step 3: N8N Developer
        from n8n_developer import n8n_developer
        n8n_result = n8n_developer({
            'requirements': requirements_str,
            'user_id': user_id
        })
        
        # Add n8n_workflow_url if available
        n8n_workflow_url = None
        if n8n_result.get('status') == 'published' and user_id:
            n8n_response = n8n_result.get('n8n_response', {})
            workflow_id = n8n_response.get('id')
            
            if workflow_id:
                from pymongo import MongoClient
                client = MongoClient(os.getenv('MONGODB_URI'))
                db = client.vibeflows
                n8n_url_cred = db.credentials.find_one({'user_id': user_id, 'name': 'N8N_URL'})
                if n8n_url_cred:
                    n8n_base_url = n8n_url_cred.get('value', '').rstrip('/')
                    n8n_workflow_url = f"{n8n_base_url}/workflow/{workflow_id}"
        
        return {
            "action": "flow_created",
            "flow_id": str(flow_id) if flow_id else None,
            "design_result": make_json_serializable(design_result),
            "developer_result": make_json_serializable(developer_result),
            "n8n_result": make_json_serializable(n8n_result),
            "n8n_workflow_url": n8n_workflow_url
        }
        
    except Exception as e:
        print(f"❌ Error in flow_creator: {str(e)}")
        return {
            "action": "flow_creation_failed",
            "error": str(e)
        }

async def execute_flow_runner(analysis_result: Dict[str, Any], chat_id: str, user_id: str) -> Dict[str, Any]:
    """Execute an existing flow"""
    print("▶️ Executing flow_runner...")
    
    try:
        flow_id = analysis_result.get('flow_id')
        if not flow_id:
            # Try to find a flow for this user
            flow = db.flows.find_one({'user_id': user_id}, sort=[('created_at', -1)])
            if flow:
                flow_id = str(flow['_id'])
            else:
                return {
                    "action": "no_flow_found",
                    "error": "No flow found to execute. Please create a flow first."
                }
        
        from flow_runner import flow_runner
        
        runner_input = {
            'flow_id': flow_id,
            'input_data': analysis_result.get('input_data', {}),
            'user_id': user_id
        }
        
        execution_result = flow_runner(runner_input)
        
        return {
            "action": "flow_executed",
            "flow_id": flow_id,
            "execution_result": execution_result
        }
        
    except Exception as e:
        print(f"❌ Error in flow_runner: {str(e)}")
        return {
            "action": "flow_execution_failed",
            "error": str(e)
        }

async def execute_response_generator(user_query: str, analysis_result: Dict[str, Any], 
                                   action_result: Dict[str, Any], chat_id: str, user_id: str) -> Dict[str, Any]:
    """Generate the final response to the user"""
    print("💬 Executing response_generator...")
    
    try:
        from response_generator import response_generator
        
        generator_input = {
            'user_query': user_query,
            'action_taken': action_result.get('action', 'analyzed'),
            'results': action_result,
            'conversation_history': get_recent_conversation(chat_id, limit=5)
        }
        
        response = response_generator(generator_input)
        return {"response": response}
        
    except Exception as e:
        print(f"❌ Error in response_generator: {str(e)}")
        raise

def save_message(chat_id: str, message: str, role: str, message_type: str):
    """Save message to database"""
    try:
        message_doc = {
            'chat_id': chat_id,
            'text': message,
            'role': role,
            'type': message_type,
            'content': {},
            'timestamp': datetime.now(),
            'created_at': datetime.now()
        }
        
        db.messages.insert_one(message_doc)
        print(f"💾 Saved {role} message to database")
        
    except Exception as e:
        print(f"❌ Failed to save message: {str(e)}")

def get_recent_conversation(chat_id: str, limit: int = 10) -> list:
    """Get recent conversation history"""
    try:
        messages = list(
            db.messages.find({'chat_id': chat_id})
            .sort('timestamp', -1)
            .limit(limit)
        )
        
        # Convert ObjectIds to strings for JSON serialization
        serialized_messages = []
        for msg in messages:
            if '_id' in msg:
                msg['_id'] = str(msg['_id'])
            # Convert any datetime objects to ISO strings
            if 'timestamp' in msg and hasattr(msg['timestamp'], 'isoformat'):
                msg['timestamp'] = msg['timestamp'].isoformat()
            if 'created_at' in msg and hasattr(msg['created_at'], 'isoformat'):
                msg['created_at'] = msg['created_at'].isoformat()
            serialized_messages.append(msg)
            
        return list(reversed(serialized_messages))  # Reverse to get chronological order
    except Exception as e:
        print(f"❌ Failed to get conversation history: {str(e)}")
        return []

# Convenience functions for direct use
async def create_workflow(requirements: str, user_id: str, chat_id: str = None) -> Dict[str, Any]:
    """Direct workflow creation"""
    if not chat_id:
        chat_id = f"direct_{user_id}_{int(datetime.now().timestamp())}"
    
    return await process_user_message(
        f"Create a workflow for: {requirements}",
        chat_id,
        user_id
    )

async def run_workflow(flow_id: str, user_id: str, input_data: Dict = None, chat_id: str = None) -> Dict[str, Any]:
    """Direct workflow execution"""
    if not chat_id:
        chat_id = f"direct_{user_id}_{int(datetime.now().timestamp())}"
    
    query = f"Run workflow {flow_id}"
    if input_data:
        query += f" with data: {json.dumps(input_data)}"
    
    return await process_user_message(query, chat_id, user_id)

async def execute_flow_creator_streaming(analysis_result: Dict[str, Any], chat_id: str, user_id: str):
    """Execute the flow creation pipeline with streaming updates"""
    print("🏗️ Executing flow_creator with streaming...")
    
    try:
        requirements = analysis_result.get('requirements', {})
        requirements_str = json.dumps(requirements) if isinstance(requirements, dict) else str(requirements)
        
        # Get user's goal from requirements for context
        goal = requirements.get('goal', 'automation workflow') if isinstance(requirements, dict) else requirements
        
        # Step 1: Flow Designer
        yield f"🎯 Creating {goal} architecture..."
        from flow_designer import flow_designer
        design_result = flow_designer({'requirements': requirements_str})
        flow_id = design_result.get('_id')
        flow_name = design_result.get('name', 'Workflow')
        
        yield f"✅ Designed '{flow_name}' with {len(design_result.get('nodes', []))} components"
        
        # Step 2: Flow Developer  
        nodes_with_agents = [n for n in design_result.get('nodes', []) if n.get('type') == 'agent']
        if nodes_with_agents:
            yield f"🤖 Creating {len(nodes_with_agents)} intelligent agents..."
            from flow_developer import flow_developer
            developer_result = flow_developer({'flow_id': flow_id})
            agents_created = len(developer_result.get('agents_created', []))
            yield f"✅ Built {agents_created} specialized agents"
        else:
            developer_result = {"status": "no_agents_needed", "agents_created": []}
            yield f"ℹ️ No custom agents needed for this workflow"
        
        # Step 3: N8N Developer
        yield f"⚙️ Generating n8n workflow for deployment..."
        from n8n_developer import n8n_developer
        n8n_result = n8n_developer({
            'requirements': requirements_str,
            'user_id': user_id
        })
        
        # Handle n8n results with meaningful messages
        if n8n_result.get('status') == 'published':
            yield f"🚀 Deployed to n8n successfully!"
            
            # Get workflow URL
            n8n_workflow_url = None
            n8n_response = n8n_result.get('n8n_response', {})
            workflow_id = n8n_response.get('id')
            
            if workflow_id and user_id:
                from pymongo import MongoClient
                client = MongoClient(os.getenv('MONGODB_URI'))
                db = client.vibeflows
                n8n_url_cred = db.credentials.find_one({'user_id': user_id, 'name': 'N8N_URL'})
                if n8n_url_cred:
                    n8n_base_url = n8n_url_cred.get('value', '').rstrip('/')
                    n8n_workflow_url = f"{n8n_base_url}/workflow/{workflow_id}"
                    yield f"🔗 Access your workflow: {n8n_workflow_url}"
        else:
            yield f"⚠️ n8n deployment had issues: {n8n_result.get('message', 'Unknown error')}"
        
        # Final result - yield instead of return in generator
        final_result = {
            "action": "flow_created",
            "flow_id": str(flow_id) if flow_id else None,
            "design_result": make_json_serializable(design_result),
            "developer_result": make_json_serializable(developer_result),
            "n8n_result": make_json_serializable(n8n_result),
            "n8n_workflow_url": n8n_workflow_url if 'n8n_workflow_url' in locals() else None
        }
        
        yield f"✅ Workflow creation completed!"
        
    except Exception as e:
        yield f"❌ Error creating workflow: {str(e)}"
        print(f"❌ Error in flow_creator_streaming: {str(e)}")

async def execute_clarification_streaming(analysis_result: Dict[str, Any], chat_id: str, user_id: str):
    """Handle clarification questions with context about what was understood"""
    try:
        intent = analysis_result.get('intent', 'automation request')
        requirements = analysis_result.get('requirements', {})
        clarification_questions = analysis_result.get('clarification_questions', [])
        
        # Summarize what we understood
        if isinstance(requirements, dict) and requirements:
            understood_parts = []
            if requirements.get('goal'):
                understood_parts.append(f"goal: {requirements['goal']}")
            if requirements.get('trigger'):
                understood_parts.append(f"trigger: {requirements['trigger']}")
            if requirements.get('platforms'):
                understood_parts.append(f"platforms: {', '.join(requirements['platforms'])}")
            
            if understood_parts:
                yield f"💡 I understand you want: {intent}"
                yield f"📋 What I got: {'; '.join(understood_parts)}"
            else:
                yield f"💡 I understand you want: {intent}"
        else:
            yield f"💡 I understand you want to create a workflow"
        
        # Ask clarification questions
        if clarification_questions:
            yield f"❓ To build the best workflow, I need to know:"
            for i, question in enumerate(clarification_questions[:3], 1):  # Limit to 3 questions
                yield f"{i}. {question}"
        else:
            yield f"❓ Could you provide more specific details about your automation needs?"
        
    except Exception as e:
        yield f"❌ Error processing request: {str(e)}"

# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test_interface():
        # Test conversation
        response1 = await process_user_message(
            "I want to create an automated email marketing workflow",
            "test_chat_123",
            "user_456"
        )
        print("Response 1:", response1)
        
        # Test flow execution
        response2 = await process_user_message(
            "Run my latest workflow",
            "test_chat_123", 
            "user_456"
        )
        print("Response 2:", response2)
    
    asyncio.run(test_interface())

