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

def generate_user_response(messages: List[Dict[str, Any]], context: Dict[str, Any] = None, model_name="claude-sonnet-4-20250514") -> str:
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
    full_messages = [{"role": "system", "content": SYSTEM}]
    
    # Add context if provided
    if context:
        context_msg = f"Context from other agents: {context}"
        full_messages.append({"role": "system", "content": context_msg})
    
    # Add conversation history
    full_messages.extend(messages)
    
    try:
        response = run_inference(full_messages, model_name=model_name)
        return response
    except Exception as e:
        return f"I apologize, but I'm experiencing some technical difficulties. Please try again in a moment. (Error: {str(e)})"

def generate_greeting(user_name: str = None) -> str:
    """Generate initial greeting message."""
    
    if user_name:
        return f"""Welcome back to VibeFlows, {user_name}! 🌊

I'm your AI assistant ready to help you build amazing marketing automation workflows.

I can help you create automations that connect tools like:
• Email marketing (Mailchimp, HubSpot, etc.) 
• CRM systems (Salesforce, Pipedrive)
• Social media (LinkedIn, Twitter, Instagram)
• Analytics (Google Analytics, Facebook Ads)
• And 1000+ other marketing tools!

What marketing workflow would you like to automate today?"""
    
    else:
        return """Welcome to VibeFlows! 🌊

I'm your AI assistant that turns plain English into powerful marketing automation.

I can help you create workflows that connect tools like:
• Email marketing (Mailchimp, HubSpot, etc.)
• CRM systems (Salesforce, Pipedrive) 
• Social media (LinkedIn, Twitter, Instagram)
• Analytics (Google Analytics, Facebook Ads)
• And 1000+ other marketing tools!

What's your name, and what marketing workflow would you like to automate?"""

def generate_understanding_summary(understanding_result: Dict[str, Any]) -> str:
    """Generate user-friendly summary of what was understood."""
    
    project_type = understanding_result.get('project_type', 'Unknown')
    summary = understanding_result.get('summary', 'Not specified')
    confidence = int(understanding_result.get('confidence', 0) * 100)
    requirements = understanding_result.get('requirements', [])
    
    response = f"""Perfect! Here's what I understood from your request: 📋

**Your Goal:** {summary}

**Project Type:** {project_type.replace('_', ' ').title()}

**Key Requirements:**"""
    
    if requirements:
        for req in requirements[:5]:  # Show top 5 requirements
            response += f"\n• {req}"
    else:
        response += "\n• (I'll help you define these as we go)"
    
    response += f"\n\n**My Confidence Level:** {confidence}% ✅"
    
    if confidence >= 80:
        response += "\n\nI have a clear understanding of what you need! Let me create a visual design of your workflow."
    elif confidence >= 60:
        response += "\n\nI have a good understanding, but I may need to ask a few clarifying questions to make sure I build exactly what you need."
    else:
        response += "\n\nI need to ask some questions to better understand your requirements."
    
    return response

def generate_clarification_questions(questions: List[str]) -> str:
    """Generate user-friendly clarification questions."""
    
    if not questions:
        return "I think I have enough information to proceed! Let me create your workflow design."
    
    response = "I need to ask a few quick questions to make sure I build exactly what you need: ❓\n"
    
    for i, question in enumerate(questions, 1):
        response += f"\n{i}. {question}"
    
    return response

def generate_design_intro() -> str:
    """Generate message before starting design phase."""
    
    return """Excellent! I now have everything I need to create your marketing automation. 🎨

Let me design a visual workflow that shows exactly how your automation will work. This will include:
• All the tools and platforms you'll connect
• The triggers that start your automation  
• The sequence of actions that will happen
• Decision points and conditional logic

Creating your workflow design now..."""

# Test function
def test_user_interface():
    """Test the user interface functions."""
    
    print("🧪 Testing User Interface Agent")
    print("=" * 40)
    
    # Test greeting
    print("1. Greeting:")
    print(generate_greeting("John"))
    print()
    
    # Test understanding summary
    print("2. Understanding Summary:")
    sample_understanding = {
        "project_type": "workflow",
        "summary": "Automate lead qualification and nurturing for B2B SaaS company",
        "confidence": 0.85,
        "requirements": ["lead scoring", "email automation", "CRM integration", "analytics tracking"]
    }
    print(generate_understanding_summary(sample_understanding))
    print()
    
    # Test clarification questions
    print("3. Clarification Questions:")
    sample_questions = [
        "Which CRM system are you currently using?",
        "What triggers should start the lead qualification process?",
        "How do you currently score your leads?"
    ]
    print(generate_clarification_questions(sample_questions))
    print()
    
    # Test design intro
    print("4. Design Introduction:")
    print(generate_design_intro())

if __name__ == "__main__":
    test_user_interface()