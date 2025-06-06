#!/usr/bin/env python3
"""
User Interface Orchestrator (Refactored)
=========================================
Updated to work with the new next_agent router while preserving flow structure.
"""

import json
import os
from typing import Dict, Any, List, AsyncGenerator
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient

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

# Keep the original flow structure
# VIBEFLOWS_FLOW = {
#     "flow_name": "VibeFlows Core Experience Flow",
#     "entry_point": "user_query_understanding",
#     "nodes": [
#         {
#             "id": "user_query_understanding",
#             "name": "🔍 Understanding Agent",
#             "type": "agent",
#             "agent_name": "user_query_understanding",
#             "metadata": {"entry_point_node": True}
#         },
#         {
#             "id": "confidence_check",
#             "name": "🎯 Confidence Check",
#             "type": "condition",
#             "agent_name": "next_agent",
#             "conditions": [
#                 {"condition": "understanding_result.confidence >= 0.8", "next_node": "mermaid_designer"},
#                 {"condition": "understanding_result.confidence >= 0.6 AND understanding_result.confidence < 0.8", "next_node": "user_interface_clarification"},
#                 {"condition": "understanding_result.confidence < 0.6", "next_node": "user_interface_more_info"}
#             ],
#             "metadata": {"decision_node": True}
#         },
#         {
#             "id": "mermaid_designer",
#             "name": "🎨 Mermaid Designer Agent",
#             "type": "agent",
#             "agent_name": "mermaid_designer"
#         },
#         {
#             "id": "user_interface_present_design",
#             "name": "👀 Present Design",
#             "type": "agent",
#             "agent_name": "user_interface",
#             "action": "present_design_for_approval",
#             "metadata": {"awaits_user_response": True}
#         },
#         {
#             "id": "approval_check",
#             "name": "✅ Approval Check",
#             "type": "condition",
#             "agent_name": "next_agent",
#             "conditions": [
#                 {"condition": "user_response == 'approve'", "next_node": "user_interface_approval_confirmed"},
#                 {"condition": "user_response == 'request_changes'", "next_node": "mermaid_designer_update"},
#                 {"condition": "user_response == 'ask_questions'", "next_node": "user_interface_answer_questions"}
#             ],
#             "metadata": {"decision_node": True, "user_input_required": True}
#         },
#         {
#             "id": "user_interface_approval_confirmed",
#             "name": "🎉 Design Approved",
#             "type": "agent",
#             "agent_name": "user_interface",
#             "action": "confirm_design_approval"
#         },
#         {
#             "id": "user_interface_building_started",
#             "name": "🚀 Building Started Notification",
#             "type": "agent",
#             "agent_name": "user_interface",
#             "action": "notify_building_started",
#             "metadata": {"final_success_state": True}
#         },
#         {
#             "id": "user_interface_clarification",
#             "name": "❓ Ask Clarification",
#             "type": "agent",
#             "agent_name": "user_interface",
#             "action": "ask_clarifying_questions",
#             "metadata": {"requires_user_response": True}
#         },
#         {
#             "id": "user_interface_more_info",
#             "name": "🔄 Request More Info",
#             "type": "agent",
#             "agent_name": "user_interface",
#             "action": "request_more_information",
#             "metadata": {"requires_user_response": True}
#         }
#     ],
#     "edges": [
#         {"from": "user_query_understanding", "to": "confidence_check"},
#         {"from": "confidence_check", "to": "mermaid_designer", "condition": "understanding_result.confidence >= 0.8"},
#         {"from": "confidence_check", "to": "user_interface_clarification", "condition": "understanding_result.confidence >= 0.6 AND understanding_result.confidence < 0.8"},
#         {"from": "confidence_check", "to": "user_interface_more_info", "condition": "understanding_result.confidence < 0.6"},
#         {"from": "mermaid_designer", "to": "user_interface_present_design"},
#         {"from": "user_interface_present_design", "to": "approval_check", "condition": "user_response_received"},
#         {"from": "approval_check", "to": "user_interface_approval_confirmed", "condition": "user_response == 'approve'"},
#         {"from": "user_interface_approval_confirmed", "to": "user_interface_building_started"}
#     ]
# }

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
        {"from": "user_query_understanding", "to": "confidence_check"},
        {"from": "mermaid_designer", "to": "ask_clarifying_questions"},
    ]
}


def save_message(chat_id: str, text: str, sender: str, message_type: str = "text", 
                mermaid: str = None, json_data: dict = None):
    """Save message to MongoDB."""
    try:
        # Ensure required fields are not None/empty
        if not chat_id or not text or not sender:
            print(f"⚠️ WARNING - Invalid message data: chat_id={chat_id}, text={text}, sender={sender}")
            return None
        
        # Use timezone-aware timestamp
        from datetime import timezone, timedelta
        # Adjust this offset to match your timezone (e.g., UTC-8 for PST, UTC+1 for CET)
        user_timezone = timezone(timedelta(hours=-8))  # Change this to your timezone offset
        current_time = datetime.now(user_timezone)
            
        message_doc = {
            "id": f"{sender}-{int(current_time.timestamp() * 1000)}",
            "chatId": chat_id,
            "text": text,
            "mermaid": mermaid,
            "sender": sender,
            "timestamp": current_time,
            "type": message_type,
            "json": json_data
        }
        
        print(f"🔍 DEBUG - Saving message: {message_doc}")
        result = messages_collection.insert_one(message_doc)
        return result.inserted_id
        
    except Exception as e:
        print(f"Error saving message: {e}")
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

def execute_flow(flow: Dict[str, Any], context: Dict[str, Any]) -> str:
    """Execute the flow starting from entry point."""
    
    current_node_id = flow["entry_point"]
    max_iterations = 10
    iteration = 0
    
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
                break
            
            # Update context with agent results
            context.update(agent_result)
            
            # Save agent results to database
            if "understanding_result" in agent_result:
                save_message(
                    context["chat_id"],
                    "Requirements analysis completed",
                    "ai",
                    "user_understanding_json",
                    json_data=agent_result["understanding_result"]
                )
            
            if "mermaid_diagram" in agent_result:
                save_message(
                    context["chat_id"],
                    "This is a design for workflow. Please let us know more details so we update the design and build you a workflow to solve your specific task.",
                    "ai",
                    "mermaid",
                    mermaid=agent_result["mermaid_diagram"]
                )
            
            if "user_response_text" in agent_result:
                print(f"🔍 DEBUG - Saving user response: {agent_result['user_response_text']}")
                save_message(
                    context["chat_id"],
                    agent_result["user_response_text"],
                    "ai",
                    "simple_text"
                )
        
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
        
        # Check if agent needs user response - break loop to wait
        if (current_node.get("metadata", {}).get("requires_user_response") or
            current_node.get("metadata", {}).get("awaits_user_response") or
            current_node.get("action") in ["ask_clarifying_questions", "request_more_information", "present_design_for_approval"]):
            print("⏳ Waiting for user response...")
            break
        
        # Check if this is a final state
        if current_node.get("metadata", {}).get("final_success_state"):
            print("✅ Flow completed successfully!")
            break
        
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
    
    # Return final response
    return context.get("user_response_text", "Process completed successfully!")

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

async def run_flow(user_query: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Main entry point: Execute the flow with user query and stream responses.
    
    Args:
        user_query: Message document with chatId, text, sender_id, etc.
        
    Yields:
        Dict containing response data and type
    """
    
    # Get required fields
    chat_id = user_query.get("chatId")
    user_message = user_query.get("text")
    sender_id = user_query.get("sender_id")
    
    if not chat_id:
        yield {
            "type": "error",
            "text": "Error: chatId required in message document"
        }
        return
    
    # Get user data
    user_data = get_user_data(sender_id) if sender_id else None
    user_name = user_data.get("name") if user_data else None
    
    # Get last relevant messages
    last_messages = get_last_messages(chat_id)
    
    # Initialize execution context
    context = {
        "chat_id": chat_id,
        "sender_id": sender_id,
        "user_name": user_name,
        "user_message": user_message,
        "last_mermaid": last_messages["last_mermaid"],
        "last_understanding": last_messages["last_understanding"],
        "last_ai_response": last_messages["last_ai_response"],
        "understanding_result": None,
        "mermaid_diagram": None,
        "user_response": None,
        "conversation_state": "processing"
    }
    
    try:
        # First, get user understanding
        understanding_result = get_user_understanding([{"role": "user", "content": user_message}])
        if isinstance(understanding_result, str):
            try:
                understanding_result = json.loads(understanding_result.replace("```json", "").replace("```", ""))
            except json.JSONDecodeError as e:
                print(f"Error parsing understanding result: {e}")
                error_doc = save_message(
                    chat_id,
                    "Error processing your request. Please try again.",
                    "ai",
                    "simple_text"
                )
                if error_doc:
                    yield error_doc
                return
        
        context["understanding_result"] = understanding_result
        
        # Save and yield understanding result
        understanding_doc = save_message(
            chat_id,
            "This is our understanding analysis. Please let us know if you have any questions or feedback.",
            "ai",
            "user_understanding_json",
            json_data=understanding_result
        )
        if understanding_doc:
            yield understanding_doc
        
        # Generate and yield mermaid diagram
        mermaid_diagram = create_mermaid_diagram(understanding_result)
        context["mermaid_diagram"] = mermaid_diagram
        
        mermaid_doc = save_message(
            chat_id,
            "This is a design for workflow. Please let us know more details so we update the design and build you a workflow to solve your specific task.",
            "ai",
            "mermaid",
            mermaid=mermaid_diagram
        )
        if mermaid_doc:
            yield mermaid_doc
        
        # Generate and yield user interface response
        interface_context = {
            "understanding": understanding_result,
            "mermaid_diagram": mermaid_diagram,
            "user_name": user_name,
            "chat_id": chat_id,
            "last_mermaid": last_messages["last_mermaid"],
            "last_understanding": last_messages["last_understanding"],
            "last_ai_response": last_messages["last_ai_response"],
            "action": "ask_clarifying_questions"
        }
        
        final_response = generate_user_response(
            [{"role": "user", "content": user_message}],
            interface_context
        )
        
        # Save and yield the final response
        final_doc = save_message(chat_id, final_response, "ai", "simple_text")
        if final_doc:
            yield final_doc
        
    except Exception as e:
        error_response = f"I apologize, but I encountered an error: {str(e)}"
        print(f"🔍 DEBUG - Error response: {error_response}")
        error_doc = save_message(chat_id, error_response, "ai", "simple_text")
        if error_doc:
            yield error_doc

if __name__ == "__main__":
    # Test example
    async def test_flow():
        test_message = {
            "chatId": "test_chat_123",
            "text": "I want to automate lead generation",
            "sender_id": "test_user_456"
        }
        
        async for response in run_flow(test_message):
            print(f"Response: {response}")
    
    import asyncio
    asyncio.run(test_flow())