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

def extract_and_execute_functions(agent_spec: Dict[str, Any], globals_dict: Dict[str, Any]):
    """Extract all node functions and agent function, execute them in global scope."""
    
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
        return original_function(merged_input)
    return wrapper

def wrap_node_functions(node_parameters: Dict[str, Dict], globals_dict: Dict[str, Any]):
    """Wrap node functions to automatically include their parameters."""
    for node_name, params in node_parameters.items():
        if node_name in globals_dict:
            original_func = globals_dict[node_name]
            globals_dict[node_name] = create_node_wrapper(original_func, params)
            print(f"Wrapped node function: {node_name} with parameters")

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
    
    # Prepare globals dictionary
    globals_dict = globals().copy()
    
    # Extract and execute all functions
    node_parameters = extract_and_execute_functions(agent_spec, globals_dict)
    
    # Wrap node functions with their parameters
    wrap_node_functions(node_parameters, globals_dict)
    
    # Get the agent function name (assumes it matches the agent name)
    agent_function_name = agent_name
    
    if agent_function_name not in globals_dict:
        print(f"Error: Agent function '{agent_function_name}' not found after execution")
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
