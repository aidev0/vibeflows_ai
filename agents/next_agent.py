#!/usr/bin/env python3
"""
Next Agent Router
=================
Minimal router that uses LLM to evaluate flow conditions and determine next agent.
"""

from typing import Dict, Any, List, Optional
import json
from agents.llm_inference import run_inference

def determine_next_agent(
    flow_conditions: List[Dict[str, Any]],
    available_agents: List[str],
    context: Dict[str, Any],
    model_name: str = "claude-sonnet-4-20250514"
) -> Dict[str, Any]:
    """
    Determine the next agent using LLM to evaluate flow conditions.
    
    Args:
        flow_conditions: List of condition dictionaries from flow definition
        available_agents: List of available agent names for validation
        context: Current execution context with all variables
        model_name: LLM model to use
        
    Returns:
        Dict with next_agent, reason, and matched_condition
    """
    
    # Build system prompt
    system_prompt = build_system_prompt(flow_conditions, available_agents)
    
    # Build context description
    context_description = build_context_description(context)
    
    # Create messages
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context_description}
    ]
    
    try:
        response = run_inference(messages, model_name)
        
        # Clean response of markdown code blocks
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
            
        result = json.loads(response)
        
        # Validate response
        if "next_agent" not in result:
            raise ValueError("Missing next_agent in response")
        
        # Validate agent is available
        next_agent = result["next_agent"]
        if next_agent not in available_agents and next_agent != "STOP":
            print(f"Warning: Invalid agent '{next_agent}', using fallback")
            return {
                "next_agent": available_agents[0] if available_agents else "STOP",
                "reason": f"Invalid agent '{next_agent}', using fallback",
                "matched_condition": None
            }
            
        return result
        
    except Exception as e:
        print(f"Error in LLM routing: {e}")
        # Return fallback with first available agent
        fallback_agent = available_agents[0] if available_agents else "STOP"
        return {
            "next_agent": fallback_agent,
            "reason": f"LLM routing failed: {e}",
            "matched_condition": None
        }

def build_system_prompt(flow_conditions: List[Dict[str, Any]], available_agents: List[str]) -> str:
    """
    Build system prompt from flow conditions and available agents.
    
    Args:
        flow_conditions: List of condition dictionaries
        available_agents: List of available agent names
        
    Returns:
        System prompt string
    """
    
    prompt = """You are a flow router. Your job is to evaluate conditions and determine the next agent.

<available_agents>
"""
    
    # Add available agents
    for agent in available_agents:
        prompt += f"- {agent}\n"
    
    prompt += "- STOP (to end execution)\n"
    prompt += """</available_agents>

<task>
Evaluate the provided conditions in order and return the first matching condition's next_agent.
The next_agent MUST be one of the available agents listed above or "STOP".
</task>

<conditions>
"""
    
    for i, condition in enumerate(flow_conditions, 1):
        condition_expr = condition.get('condition', 'true')
        next_node = condition.get('next_node', 'unknown')
        description = condition.get('description', f'Condition {i}')
        
        prompt += f"""
{i}. {description}
   Condition: {condition_expr}
   Next Agent: {next_node}
"""
    
    prompt += """
</conditions>

<evaluation_rules>
- Evaluate conditions in the exact order provided
- Return the FIRST condition that evaluates to true
- Use the context variables provided by the user
- The next_agent MUST be from the available agents list
- Be precise in your evaluation
</evaluation_rules>

<output_format>
Respond with JSON only:
{
  "next_agent": "agent_name_from_available_list_or_STOP",
  "reason": "brief explanation of which condition matched",
  "matched_condition": "the condition expression that matched"
}
</output_format>
"""
    
    return prompt

def build_context_description(context: Dict[str, Any]) -> str:
    """
    Build context description for the LLM.
    
    Args:
        context: Context dictionary
        
    Returns:
        Context description string
    """
    
    description = "Current context for condition evaluation:\n\n"
    
    # Add each context variable
    for key, value in context.items():
        if isinstance(value, dict):
            description += f"{key}:\n"
            for subkey, subvalue in value.items():
                description += f"  {subkey}: {subvalue}\n"
        else:
            description += f"{key}: {value}\n"
    
    description += "\nEvaluate the conditions against this context and return the next agent."
    
    return description

def build_evaluation_context(**kwargs) -> Dict[str, Any]:
    """
    Build evaluation context from keyword arguments.
    
    Returns:
        Context dictionary for condition evaluation
    """
    return kwargs
