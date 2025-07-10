#!/usr/bin/env python3
"""
Agent Runner System
==================
Loads agent by agent_id from database, extracts all node functions and agent function, 
executes them in the global scope, and runs the agent.
Attaches node parameters to input data when calling node functions.
"""

import json
import os
import sys
from typing import Dict, Any
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

def load_agent_from_db(agent_id: str) -> Dict[str, Any]:
    """Load agent from MongoDB by agent_id."""
    try:
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client.vibeflows
        
        # Convert string ID to ObjectId
        try:
            object_id = ObjectId(agent_id)
        except:
            print(f"Error: Invalid agent_id format: {agent_id}")
            sys.exit(1)
            
        agent_spec = db.agents.find_one({'_id': object_id})
        if not agent_spec:
            print(f"Error: Agent with ID '{agent_id}' not found in database")
            sys.exit(1)
        return agent_spec
    except Exception as e:
        print(f"Error loading agent from database: {e}")
        sys.exit(1)

def load_all_integrations(globals_dict: Dict[str, Any]):
    """Load all integrations from database into the global scope."""
    try:
        # Ensure environment variables are loaded
        from dotenv import load_dotenv
        load_dotenv()
        
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client.vibeflows
        
        # Load all integrations
        integrations = db.integrations.find()
        for integration in integrations:
            integration_name = integration.get('name')
            integration_function = integration.get('function')
            
            if integration_name and integration_function:
                try:
                    # Execute the integration function in the global scope
                    exec(integration_function, globals_dict)
                    print(f"Loaded integration: {integration_name}")
                except Exception as e:
                    print(f"Warning: Failed to load integration '{integration_name}': {e}")
        
        client.close()
    except Exception as e:
        print(f"Error loading integrations: {e}")

def extract_and_execute_functions(agent_spec: Dict[str, Any], globals_dict: Dict[str, Any]):
    """Extract all node functions and agent function, execute them in global scope."""
    
    # First, load all integrations into the global scope
    load_all_integrations(globals_dict)
    
    # Store node parameters for later use
    node_parameters = {}
    
    # Extract and execute node functions
    if 'nodes' in agent_spec:
        for node in agent_spec['nodes']:
            node_name = node.get('name')
            node_function = node.get('function')
            node_params = node.get('parameters', {})
            
            if node_name and node_function:
                # Store parameters for this node
                node_parameters[node_name] = node_params
                print(f"  Parameters for {node_name}: {node_params}")
                
                # Execute the function in global scope
                try:
                    exec(node_function, globals_dict)
                    print(f"Loaded node function: {node_name}")
                except Exception as e:
                    print(f"Error executing node function '{node_name}': {e}")
                    sys.exit(1)
    
    # Extract and execute agent function
    agent_function = agent_spec.get('function')
    if agent_function:
        try:
            exec(agent_function, globals_dict)
            print(f"Loaded agent function: {agent_spec.get('name', 'unknown')}")
        except Exception as e:
            print(f"Error executing agent function: {e}")
            sys.exit(1)
    else:
        print("Error: No agent function found in specification")
        sys.exit(1)
    
    return node_parameters

def create_node_wrapper(original_function, node_params):
    """Create a wrapper function that merges node parameters with input data."""
    def wrapper(input_data):
        # Merge node parameters with input data
        merged_input = {**node_params, **input_data}
        # Debug: print what's being passed to the node
        print(f"Node input after merging parameters: {list(merged_input.keys())}")
        if 'integration_name' in merged_input:
            print(f"Integration name being used: {merged_input['integration_name']}")
        return original_function(merged_input)
    return wrapper

def wrap_node_functions(node_parameters: Dict[str, Dict], globals_dict: Dict[str, Any]):
    """Wrap node functions to automatically include their parameters."""
    for node_name, params in node_parameters.items():
        # Convert node name to function name (replace spaces with underscores, lowercase)
        func_name = node_name.lower().replace(' ', '_')
        if func_name in globals_dict:
            original_func = globals_dict[func_name]
            globals_dict[func_name] = create_node_wrapper(original_func, params)
            print(f"Wrapped node function: {func_name} (from {node_name}) with parameters")
        else:
            print(f"Warning: Function {func_name} (from node {node_name}) not found in globals")

def run_agent(agent_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to run an agent.
    
    Args:
        agent_id: MongoDB ObjectId of the agent
        input_data: Input data for the agent
        
    Returns:
        Agent execution result
    """
    
    print(f"Loading agent: {agent_id}")
    
    # Load agent from database
    agent_spec = load_agent_from_db(agent_id)
    agent_name = agent_spec.get('name', 'unknown')
    
    print(f"Agent loaded: {agent_name}")
    print(f"Description: {agent_spec.get('description', 'No description')}")
    
    # Prepare globals dictionary with necessary imports and environment
    # Make sure environment variables are accessible
    import os as os_module
    
    globals_dict = {
        '__builtins__': __builtins__,
        'os': os_module,
        'json': json,
        'sys': sys,
        'MongoClient': MongoClient,
        'ObjectId': ObjectId,
        # Add dotenv for nodes that need it
        'load_dotenv': load_dotenv
    }
    
    # Ensure the environment is loaded in the globals context
    globals_dict['os'].environ.update(os.environ)
    
    # Extract and execute all functions
    node_parameters = extract_and_execute_functions(agent_spec, globals_dict)
    
    # Wrap node functions with their parameters
    wrap_node_functions(node_parameters, globals_dict)
    
    # Get the agent function name - try to find it in globals
    agent_function_name = None
    
    # First try the agent name as-is
    if agent_name in globals_dict:
        agent_function_name = agent_name
    else:
        # Try converting to snake_case
        snake_case_name = agent_name.lower().replace(' & ', '_').replace(' ', '_')
        if snake_case_name in globals_dict:
            agent_function_name = snake_case_name
        else:
            # Look for any function that ends with '_agent'
            for key in globals_dict:
                if key.endswith('_agent') and callable(globals_dict[key]):
                    agent_function_name = key
                    break
    
    if not agent_function_name:
        print(f"Error: Agent function not found after execution")
        print(f"Available functions: {[k for k in globals_dict.keys() if callable(globals_dict.get(k)) and not k.startswith('_')]}")
        sys.exit(1)
    
    # Run the agent
    print(f"Running agent: {agent_name}")
    print(f"Input: {input_data}")
    
    try:
        result = globals_dict[agent_function_name](input_data)
        print(f"Agent completed successfully")
        return result
    except Exception as e:
        print(f"Error running agent: {e}")
        raise

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    if len(sys.argv) < 2:
        print("Usage: python agent_runner.py <agent_id> [input_json]")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    
    # Default test input
    if len(sys.argv) > 2:
        import json
        input_data = json.loads(sys.argv[2])
    else:
        # Default test data - generic format that can work for different agents
        input_data = {
            'topic': 'Introduction to Python Programming',
            'target_audience': 'beginners with no programming experience',
            'content_type': 'tutorial blog post',
            'brand_guidelines': {
                'tone': 'friendly and approachable',
                'style': 'conversational',
                'voice': 'educational'
            }
        }
    
    try:
        result = run_agent(agent_id, input_data)
        print("\nAgent Result:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Failed to run agent: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
