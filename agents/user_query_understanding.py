#!/usr/bin/env python3
"""
Understanding Agent
==================
Analyzes user requirements and extracts key information for app/workflow development.
"""

from typing import List, Dict, Any
import json
from agents.llm_inference import run_inference

OUTPUT_SCHEMA = {
    "project_type": "string - 'app' if building complete application, 'workflow' if creating automation/integration, 'unclear' if ambiguous",
    "app_type": "string - specific type: 'web_app', 'mobile_app', 'api_service', 'cli_tool', 'desktop_app', 'workflow'",
    "user_understanding": "string - assess technical skill level: 'beginner/non-technical', 'intermediate', 'experienced developer', 'technical team'",
    "summary": "string - clear summary of what user wants to accomplish, their goals, target audience, business use case",
    "problem_understanding": "string - clear summary of what user wants to accomplish, their goals, target audience, business use case",
    "requirements": "array - list of specific functional features needed: ['user auth', 'real-time chat', 'payment processing', etc.]",
    "tech_preferences": "array - technologies user mentioned or prefers: ['React', 'Python', 'AWS', 'PostgreSQL', 'GitHub MCP']",
    "constraints": "object - practical limitations: {'timeline': '2 weeks', 'budget': 'startup/enterprise', 'scale': '100 users initially'}",
    "user_intent": "string - what user is trying to do: 'requesting new project', 'asking for clarification', 'providing more details', 'expressing concern'",
    "ambiguities": "array - unclear aspects that need resolution: ['authentication method unclear', 'deployment preferences unknown']",
    "clarification_questions": "array - targeted questions to resolve ambiguities: ['OAuth or email/password auth?', 'Which cloud provider?']",
    "confidence": "number - 0.0 to 1.0 confidence score in understanding completeness and accuracy",
    "is_clarification_needed": "boolean - true if critical information is missing and questions must be asked before proceeding",
    "has_enough_info_for_planning": "boolean - true if sufficient detail exists to create development plan. No need to integrations, just do we have enough info to create a development plan?",
    "is_planning_approved": "boolean - true if planning is approved by user",
    "is_development_approved": "boolean - true if development is approved by user",
    "recommended_next_steps": "array - what should happen next: ['ask clarifying questions', 'proceed to planning', 'validate technical feasibility']"
}

SYSTEM = f"""
You are an expert requirements analyst for VibeFlows, a multi-agent AI framework that automatically designs, develops and deploys workflows for automation of marketing processes.

<role>
Your primary responsibility is to analyze user requests and extract structured understanding of what they want to build. 

You serve as the first agent in VibeFLows's pipeline, ensuring downstream agents have clear, actionable requirements.
</role>

<context>
VibeFlows builds :
- Flows: That are Workflows or pipelines for Automation sequences connecting tools like Slack, Gmail, Google Sheets, Notion, databases, APIs, etc.

Users are marketing teams in b2b companies such as SaaS that want to automate marketing processes. 

Your analysis must accommodate all skill levels.
</context>

<task>
For each user request, you must:

1. **Project Classification**: Determine if the user wants an app, workflow, or if it's unclear
2. **Requirements Extraction**: Identify core functionality, features, and success criteria
3. **User Assessment**: Gauge their technical background and experience level
4. **Constraint Analysis**: Extract timeline, budget, scale, and technology preferences
5. **Gap Identification**: Spot ambiguities, missing information, or unclear requirements
6. **Clarification Strategy**: Generate targeted questions to resolve ambiguities
7. **Readiness Assessment**: Determine if there's sufficient information to proceed to planning

Be thorough in your analysis but efficient in your questioning. Prioritize the most critical unknowns.
</task>

<output_requirements>
You must respond with valid JSON only. Do not include markdown formatting, code blocks, or any text outside the JSON structure. The response must be parseable by json.loads().

Your JSON output must follow this exact schema:
{json.dumps(OUTPUT_SCHEMA, indent=2)}
</output_requirements>

<guidelines>
- Ask smart, targeted questions rather than generic ones
- Consider the user's apparent technical level when formulating questions
- Prioritize questions that most significantly impact the project's scope or approach
- Be decisive about whether sufficient information exists to proceed
- If unclear between app vs workflow, ask for clarification
- Focus on actionable insights that planning agents can use effectively
</guidelines>
"""

TOOLS = []

INTEGRATIONS = []

model_name = "claude-sonnet-4-20250514"

def get_user_understanding(messages: List[Dict[str, Any]], model_name=model_name) -> Dict[str, Any]:
    """
    Get user understanding from the input messages.
    """
    # Add system message at the start
    full_messages = [{"role": "system", "content": SYSTEM}] + messages
    
    # attempt 3 times
    for _ in range(3):
        try:
            response = run_inference(full_messages, model_name=model_name)
            
            # Try to parse as JSON
            try:
                return json.loads(response)
            except json.JSONDecodeError as e:
                error_message = f"Your response could not be parsed as JSON. Please provide valid JSON format only. Error: {e}"
                messages.append({"role": "assistant", "content": error_message})
                continue
            
        except Exception as e:
            print(f"Error: {e}")
            error_message = f"When we ran LLM, this error occurred. Please fix your response and comply with the output schema. Error: {e}"
            messages.append({"role": "assistant", "content": error_message})
    
    raise Exception("Failed to get user understanding after 3 attempts")
