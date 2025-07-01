#!/usr/bin/env python3
"""
Task Graph Designer Agent
=========================
Creates task dependency graphs from user workflow requirements.
"""

from typing import Dict, Any, List
import json
from datetime import datetime, timezone
from pymongo import MongoClient
import os
from agents.llm_inference import run_inference

# Output schema definition
OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["name", "description", "nodes", "connections"],
    "properties": {
        "name": {
            "type": "string",
            "description": "Brief workflow name"
        },
        "description": {
            "type": "string", 
            "description": "2-3 sentence description of what this workflow accomplishes"
        },
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "name", "type", "description"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["trigger", "process", "condition", "action", "integration", "wait", "end"]
                    },
                    "description": {"type": "string"},
                    "conditions": {
                        "type": "array",
                        "description": "Only for condition nodes",
                        "items": {
                            "type": "object",
                            "required": ["expression", "output", "label"],
                            "properties": {
                                "expression": {"type": "string"},
                                "output": {"type": "string"},
                                "label": {"type": "string"}
                            }
                        }
                    }
                }
            }
        },
        "connections": {
            "type": "array",
            "items": {
                "type": "object", 
                "required": ["from", "to"],
                "properties": {
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "label": {"type": "string", "description": "Optional edge label for UI"}
                }
            }
        }
    }
}

SYSTEM = """
You are the Task Graph Designer agent for VibeFlows, specialized in creating task dependency graphs from marketing automation workflows.

Pay attention to the context provided. If there's a previous understanding or design, make changes that build on that context rather than starting from scratch.

<role>
Your job is to convert user workflow requirements into a structured task dependency graph that shows what needs to be done and in what order.
</role>

<task>
Based on the user's requirements analysis, create a task dependency graph that includes:
1. Individual tasks/goals that need to be accomplished
2. Clear dependencies between tasks (A must happen before B)
3. Logical grouping of related tasks
4. Actionable task descriptions
5. Integration setup tasks
6. Data flow and processing tasks
</task>

<design_structure>
The output should be a JSON object with this exact structure:
{
  "name": "Brief workflow name",
  "description": "2-3 sentence description of what this workflow accomplishes",
  "nodes": [
    {
      "id": "unique_task_id",
      "name": "Task Name", 
      "description": "What this task does",
      "type": "trigger|process|condition|action|integration|wait|end",
      "conditions": [  // Only for condition nodes
        {
          "expression": "condition logic",
          "output": "output_name",
          "label": "Human readable label"
        }
      ]
    }
  ],
  "connections": [
    {
      "from": "task_id_1",
      "to": "task_id_2", 
      "label": "optional edge label for UI"
    }
  ]
}
</design_structure>

<task_types>
- trigger: Starting points (form submission, email received, time-based)
- process: Data manipulation, enrichment, scoring, transformation  
- condition: Conditional routing nodes with switch-like logic and multiple outputs
- action: Outbound actions (send email, create task, notifications)
- integration: External system connections (CRM sync, webhook calls)
- wait: Time delays or condition waits
- end: Workflow termination points
</task_types>

<guidelines>
- Use clear, actionable task names
- Keep task descriptions concise but specific
- Include all necessary setup/integration tasks
- Show logical dependencies clearly through connections
- Create separate condition nodes for all conditional logic
- For condition nodes, include conditions array with expression/output/label structure
- In condition nodes, the "output" field should reference actual target node IDs
- Always include a "default" condition as fallback in condition nodes
- Connect FROM condition nodes TO target nodes using the output field that matches the node ID
- All other node types connect normally without output field
- Group related tasks sensibly
- Use descriptive IDs (snake_case)
</guidelines>

<output_format>
Respond with ONLY the JSON object. No explanations, no markdown code blocks, just the raw JSON that can be directly parsed.
</output_format>
"""

def get_required_fields(schema: Dict[str, Any], path: str = "") -> List[str]:
    """
    Extract required fields from a JSON schema recursively.
    
    Args:
        schema: JSON schema dictionary
        path: Current path in schema (for nested objects)
        
    Returns:
        List of required field paths
    """
    required_fields = []
    
    if "required" in schema:
        for field in schema["required"]:
            field_path = f"{path}.{field}" if path else field
            required_fields.append(field_path)
    
    if "properties" in schema:
        for prop_name, prop_schema in schema["properties"].items():
            prop_path = f"{path}.{prop_name}" if path else prop_name
            if prop_schema.get("type") == "object":
                required_fields.extend(get_required_fields(prop_schema, prop_path))
            elif prop_schema.get("type") == "array" and "items" in prop_schema:
                if prop_schema["items"].get("type") == "object":
                    item_path = f"{prop_path}[]"
                    required_fields.extend(get_required_fields(prop_schema["items"], item_path))
    
    return required_fields

def create_task_graph(messages: List[Dict[str, str]], model_name="claude-sonnet-4-20250514", max_retries=3) -> Dict[str, Any]:
    """
    Create a task dependency graph from conversation messages with retry logic.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content' keys
        model_name: LLM model to use
        max_retries: Maximum number of retry attempts
        
    Returns:
        Dictionary with task graph structure
    """
    
    # Start with system message and provided messages
    conversation = [{"role": "system", "content": SYSTEM}] + messages
    conversation.append({"role": "user", "content": "Create a task dependency graph based on the conversation above."})
    
    errors_encountered = []
    
    for attempt in range(max_retries):
        try:
            response = run_inference(conversation, model_name=model_name)
            # Parse the JSON response
            design = json.loads(response.strip())
            
            # Validate structure using schema
            required_keys = OUTPUT_SCHEMA["required"]
            if not all(key in design for key in required_keys):
                raise ValueError("Invalid design structure - missing required keys: " + 
                               ", ".join(k for k in required_keys if k not in design))
            
            # Validate condition nodes have conditions and valid outputs
            node_ids = {node["id"] for node in design["nodes"]}
            for node in design["nodes"]:
                if node.get("type") == "condition":
                    if "conditions" not in node:
                        raise ValueError(f"Condition node {node['id']} missing conditions")
                    # Check that condition outputs reference valid node IDs
                    for condition in node["conditions"]:
                        output_id = condition.get("output")
                        if output_id and output_id not in node_ids:
                            raise ValueError(f"Condition node {node['id']} references non-existent node: {output_id}")
            
            # Validate connections reference valid nodes
            for conn in design["connections"]:
                if conn["from"] not in node_ids:
                    raise ValueError(f"Connection references non-existent 'from' node: {conn['from']}")
                if conn["to"] not in node_ids:
                    raise ValueError(f"Connection references non-existent 'to' node: {conn['to']}")
            
            # Run additional validation checks
            validation_warnings = validate_task_graph(design)
            
            # If we get here, validation passed
            if errors_encountered:
                design["retry_info"] = {
                    "attempts": attempt + 1,
                    "errors_fixed": errors_encountered
                }
            
            # Add validation warnings if any
            if validation_warnings:
                design["validation_warnings"] = validation_warnings
            
            return design
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON decode error: {str(e)}"
            errors_encountered.append(error_msg)
            
            if attempt < max_retries - 1:
                # Add error feedback to conversation for next attempt
                conversation.append({
                    "role": "user", 
                    "content": f"Error in attempt {attempt + 1}: {error_msg}. Please fix the JSON format and try again."
                })
            
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            errors_encountered.append(error_msg)
            
            if attempt < max_retries - 1:
                # Add error feedback to conversation for next attempt
                conversation.append({
                    "role": "user",
                    "content": f"Error in attempt {attempt + 1}: {error_msg}. Please fix this issue and regenerate the task graph."
                })
    
    # If all retries failed, return error response
    return {
        "name": "Error",
        "description": "Failed to create valid task graph after multiple attempts",
        "nodes": [],
        "connections": [],
        "error": "Max retries exceeded",
        "errors_encountered": errors_encountered
    }

def validate_task_graph(design: Dict[str, Any]) -> List[str]:
    """
    Validate the task graph for common issues.
    
    Args:
        design: Task graph dictionary
        
    Returns:
        List of validation warnings/errors
    """
    warnings = []
    
    if not design.get("nodes"):
        warnings.append("No tasks defined")
        return warnings
    
    # Check for orphaned nodes
    node_ids = {node["id"] for node in design["nodes"]}
    connected_nodes = set()
    
    for conn in design.get("connections", []):
        if conn["from"] not in node_ids:
            warnings.append(f"Connection references unknown node: {conn['from']}")
        if conn["to"] not in node_ids:
            warnings.append(f"Connection references unknown node: {conn['to']}")
        connected_nodes.add(conn["from"])
        connected_nodes.add(conn["to"])
    
    # Check for condition nodes with invalid outputs
    node_ids = {node["id"] for node in design["nodes"]}
    for node in design["nodes"]:
        if node.get("type") == "condition":
            if "conditions" not in node or not node["conditions"]:
                warnings.append(f"Condition node {node['id']} has no conditions")
            else:
                # Check if condition outputs reference valid node IDs
                for condition in node["conditions"]:
                    output_id = condition.get("output")
                    if output_id and output_id not in node_ids:
                        warnings.append(f"Condition node {node['id']} references non-existent node: {output_id}")
                
                # Check if condition outputs are used in connections
                outputs = {cond.get("output") for cond in node["conditions"] if cond.get("output")}
                used_outputs = {conn.get("output") for conn in design.get("connections", []) 
                              if conn["from"] == node["id"] and conn.get("output")}
                unused = outputs - used_outputs
                if unused:
                    warnings.append(f"Condition node {node['id']} has unused outputs: {unused}")
    
    orphaned = node_ids - connected_nodes
    if orphaned and len(design["nodes"]) > 1:
        warnings.append(f"Orphaned nodes (no connections): {', '.join(orphaned)}")
    
    # Check for duplicate node IDs
    ids = [node["id"] for node in design["nodes"]]
    if len(ids) != len(set(ids)):
        warnings.append("Duplicate node IDs found")
    
    return warnings

def generate_task_summary(design: Dict[str, Any], model_name="claude-sonnet-4-20250514") -> str:
    """
    Generate a concise summary of the task graph.
    
    Args:
        design: Task graph dictionary
        model_name: LLM model to use
        
    Returns:
        Task summary string
    """
    
    summary_prompt = f"""
Based on this task dependency graph:

{json.dumps(design, indent=2)}

Write a brief, executive summary (2-3 sentences) that explains:
1. What this workflow accomplishes
2. Key tasks involved
3. Expected outcome/benefit

Focus on business value. Use clear, professional language.
Respond with ONLY the summary text.
"""
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant that creates concise business summaries of marketing automation workflows."},
        {"role": "user", "content": summary_prompt}
    ]
    
    try:
        summary = run_inference(messages, model_name=model_name)
        return summary.strip()
    except Exception as e:
        return f"Error generating summary: {str(e)}"

def get_task_execution_order(design: Dict[str, Any]) -> List[List[str]]:
    """
    Determine the execution order of tasks based on dependencies.
    
    Args:
        design: Task graph dictionary
        
    Returns:
        List of lists, where each inner list contains tasks that can run in parallel
    """
    from collections import defaultdict, deque
    
    # Build dependency graph
    dependencies = defaultdict(set)  # task -> set of prerequisites
    dependents = defaultdict(set)    # task -> set of tasks that depend on it
    
    all_tasks = {node["id"] for node in design["nodes"]}
    
    for conn in design.get("connections", []):
        dependencies[conn["to"]].add(conn["from"])
        dependents[conn["from"]].add(conn["to"])
    
    # Topological sort to find execution order
    execution_order = []
    remaining_tasks = all_tasks.copy()
    
    while remaining_tasks:
        # Find tasks with no remaining dependencies
        ready_tasks = [task for task in remaining_tasks 
                      if not dependencies[task].intersection(remaining_tasks)]
        
        if not ready_tasks:
            # Circular dependency detected
            execution_order.append(list(remaining_tasks))
            break
            
        execution_order.append(ready_tasks)
        remaining_tasks -= set(ready_tasks)
    
    return execution_order

def get_db_connection():
    """Get database connection"""
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    database_name = os.getenv("MONGODB_DATABASE", "vibeflows")
    client = MongoClient(mongo_uri)
    db = client[database_name]
    return db

def save_design_to_db(design: Dict[str, Any]) -> str:
    """
    Save design to database collection 'designs'
    
    Args:
        design: Task graph design dictionary
        
    Returns:
        Document ID (string)
    """
    db = get_db_connection()
    designs_collection = db.designs
    
    # Prepare document for storage
    design_document = {
        "name": design.get("name", "Untitled Workflow"),
        "description": design.get("description", ""),
        "nodes": design.get("nodes", []),  # Store the full design data
        "connections": design.get("connections", []),  # Store the full design data
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "version": 1,
        "status": "active"
    }
    
    # Add validation info if present
    if "validation_warnings" in design:
        design_document["validation_warnings"] = design["validation_warnings"]
    
    if "retry_info" in design:
        design_document["retry_info"] = design["retry_info"]
    
    try:
        # Insert into database
        result = designs_collection.insert_one(design_document)
        doc_id = str(result.inserted_id)
        print(f"Design saved with ID: {doc_id}")
        return doc_id
    except Exception as e:
        print(f"Error saving design to database: {e}")
        raise

def create_and_save_task_graph(messages: List[Dict[str, str]], 
                              model_name: str = "claude-sonnet-4-20250514") -> Dict[str, Any]:
    """
    Create task graph and automatically save to database
    
    Args:
        messages: User conversation messages
        model_name: LLM model to use
        
    Returns:
        Design with database document ID included
    """

    message = {}
    # Create the design
    design = create_task_graph(messages, model_name)
    print("design is here:")
    print(design)

    summary = generate_task_summary(design)
    print("summary is here:")
    print(summary)

    message["text"] = summary
    message["sender"] = "ai"
    message["type"] = "workflow_designer_response_json"
    message["timestamp"] = datetime.now()
    
    # Save to database if creation was successful
    if "error" not in design:
        try:
            doc_id = save_design_to_db(design)
            design["_id"] = doc_id
            design["saved_to_db"] = True
        except Exception as e:
            print(f"Failed to save design to database: {e}")
            design["save_error"] = str(e)
            design["saved_to_db"] = False
    
    message["json"] = design
    return message