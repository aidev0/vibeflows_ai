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
            "agent_name": "user_query_understanding",
            "metadata": {"entry_point_node": True}
        },
        {
            "id": "mermaid_designer",
            "name": "🎨 Mermaid Designer Agent",
            "type": "agent",
            "agent_name": "mermaid_designer"
        },
        {
            "id": "ask_clarifying_questions",
            "name": "Generate response to user based on the understanding and ask clarification questions.",
            "type": "agent",
            "agent_name": "user_interface",
            "action": "ask_clarifying_questions",
            "metadata": {"requires_user_response": True}
        },
    ],
    "edges": [
        {"from": "user_query_understanding", "to": "mermaid_designer"},
        {"from": "mermaid_designer", "to": "ask_clarifying_questions"},
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
            llm_messages.append({"role": "assistant", "content": msg["text"]})
            # If there's JSON data, include it as a separate message
            if msg.get("json"):
                llm_messages.append({"role": "assistant", "content": json.dumps(msg["json"])})
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
            result = get_user_understanding(context["llm_messages"])
            
            # If result is a string (JSON), parse it
            if isinstance(result, str):
                try:
                    # Clean markdown code blocks if present
                    cleaned_result = result.replace("```json", "").replace("```", "")
                    result = json.loads(cleaned_result)
                except json.JSONDecodeError as e:
                    print(f"Error parsing understanding result: {e}")
                    return {"error": f"Failed to parse understanding result: {e}"}
            
            return {"understanding_result": result}
        
        elif agent_name == "mermaid_designer":
            understanding_result = context.get("understanding_result")
            if understanding_result:
                mermaid_diagram = create_mermaid_diagram(understanding_result)
                return {"mermaid_diagram": mermaid_diagram}
            else:
                return {"error": "No understanding_result available for mermaid_designer"}
        
        elif agent_name == "user_interface":
            llm_messages = context["llm_messages"]
            interface_context = {
                "understanding": context.get("understanding_result"),
                "mermaid_diagram": context.get("mermaid_diagram"),
                "user_name": context.get("user_name"),
                "chat_id": context.get("chat_id"),
                "action": action or "general_response"
            }
            response = generate_user_response(llm_messages, interface_context)
            return {"user_response_text": response}
        
        else:
            return {"error": f"Unknown agent: {agent_name}"}
    
    except Exception as e:
        return {"error": f"Agent {agent_name} failed: {str(e)}"}

def build_routing_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """Build context for next_agent router."""
    understanding_result = context.get("understanding_result")
    
    # If understanding_result is a string (JSON), try to parse it
    if isinstance(understanding_result, str):
        try:
            import json
            understanding_result = json.loads(understanding_result)
        except:
            understanding_result = None
    
    return {
        "understanding_result": understanding_result,
        "mermaid_diagram": context.get("mermaid_diagram"),
        "user_response": context.get("user_response"),
        "conversation_state": context.get("conversation_state", "processing")
    }

def evaluate_condition(condition: str, context: Dict[str, Any]) -> bool:
    """Evaluate a condition string against the context."""
    if not condition:
        return True
    
    try:
        # Simple condition evaluation
        understanding_result = context.get("understanding_result", {})
        user_response = context.get("user_response", "")
        
        # Replace variables in condition
        condition = condition.replace("understanding_result.confidence", str(understanding_result.get("confidence", 0)))
        condition = condition.replace("user_response", f"'{user_response}'")
        condition = condition.replace("AND", "and")
        
        # Evaluate the condition
        return eval(condition)
    except Exception as e:
        print(f"Error evaluating condition '{condition}': {e}")
        return False

async def execute_flow(flow: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Execute the flow starting from entry point and return all messages as a list."""
    
    current_node_id = flow["entry_point"]
    max_iterations = 10
    iteration = 0
    responses = []
    
    # Get available agents from flow
    available_agents = get_available_agents_from_flow(flow)
    
    while iteration < max_iterations:
        print(f"🔄 Iteration {iteration + 1}: Processing node '{current_node_id}'")
        
        # Get current node
        current_node = get_node_by_id(flow, current_node_id)
        if not current_node:
            print(f"❌ Node '{current_node_id}' not found")
            break
        
        # Execute current node
        if current_node["type"] == "agent":
            agent_name = current_node["agent_name"]
            action = current_node.get("action")
            
            print(f"🤖 Executing agent: {agent_name}")
            if action:
                print(f"   Action: {action}")
            
            # Execute the agent
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
            
            # Update context with agent results
            context.update(agent_result)
            
            # Save and collect agent results to database
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
        
        elif current_node["type"] == "condition":
            agent_name = current_node["agent_name"]
            
            print(f"🎯 Executing condition router: {agent_name}")
            
            # For next_agent routing - use the updated function signature
            if agent_name == "next_agent":
                flow_conditions = current_node.get("conditions", [])
                routing_context = build_routing_context(context)
                
                # Use the updated next_agent router
                routing_result = determine_next_agent(
                    flow_conditions=flow_conditions,
                    available_agents=available_agents,
                    context=routing_context
                )
                
                if "next_agent" in routing_result:
                    next_agent_name = routing_result["next_agent"]
                    
                    # Map agent names to actual node IDs based on flow structure
                    next_node_id = None
                    
                    # Special mappings based on current node and decision
                    if current_node_id == "confidence_check":
                        if next_agent_name == "user_interface":
                            # Low confidence - need more info
                            confidence = context.get("understanding_result", {}).get("confidence", 0)
                            if confidence < 0.6:
                                next_node_id = "user_interface_more_info"
                            else:
                                next_node_id = "user_interface_clarification"
                        elif next_agent_name == "mermaid_designer":
                            next_node_id = "mermaid_designer"
                    
                    elif current_node_id == "approval_check":
                        if next_agent_name == "user_interface":
                            user_response = context.get("user_response")
                            if user_response == "approve":
                                next_node_id = "user_interface_approval_confirmed"
                            else:
                                # Default to asking questions
                                next_node_id = "user_interface_answer_questions"
                        elif next_agent_name == "mermaid_designer":
                            next_node_id = "mermaid_designer_update"
                    
                    # Generic fallback - find any node with matching agent_name
                    if not next_node_id:
                        for node in flow["nodes"]:
                            if node.get("agent_name") == next_agent_name:
                                next_node_id = node["id"]
                                break
                    
                    if next_node_id:
                        current_node_id = next_node_id
                        iteration += 1
                        continue
                    else:
                        print(f"⚠️ Could not find node for agent: {next_agent_name}")
                        break
        
        # # Check if agent needs user response - break loop to wait
        # if (current_node.get("metadata", {}).get("requires_user_response") or
        #     current_node.get("metadata", {}).get("awaits_user_response") or
        #     current_node.get("action") in ["ask_clarifying_questions", "request_more_information", "present_design_for_approval"]):
        #     print("⏳ Waiting for user response...")
        #     break
        
        # # Check if this is a final state
        # if current_node.get("metadata", {}).get("final_success_state"):
        #     print("✅ Flow completed successfully!")
        #     break
        
        # Get next nodes based on edges (fallback to original flow logic)
        next_nodes = get_next_nodes(flow, current_node_id)
        
        if not next_nodes:
            print("🏁 No more nodes to process")
            break
        
        # Find the first matching condition
        next_node_id = None
        for next_info in next_nodes:
            condition = next_info["condition"]
            if evaluate_condition(condition, context):
                next_node_id = next_info["node"]["id"]
                break
        
        if not next_node_id:
            # Take the first node if no conditions match
            next_node_id = next_nodes[0]["node"]["id"]
        
        current_node_id = next_node_id
        iteration += 1
    
    return responses

def get_last_messages(chat_id: str) -> Dict[str, Any]:
    """Get the last relevant messages from the chat."""
    try:
        # Get all messages sorted by timestamp
        messages = list(
            messages_collection
            .find({"chatId": chat_id})
            .sort("timestamp", -1)
        )
        
        last_messages = {
            "last_mermaid": None,
            "last_understanding": None,
            "last_ai_response": None
        }
        
        for msg in messages:
            if msg.get("sender") == "ai" or msg.get("sender") == "assistant":
                if msg.get("type") == "mermaid" and not last_messages["last_mermaid"]:
                    last_messages["last_mermaid"] = msg.get("mermaid")
                elif msg.get("type") == "user_understanding_json" and not last_messages["last_understanding"]:
                    last_messages["last_understanding"] = msg.get("json")
                elif msg.get("type") == "simple_text" and not last_messages["last_ai_response"]:
                    last_messages["last_ai_response"] = msg.get("text")
            
            # Break if we have all the messages we need
            if all(last_messages.values()):
                break
                
        return last_messages
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
    
    if not chat_id:
        return [{
            "type": "error",
            "text": "Error: chatId required in message document",
            "id": f"error-{int(datetime.now().timestamp() * 1000)}",
            "chatId": chat_id or "unknown",
            "sender": "system",
            "timestamp": datetime.now(timezone(timedelta(hours=-8))).isoformat()
        }]

    if not user_message:
        return [{
            "type": "error", 
            "text": "Error: text required in message document",
            "id": f"error-{int(datetime.now().timestamp() * 1000)}",
            "chatId": chat_id,
            "sender": "system",
            "timestamp": datetime.now(timezone(timedelta(hours=-8))).isoformat()
        }]
    
    # Get last relevant messages for context
    last_messages = get_last_messages(chat_id)
    
    # Get all chat messages for LLM context
    all_messages = get_chat_messages(chat_id)
    llm_messages = convert_messages_to_llm_format(all_messages)
    # Add the current user message
    llm_messages.append({"role": "user", "content": user_message})
    
    # Initialize execution context
    context = {
        "chat_id": chat_id,
        "user_message": user_message,
        "llm_messages": llm_messages,
        "last_mermaid": last_messages["last_mermaid"],
        "last_understanding": last_messages["last_understanding"],
        "last_ai_response": last_messages["last_ai_response"],
        "understanding_result": None,
        "mermaid_diagram": None,
        "user_response": None,
        "user_name": "User",  # Default user name
        "conversation_state": "processing"
    }
    
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