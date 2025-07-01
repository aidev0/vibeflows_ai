import anthropic
import json
import os
from typing import Dict, Any
from pymongo import MongoClient

# Database connection
client = MongoClient(os.getenv('MONGODB_URI'))
db = client.vibeflows

def response_generator(input_data: Dict[str, Any]) -> str:
    """
    Generate natural language responses based on actions taken and results
    """
    user_query = input_data.get('user_query', '')
    action_taken = input_data.get('action_taken', 'processed')
    results = input_data.get('results', {})
    conversation_history = input_data.get('conversation_history', [])
    
    try:
        anthropic_client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        # Build context for the LLM
        context = f"""
User Query: {user_query}
Action Taken: {action_taken}
Results: {json.dumps(results, indent=2)}
"""
        
        # Add conversation history if available
        if conversation_history:
            recent_messages = conversation_history[-3:]  # Last 3 messages
            context += f"\nRecent Conversation:\n{json.dumps(recent_messages, indent=2)}"
        
        system_prompt = """
You are VibeFlows AI assistant. Generate CONCISE, BRIEF responses (1-2 sentences max).

Response Guidelines:
- For flow_created: If n8n_workflow_url exists, include it: "✅ Created [FlowName]. N8N: [URL]"
- For flow_created without URL: "✅ Created [FlowName]. Ready to run!"
- For flow_executed: "✅ Executed successfully. Status: [status]"  
- For no_flow_found: "❌ No flows found. Create one?"
- For errors: "❌ [brief issue]. [quick fix suggestion]"
- For clarification_needed: Ask the specific clarification questions provided
- For general: Brief, helpful guidance toward automation

IMPORTANT: If results contain n8n_workflow_url, always include it in your response.
Be direct, actionable, and under 20 words when possible.
Use emojis minimally but effectively.

For clarification requests:
- Ask the specific questions from clarification_questions array
- Be concise but clear about what information is needed
- Guide user toward providing actionable workflow details
"""
        
        messages = [
            {
                "role": "user", 
                "content": f"Generate a natural response for this workflow interaction:\n\n{context}"
            }
        ]
        
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=system_prompt,
            messages=messages
        )
        
        return response.content[0].text
        
    except Exception as e:
        print(f"❌ Error in response_generator: {str(e)}")
        raise 