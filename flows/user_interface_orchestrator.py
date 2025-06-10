#!/usr/bin/env python3
"""
User Interface Orchestrator (Fixed)
====================================
Fixed MongoDB ObjectId serialization issues for streaming responses.
"""

import json
import os
from typing import Dict, Any, List, AsyncGenerator
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId

# Import agents
from agents.user_query_understanding import get_user_understanding
from agents.user_interface import generate_user_response
from agents.mermaid_designer import create_mermaid_diagram
from agents.next_agent import determine_next_agent
from agents.n8n_workflow_developer import create_n8n_workflow

# Load environment variables
load_dotenv()

# MongoDB setup
mongo_client = MongoClient(os.getenv("MONGODB_URI"))
db = mongo_client[os.getenv("MONGODB_DATABASE")]
messages_collection = db["messages"]
users_collection = db["users"]

VIBEFLOWS_FLOW = {
    "flow_name": "VibeFlows Core Experience Flow",
    "entry_point": "user_query_understanding",
    "nodes": [
        {
            "id": "user_query_understanding",
            "name": "🔍 Understanding Agent",
            "type": "agent",
            "action": "Analyze user query and provide understanding",
            "agent_name": "user_query_understanding",
            "metadata": {"entry_point_node": True}
        },
        {
            "id": "mermaid_designer",
            "name": "🎨 Mermaid Designer Agent",
            "type": "agent",
            "action": "Design a mermaid diagram based on the understanding",
            "agent_name": "mermaid_designer"
        },
        {
            "id": "n8n_workflow_developer",
            "name": "🤖 N8N Workflow Developer Agent",
            "type": "agent",
            "action": "Develop N8N workflow based on the understanding and mermaid diagram.",
            "agent_name": "n8n_workflow_developer"
        },
        {
            "id": "user_communication_agent",
            "name": "💬 User Communication Agent",
            "action": "Generate response to user based on our understanding & mermaid diagram and ask clarification questions if needed.",
            "type": "agent",
            "agent_name": "user_interface",
            "metadata": {"requires_user_response": True}
        },
    ],
    "edges": [
        {"from": "user_query_understanding", "to": "mermaid_designer"},
        {"from": "mermaid_designer", "to": "n8n_workflow_developer"},
        {"from": "n8n_workflow_developer", "to": "user_communication_agent"},
    ]
}

def save_message(chat_id: str, text: str, sender: str, message_type: str = "text", 
                mermaid: str = None, json_data: dict = None) -> Dict[str, Any]:
    """
    Save message to MongoDB and return the message document (not ObjectId).
    
    Returns:
        Dict containing the complete message document for streaming
    """
    try:
        # Ensure required fields are not None/empty
        if not chat_id or not text or not sender:
            print(f"⚠️ WARNING - Invalid message data: chat_id={chat_id}, text={text}, sender={sender}")
            return None
        
        # Use timezone-aware timestamp (PST/PDT)
        user_timezone = timezone(timedelta(hours=-8))  # PST timezone
        current_time = datetime.now(user_timezone)
        
        # Create message document
        message_doc = {
            "id": f"{sender}-{int(current_time.timestamp() * 1000)}",
            "chatId": chat_id,
            "text": text,
            "sender": sender,
            "timestamp": current_time,
            "type": message_type
        }
        
        # Add optional fields only if they exist
        if mermaid:
            message_doc["mermaid"] = mermaid
        if json_data:
            message_doc["json"] = json_data
        
        print(f"🔍 DEBUG - Saving message: {message_doc}")
        
        # Save to MongoDB
        result = messages_collection.insert_one(message_doc.copy())  # Use copy to preserve original
        
        # Convert timestamp to ISO string for JSON serialization
        message_doc["timestamp"] = current_time.isoformat()
        
        # Remove MongoDB's _id from the returned document since we have our own id
        if "_id" in message_doc:
            del message_doc["_id"]
        
        print(f"✅ Message saved with ID: {result.inserted_id}")
        return message_doc
        
    except Exception as e:
        print(f"❌ Error saving message: {e}")
        return None

def get_user_data(user_id: str) -> Dict[str, Any]:
    """Get user data from database."""
    try:
        return users_collection.find_one({"user_id": user_id})
    except Exception as e:
        print(f"Error getting user data: {e}")
        return None

def get_chat_messages(chat_id: str) -> List[Dict[str, Any]]:
    """Get all messages for a chat."""
    try:
        messages = list(
            messages_collection
            .find({"chatId": chat_id})
            .sort("timestamp", 1)
        )
        return messages
    except Exception as e:
        print(f"Error getting chat messages: {e}")
        return []

def convert_messages_to_llm_format(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert database messages to LLM format."""
    llm_messages = []
    for msg in messages:
        # Handle user messages
        if msg.get("sender") == "user":
            llm_messages.append({"role": "user", "content": msg["text"]})
        # Handle AI messages
        elif msg.get("sender") == "ai":
            # Include all AI messages regardless of type
            if msg["type"] == "mermaid" and msg["mermaid"]:
                content = "DECRIPTION" + "\n" + msg["text"] + "MERMAID FLOWCHART:\n" + str(msg["mermaid"])
            elif "json" in msg["type"]:
                content = "DESCRIPTION:\n" + msg["text"] + "\nJSON DATA:\n" + json.dumps(msg["json"])
            else:
                content = msg["text"]
            llm_messages.append({"role": "assistant", "content": content})
    return llm_messages

def get_node_by_id(flow: Dict[str, Any], node_id: str) -> Dict[str, Any]:
    """Get a node from the flow by its ID."""
    for node in flow["nodes"]:
        if node["id"] == node_id:
            return node
    return None

def get_next_nodes(flow: Dict[str, Any], current_node_id: str) -> List[Dict[str, Any]]:
    """Get possible next nodes from current node."""
    next_nodes = []
    for edge in flow["edges"]:
        if edge["from"] == current_node_id:
            next_node = get_node_by_id(flow, edge["to"])
            if next_node:
                next_nodes.append({
                    "node": next_node,
                    "condition": edge.get("condition")
                })
    return next_nodes

def get_available_agents_from_flow(flow: Dict[str, Any]) -> List[str]:
    """Extract available agent names from flow structure."""
    agents = set()
    for node in flow["nodes"]:
        if node.get("agent_name") and node["agent_name"] != "next_agent":
            agents.add(node["agent_name"])
    return list(agents)

def execute_agent(agent_name: str, context: Dict[str, Any], action: str = None) -> Dict[str, Any]:
    """Execute a specific agent with given context."""
    
    try:
        if agent_name == "user_query_understanding":
            result = get_user_understanding(context)
            
            # If result is a string (JSON), parse it
            if isinstance(result, str):
                try:
                    # Clean markdown code blocks if present
                    cleaned_result = result.replace("```json", "").replace("```", "")
                    result = json.loads(cleaned_result)
                    print(f"🔍 DEBUG - Result of {agent_name}\n: {result}")
                except json.JSONDecodeError as e:
                    print(f"Error parsing understanding result: {e}")
                    return {"error": f"Failed to parse understanding result: {e}"}
            
            return {"understanding_result": result}
        
        elif agent_name == "mermaid_designer":
            mermaid_diagram = create_mermaid_diagram(context)
            return {"mermaid_diagram": mermaid_diagram}
        
        elif agent_name == "n8n_workflow_developer":
            response = create_n8n_workflow(context)
            return {"n8n_workflow_json": response}
        
        elif agent_name == "user_interface":
            response = generate_user_response(context)
            return {"user_response_text": response}
        
        else:
            return {"error": f"Unknown agent: {agent_name}"}
    
    except Exception as e:
        return {"error": f"Agent {agent_name} failed: {str(e)}"}

async def execute_flow(flow: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Execute the flow starting from entry point and return all messages as a list."""
    
    current_node_id = flow["entry_point"]
    max_iterations = 10
    iteration = 0
    responses = []
    
    while iteration < max_iterations:
        print(f"🔄 Iteration {iteration + 1}: Processing node '{current_node_id}'")

        current_node = get_node_by_id(flow, current_node_id)
        if not current_node:
            print(f"❌ Node '{current_node_id}' not found")
            break

        next_nodes = get_next_nodes(flow, current_node_id)
        next_node_id = next_nodes[0]["node"]["id"] if next_nodes else None

        if current_node["type"] == "agent":
            agent_name = current_node["agent_name"]
            action = current_node.get("action")
            
            print(f"🤖 Executing agent: {agent_name}")
            if action:
                print(f"   Action: {action}")
            
            agent_result = execute_agent(agent_name, context, action)
            
            if "error" in agent_result:
                print(f"❌ Agent error: {agent_result['error']}")
                error_doc = save_message(
                    context["chat_id"],
                    f"Error in {agent_name}: {agent_result['error']}",
                    "ai",
                    "simple_text"
                )
                if error_doc:
                    responses.append(error_doc)
                break
            
            if "understanding_result" in agent_result:
                understanding_doc = save_message(
                    context["chat_id"],
                    "Requirements analysis completed",
                    "ai",
                    "user_understanding_json",
                    json_data=agent_result["understanding_result"]
                )
                if understanding_doc:
                    responses.append(understanding_doc)
                context["current_understanding"] = agent_result["understanding_result"]
            
            if "mermaid_diagram" in agent_result:
                mermaid_doc = save_message(
                    context["chat_id"],
                    "This is a design for workflow. Please let us know more details so we update the design and build you a workflow to solve your specific task.",
                    "ai",
                    "mermaid",
                    mermaid=agent_result["mermaid_diagram"]
                )
                if mermaid_doc:
                    responses.append(mermaid_doc)
                context["current_mermaid"] = agent_result["mermaid_diagram"]
            
            if "user_response_text" in agent_result:
                print(f"🔍 DEBUG - Saving user response: {agent_result['user_response_text']}")
                response_doc = save_message(
                    context["chat_id"],
                    agent_result["user_response_text"],
                    "ai",
                    "simple_text"
                )
                if response_doc:
                    responses.append(response_doc)
        
        if not next_node_id:
            print("🏁 No more nodes to process")
            break

        current_node_id = next_node_id
        iteration += 1

    return responses

def get_context(user_query) -> Dict[str, Any]:
    """Get the last relevant messages from the chat."""
     # Get required fields
    chat_id = user_query.get("chatId")
    user_message = user_query.get("text")
    user_id = user_query.get("user_id")
    
    try:
        # Get all messages sorted by timestamp
        messages = list(
            messages_collection
            .find({"chatId": chat_id})
            .sort("timestamp", -1)
        )

        context = {
                "chat_id": chat_id,
                "user_id": user_id,
                "user_message": user_message,
                "last_mermaid": None,  # last mermaid in chat db before edit, it is gonna be prev_mermaid after we make nw one.
                "last_understanding": None,
                "last_ai_response": None,
                "current_understanding": None,
                "current_mermaid": None,
                "conversation_state": "processing",
                "last_n8n_workflow": None,
                }
        
        last_messages = {
            "last_mermaid": None,
            "last_understanding": None,
            "last_ai_response": None
        }
        
        for msg in messages:
            if msg.get("sender") == "ai" or msg.get("sender") == "assistant":
                if msg.get("type") == "mermaid" and not last_messages["last_mermaid"]:
                    context["last_mermaid"] = msg.get("mermaid")
                elif msg.get("type") == "user_understanding_json" and not last_messages["last_understanding"]:
                    context["last_understanding"] = msg.get("json")
                elif msg.get("type") == "simple_text" and not last_messages["last_ai_response"]:
                    context["last_ai_response"] = msg.get("text")
                elif msg.get("type") == "n8n_workflow_json" and not last_messages["last_n8n_workflow"]:
                    context["last_n8n_workflow"] = msg.get("json")
        return context
    except Exception as e:
        print(f"Error getting last messages: {e}")
        return {
            "last_mermaid": None,
            "last_understanding": None,
            "last_ai_response": None
        }

async def run_flow(user_query: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Main entry point: Execute the complete workflow with user query and return all responses.
    
    Args:
        user_query: Message document with chatId, text, sender_id, etc.
        
    Returns:
        List of response documents
    """
    
    # Get required fields
    chat_id = user_query.get("chatId")
    user_message = user_query.get("text")
    user_id = user_query.get("user_id")
    
    if not chat_id:
        return [{
            "type": "error",
            "text": "Error: chatId required in message document",
            "id": f"error-{int(datetime.now().timestamp() * 1000)}",
            "chatId": chat_id or "unknown",
            "sender": "ai",
            "timestamp": datetime.now(timezone(timedelta(hours=-8))).isoformat()
        }]

    if not user_message:
        return [{
            "type": "error", 
            "text": "Error: text required in message document",
            "id": f"error-{int(datetime.now().timestamp() * 1000)}",
            "chatId": chat_id,
            "sender": "ai",
            "timestamp": datetime.now(timezone(timedelta(hours=-8))).isoformat()
        }]
    if not user_id:
        return [{
            "type": "error", 
            "text": "Error: text required in message document",
            "id": f"error-{int(datetime.now().timestamp() * 1000)}",
            "chatId": chat_id,
            "sender": "ai",
            "timestamp": datetime.now(timezone(timedelta(hours=-8))).isoformat()
        }]
    
    # Get last relevant messages for context
    context = get_context(user_query)
    
    try:
        print(f"🚀 Starting workflow execution for chat: {chat_id}")
        print(f"📝 User message: {user_message}")
        
        # Execute the complete flow and get all responses
        responses = await execute_flow(VIBEFLOWS_FLOW, context)
        print(f"🎉 Workflow execution completed for chat: {chat_id}")
        return responses
        
    except Exception as e:
        error_response = f"I apologize, but I encountered an error: {str(e)}"
        print(f"❌ Error in run_flow: {e}")
        error_doc = save_message(chat_id, error_response, "ai", "simple_text")
        return [error_doc] if error_doc else []