import anthropic
import json
import os
from typing import Dict, Any

def check_edge_condition(condition: str, output_data: Dict[str, Any]) -> bool:
    """
    Check if edge condition is met using LLM evaluation ONLY.
    
    Args:
        condition: The condition string from the edge definition
        output_data: The output data from the previous node
        
    Returns:
        bool: True if condition is met, False otherwise
    """
    
    if not condition or condition.strip() == "":
        return True  # Empty condition always passes
    
    SYSTEM = """
You are a flow condition evaluator. 
You determine if edge conditions are satisfied based on node output data.

Evaluate the given condition against the provided output data.
Return ONLY true or false (boolean).

Common condition patterns:
- output.action_type === 'create_flow' 
- output.action_type === 'run_flow'
- output.action_type === 'respond'
- output.needs_clarification === true
- output.confidence > 0.8
- Complex conditions with || (OR) and && (AND)

Be precise and literal in your evaluation.
"""

    try:
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        messages = [
            {"role": "user", "content": f"Condition: {condition}\n\nOutput Data: {json.dumps(output_data, indent=2)}\n\nEvaluate if the condition is met. Return only true or false."}
        ]
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            system=SYSTEM,
            messages=messages
        )
        
        result_text = response.content[0].text.strip().lower()
        
        # Parse boolean response
        if result_text == "true":
            return True
        elif result_text == "false":
            return False
        else:
            # Try to parse as JSON boolean
            try:
                return json.loads(result_text)
            except:
                print(f"Warning: Could not parse LLM condition result: {result_text}")
                return False  # Default to false if unparseable
                
    except Exception as e:
        print(f"Error in LLM condition evaluation: {e}")
        return False  # Default to false on error

def get_next_node_by_conditions(edges: list, current_node_id: str, output_data: Dict[str, Any]) -> str:
    """
    Determine the next node based on edge conditions using LLM evaluation.
    
    Args:
        edges: List of edge definitions from the flow
        current_node_id: ID of the current node
        output_data: Output data from the current node
        
    Returns:
        str: ID of the next node to execute, or None if no valid path
    """
    
    valid_edges = [edge for edge in edges if edge.get("source") == current_node_id]
    
    for edge in valid_edges:
        condition = edge.get("condition", "")
        
        if check_edge_condition(condition, output_data):
            return edge.get("target")
    
    # If no conditions match, return None
    return None 