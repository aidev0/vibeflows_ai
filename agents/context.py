#!/usr/bin/env python3
"""
Context Manager
===============
Gets chat context messages with filtering and deduplication
"""

from typing import Dict, Any, List, Optional
from pymongo import MongoClient
import os

def get_db_connection():
    """Get database connection"""
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    database_name = os.getenv("MONGODB_DATABASE", "vibeflows")
    client = MongoClient(mongo_uri)
    db = client[database_name]
    return db

def get_context_messages(chat_id: str, agent_id: Optional[str] = None, flow_id: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Get context messages for a chat with optional filters
    
    Args:
        chat_id: Required chat ID to filter messages
        agent_id: Optional agent ID filter
        flow_id: Optional flow ID filter
        
    Returns:
        List of context messages with role and content
    """
    db = get_db_connection()
    messages_collection = db.messages
    
    # Build filter query - handle both chat_id and chatId
    filter_query = {
        "$or": [
            {"chat_id": chat_id},
            {"chatId": chat_id}
        ]
    }
    
    if agent_id:
        filter_query["agent_id"] = agent_id
    
    if flow_id:
        filter_query["flow_id"] = flow_id
    
    try:
        # Get all messages matching filters, sorted by _id
        messages = list(messages_collection.find(filter_query).sort("_id", 1))
        
        # Process messages to get unique role+type combinations
        role_type_map = {}
        
        for message in messages:
            raw_role = message.get("role") or message.get("sender", "user")
            # Normalize ai/assistant roles
            if raw_role.lower() in ["ai", "assistant"]:
                role = "assistant"
            else:
                role = raw_role
            
            message_type = message.get("type", "default")
            
            # Create unique key for role+type combination
            role_type_key = f"{role}_{message_type}"
            
            # Keep only the latest message for each role+type combination
            role_type_map[role_type_key] = message
        
        # Convert to context format
        context_messages = []
        
        for message in role_type_map.values():
            # Combine text, markdown, json, mermaid, and code content
            content_parts = []
            
            if message.get("text"):
                content_parts.append(message["text"])
            
            if message.get("markdown"):
                content_parts.append(message["markdown"])
            
            if message.get("json"):
                # Convert JSON to string if it's not already
                json_content = message["json"]
                if isinstance(json_content, dict):
                    import json
                    json_content = json.dumps(json_content, indent=2)
                content_parts.append(json_content)
            
            if message.get("mermaid"):
                content_parts.append(message["mermaid"])
            
            if message.get("code"):
                content_parts.append(message["code"])
            
            # Combine all content parts
            combined_content = "\n".join(content_parts) if content_parts else ""
            
            # Normalize role for output
            raw_role = message.get("role") or message.get("sender", "user")
            normalized_role = "assistant" if raw_role.lower() in ["ai", "assistant"] else raw_role
            
            context_message = {
                "role": normalized_role,
                "content": combined_content
            }
            
            context_messages.append(context_message)
        
        # Sort by original message _id to maintain conversation order
        # We need to map back to original _ids
        message_ids = {id(msg): msg.get("_id") for msg in role_type_map.values()}
        context_messages.sort(key=lambda x: message_ids.get(id(x), 0))
        
        return context_messages
        
    except Exception as e:
        print(f"Error retrieving context messages: {e}")
        return []

def get_recent_context_messages(chat_id: str, 
                               agent_id: Optional[str] = None, 
                               flow_id: Optional[str] = None,
                               limit: int = 50) -> List[Dict[str, str]]:
    """
    Get recent context messages with a limit
    
    Args:
        chat_id: Required chat ID to filter messages
        agent_id: Optional agent ID filter
        flow_id: Optional flow ID filter
        limit: Maximum number of recent messages to consider
        
    Returns:
        List of context messages with role and content
    """
    db = get_db_connection()
    messages_collection = db.messages
    
    # Build filter query - handle both chat_id and chatId
    filter_query = {
        "$or": [
            {"chat_id": chat_id},
            {"chatId": chat_id}
        ]
    }
    
    if agent_id:
        filter_query["agent_id"] = agent_id
    
    if flow_id:
        filter_query["flow_id"] = flow_id
    
    try:
        # Get recent messages matching filters, sorted by _id (newest first)
        recent_messages = list(
            messages_collection.find(filter_query)
            .sort("_id", -1)
            .limit(limit)
        )
        
        # Reverse to get chronological order (oldest first)
        recent_messages.reverse()
        
        # Process messages to get unique role+type combinations
        role_type_map = {}
        
        for message in recent_messages:
            raw_role = message.get("role") or message.get("sender", "user")
            # Normalize ai/assistant roles
            if raw_role.lower() in ["ai", "assistant"]:
                role = "assistant"
            else:
                role = raw_role
            
            message_type = message.get("type", "default")
            
            # Create unique key for role+type combination
            role_type_key = f"{role}_{message_type}"
            
            # Keep only the latest message for each role+type combination
            role_type_map[role_type_key] = message
        
        # Convert to context format
        context_messages = []
        
        for message in role_type_map.values():
            # Combine text, markdown, json, mermaid, and code content
            content_parts = []
            
            if message.get("text"):
                content_parts.append(message["text"])
            
            if message.get("markdown"):
                content_parts.append(message["markdown"])
            
            if message.get("json"):
                # Convert JSON to string if it's not already
                json_content = message["json"]
                if isinstance(json_content, dict):
                    import json
                    json_content = json.dumps(json_content, indent=2)
                content_parts.append(json_content)
            
            if message.get("mermaid"):
                content_parts.append(message["mermaid"])
            
            if message.get("code"):
                content_parts.append(message["code"])
            
            # Combine all content parts
            combined_content = "\n".join(content_parts) if content_parts else ""
            
            # Normalize role for output
            raw_role = message.get("role") or message.get("sender", "user")
            normalized_role = "assistant" if raw_role.lower() in ["ai", "assistant"] else raw_role
            
            context_message = {
                "role": normalized_role,
                "content": combined_content
            }
            
            context_messages.append(context_message)
        
        # Sort by original message _id to maintain conversation order
        context_messages.sort(key=lambda x: next(
            msg.get("_id", 0) for msg in role_type_map.values() 
            if msg.get("role") == x["role"]
        ))
        
        return context_messages
        
    except Exception as e:
        print(f"Error retrieving recent context messages: {e}")
        return []

def get_context_summary(chat_id: str, 
                       agent_id: Optional[str] = None, 
                       flow_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get summary information about the context
    
    Args:
        chat_id: Required chat ID to filter messages
        agent_id: Optional agent ID filter
        flow_id: Optional flow ID filter
        
    Returns:
        Dictionary with context summary information
    """
    db = get_db_connection()
    messages_collection = db.messages
    
    # Build filter query - handle both chat_id and chatId
    filter_query = {
        "$or": [
            {"chat_id": chat_id},
            {"chatId": chat_id}
        ]
    }
    
    if agent_id:
        filter_query["agent_id"] = agent_id
    
    if flow_id:
        filter_query["flow_id"] = flow_id
    
    try:
        # Get total message count
        total_messages = messages_collection.count_documents(filter_query)
        
        # Get unique roles (check both role and sender fields)
        roles_from_role = messages_collection.distinct("role", filter_query)
        roles_from_sender = messages_collection.distinct("sender", filter_query)
        roles = list(set(roles_from_role + roles_from_sender))
        
        # Get unique message types
        message_types = messages_collection.distinct("type", filter_query)
        
        # Get date range
        first_message = messages_collection.find_one(filter_query, sort=[("_id", 1)])
        last_message = messages_collection.find_one(filter_query, sort=[("_id", -1)])
        
        summary = {
            "chat_id": chat_id,
            "agent_id": agent_id,
            "flow_id": flow_id,
            "total_messages": total_messages,
            "unique_roles": roles,
            "message_types": message_types,
            "first_message_at": first_message.get("created_at") if first_message else None,
            "last_message_at": last_message.get("created_at") if last_message else None
        }
        
        return summary
        
    except Exception as e:
        print(f"Error getting context summary: {e}")
        return {
            "chat_id": chat_id,
            "agent_id": agent_id,
            "flow_id": flow_id,
            "error": str(e)
        }

# Usage examples
if __name__ == "__main__":
    # Get all context messages for a chat
    context = get_context_messages("chat_123")
    print(f"Found {len(context)} unique context messages")
    
    # Get context for specific agent
    agent_context = get_context_messages("chat_123", agent_id="agent_456")
    print(f"Found {len(agent_context)} messages from agent_456")
    
    # Get recent context with limit
    recent_context = get_recent_context_messages("chat_123", limit=20)
    print(f"Found {len(recent_context)} recent unique messages")
    
    # Get context summary
    summary = get_context_summary("chat_123")
    print(f"Summary: {summary}")