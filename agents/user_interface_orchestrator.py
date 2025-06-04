#!/usr/bin/env python3
"""
User Interface Orchestrator
============================
Orchestrates the entire VibeFlows pipeline and manages conversation flow.
"""

import json
import os
from typing import Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient

# Import agents
from agents.user_query_understanding import get_user_understanding
from agents.user_interface import generate_user_response

# Load environment variables
load_dotenv()

class VibeFlowsOrchestrator:
    def __init__(self):
        # MongoDB setup
        self.mongo_client = MongoClient(os.getenv("MONGODB_URI"))
        self.db = self.mongo_client[os.getenv("MONGODB_DATABASE")]
        self.messages_collection = self.db["messages"]
        self.users_collection = self.db["users"]
        
        # Conversation state
        self.chat_id = None
        self.user_id = None
        self.user_name = None
        self.conversation_history = []
        self.understanding_result = None
        
    def save_message(self, text: str, sender: str, message_type: str = "text", 
                    mermaid: str = None, json_data: dict = None):
        """Save message to MongoDB."""
        try:
            message_doc = {
                "id": f"{sender}-{int(datetime.now().timestamp() * 1000)}",
                "chatId": self.chat_id,
                "text": text,
                "mermaid": mermaid,
                "sender": sender,
                "timestamp": datetime.now(),
                "type": message_type,
                "json": json_data
            }
            
            result = self.messages_collection.insert_one(message_doc)
            return result.inserted_id
            
        except Exception as e:
            print(f"Error saving message: {e}")
            return None
    
    def get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Get user data from database."""
        try:
            return self.users_collection.find_one({"user_id": user_id})
        except Exception as e:
            print(f"Error getting user data: {e}")
            return None
    
    def get_chat_messages(self, chat_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a chat."""
        try:
            messages = list(
                self.messages_collection
                .find({"chatId": chat_id})
                .sort("timestamp", 1)
            )
            return messages
        except Exception as e:
            print(f"Error getting chat messages: {e}")
            return []
    
    def convert_messages_to_llm_format(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert database messages to LLM format."""
        llm_messages = []
        for msg in messages:
            if msg.get("sender") == "user":
                llm_messages.append({"role": "user", "content": msg["text"]})
            elif msg.get("sender") == "ai" and msg.get("type") in ["simple_text", "response"]:
                llm_messages.append({"role": "assistant", "content": msg["text"]})
        return llm_messages
    
    def start_conversation(self, chat_id: str, user_id: str = None, user_name: str = None):
        """Initialize a new conversation."""
        self.chat_id = chat_id
        self.user_id = user_id
        self.user_name = user_name
        
        # Get existing messages if any
        existing_messages = self.get_chat_messages(chat_id)
        self.conversation_history = self.convert_messages_to_llm_format(existing_messages)
        
        # Get user data if user_id provided
        if user_id and not user_name:
            user_data = self.get_user_data(user_id)
            if user_data:
                self.user_name = user_data.get("name")
        
        return f"Ready to help you with marketing automation, {self.user_name or 'there'}!"
    
    def process_user_input(self, user_input: str) -> str:
        """Process user input and return appropriate response."""
        
        # Save user message
        self.save_message(user_input, "user", "text")
        
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Run understanding agent
        try:
            self.understanding_result = get_user_understanding(self.conversation_history)
            
            # Save understanding result
            self.save_message(
                "Requirements analysis completed",
                "ai",
                "user_understanding", 
                json_data=self.understanding_result
            )
            
            # Generate response using interface agent
            response = self._generate_response()
            
            # Save AI response
            self.save_message(response, "ai", "simple_text")
            
            return response
            
        except Exception as e:
            error_response = f"I apologize, but I'm having trouble processing your request right now. Let me try again. (Error: {str(e)})"
            self.save_message(error_response, "ai", "simple_text")
            return error_response
    
    def _generate_response(self) -> str:
        """Generate response using interface agent."""
        
        context = {
            "understanding": self.understanding_result,
            "user_name": self.user_name,
            "chat_id": self.chat_id
        }
        
        return generate_user_response(self.conversation_history, context)
    
    def get_conversation_status(self) -> Dict[str, Any]:
        """Get current conversation status."""
        return {
            "chat_id": self.chat_id,
            "user_id": self.user_id, 
            "user_name": self.user_name,
            "message_count": len(self.conversation_history),
            "has_understanding": self.understanding_result is not None,
            "understanding_confidence": self.understanding_result.get("confidence", 0) if self.understanding_result else 0,
            "ready_for_design": self.understanding_result.get("has_enough_info_for_planning", False) if self.understanding_result else False
        }

# Main entry point function
def main(message_doc: Dict[str, Any]) -> str:
    """
    Main entry point: Accept message document and run full pipeline.
    
    Args:
        message_doc: Message document with chatId, text, sender, etc.
        
    Returns:
        AI response string
    """
    
    # Get required fields
    chat_id = message_doc.get("chatId")
    user_message = message_doc.get("text")
    user_id = message_doc.get("sender")
    
    if not chat_id:
        return "Error: chatId required in message document"
    
    orchestrator = VibeFlowsOrchestrator()
    orchestrator.start_conversation(chat_id, user_id)
    
    # If no text, this is beginning of chat - return greeting
    if not user_message:
        greeting = "Welcome to VibeFlows! 🌊 I'm your AI assistant that turns plain English into powerful marketing automation. What marketing workflow would you like to automate today?"
        orchestrator.save_message(greeting, "ai", "simple_text")
        return greeting
    
    # Process user message
    return orchestrator.process_user_input(user_message)

if __name__ == "__main__":
    # Test example
    test_message = {
        "chatId": "test_chat_123",
        "text": "I want to automate lead generation",
        "userId": "test_user_456"
    }
    
    response = main(test_message)
    print(response)