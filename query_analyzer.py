def query_analyzer(input_data):
    user_query = input_data['user_query']
    conversation_history = input_data.get('conversation_history', [])

    SYSTEM = """
You are an automation AI query analyzer for VibeFlows. 
You analyze user queries to determine their intent and route them to the appropriate system components.

Your primary goal is to classify user queries into these ATOMIC ACTIONS:

1. **create_flow** - User wants to build new automation workflows, campaigns, or sequences
   Examples: "create email sequence", "build lead generation workflow", "set up automated campaigns"

2. **run_flow** - User wants to run/trigger existing workflows or get execution results  
   Examples: "run my email campaign", "execute lead gen flow", "start the workflow", "trigger automation"

3. **respond** - User needs information, help, explanations, or general assistance
   Examples: "what can you do?", "explain workflows", "how does this work?", "show me features"

ANALYSIS REQUIREMENTS:
- Extract specific business requirements (goals, audience, triggers, tools, etc.)
- Determine confidence level (0.0 to 1.0)
- Identify if clarification is needed for incomplete requirements
- Map intent to the correct action_type

BUSINESS CONTEXT EXTRACTION:
For create_flow requests, extract:
- Business goal/objective
- Target audience/personas  
- Trigger events/conditions
- Desired outcomes/conversions
- Preferred tools/platforms
- Timeline constraints

For run_flow requests, extract:
- Which flow/workflow to run
- Input parameters/data
- Execution context

CLARIFICATION LOGIC:
Set needs_clarification = true when:
- Requirements are vague or incomplete
- Missing critical information for flow creation
- Ambiguous intent between multiple actions

return json of this format:
{
  "intent": "string - clear description of what user wants",
  "action_type": "create_flow|run_flow|respond",
   "flow_id": "string - if executing existing flow" -- don't make this up, it should be the id of the flow provided by the user.
  "requirements": {
    "goal": "string - business objective",
    "audience": "string - target audience", 
    "trigger": "string - what starts the automation",
    "outcome": "string - desired result",
    "platforms": ["array of preferred tools/platforms"],
    "timeline": "string - any time constraints",
    "additional_context": "object - any other relevant details"
  },
  "confidence": "number between 0.0-1.0",
  "needs_clarification": "boolean",
  "clarification_questions": ["array of specific questions to ask"],
  "missing_info": ["array of missing required information"]
}
"""

    import anthropic
    import json
    import os
    
    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    
    # Build conversation context
    context = ""
    if conversation_history:
        context = f"Conversation History: {json.dumps(conversation_history[-3:])}\n\n"
    
    messages = [
        {"role": "user", "content": f"{context}Current User Query: {user_query}\n\nAnalyze this query and classify the atomic action."}
    ]
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        system=SYSTEM,
        messages=messages
    )
    
    try:
        # Clean response of markdown code blocks
        response_text = response.content[0].text
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
            
        result = json.loads(response_text)
        
        # Validate action_type
        valid_actions = ["create_flow", "run_flow", "respond"]
        if result.get("action_type") not in valid_actions:
            result["action_type"] = "respond"  # Default fallback
            
        return result
        
    except json.JSONDecodeError as e:
        return {
            "intent": "unclear_request",
            "action_type": "respond", 
            "requirements": {
                "goal": "Unable to parse user request",
                "additional_context": {"parse_error": str(e)}
            },
            "confidence": 0.1,
            "needs_clarification": True,
            "clarification_questions": ["Could you please rephrase your request more clearly?"],
            "missing_info": ["clear intent and requirements"]
        }