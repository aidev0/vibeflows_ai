#!/usr/bin/env python3
"""
User Interface Agent
===================
Simple communication interface for VibeFlows users.
Only responsible for generating user-friendly responses.
"""

from typing import List, Dict, Any
from agents.llm_inference import run_inference

SYSTEM = """
You are the user interface agent for VibeFlows, a marketing automation AI.

<role>
You are ONLY responsible for communicating with users in a friendly, helpful way.
You do NOT analyze requirements, make decisions, or run workflows.
You simply provide clear, engaging responses based on what other agents have determined.
</role>

<guidelines>
- Be friendly, professional, and encouraging
- Use clear, non-technical language
- Provide specific examples when explaining concepts
- Keep responses concise but informative
- Use emojis appropriately to make conversations engaging
- Focus on business value and marketing outcomes
</guidelines>

<response_format>
Respond naturally in plain text. Be conversational and helpful.
</response_format>
"""

def generate_user_response(context: Dict[str, Any] = None, action: str = None, model_name="claude-sonnet-4-20250514") -> str:
    """
    Generate a user-friendly response.
    
    Args:
        messages: Conversation history
        context: Additional context from orchestrator (analysis results, etc.)
        model_name: LLM model to use
        
    Returns:
        User-friendly response string
    """
    
    # Add system message
    messages = [{"role": "system", "content": SYSTEM}]

    if "last_ai_response" in context:
        messages.append({"role": "assistant", "content": str(context["last_ai_response"])})
    if "last_understanding" in context:
        messages.append({"role": "assistant", "content": str(context["last_understanding"])})
    if "last_mermaid" in context:
        messages.append({"role": "assistant", "content": str(context["last_mermaid"])})
    if "user_message" in context:
        messages.append({"role": "user", "content": str(context["user_message"])})  
    if "current_understanding" in context:
        messages.append({"role": "assistant", "content": str(context["current_understanding"])})
    if "current_mermaid" in context:
        messages.append({"role": "assistant", "content": str(context["current_mermaid"])})
    messages.append({"role": "user", "content": "create a response based on user's latest messages and the context."})
    try:
        response = run_inference(messages, model_name=model_name)
        return response
    except Exception as e:
        return f"I apologize, but I'm experiencing some technical difficulties. Please try again in a moment. (Error: {str(e)})"
