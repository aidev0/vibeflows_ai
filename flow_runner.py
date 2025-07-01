from pymongo import MongoClient
from bson import ObjectId
import os
from edge_condition_checker import get_next_node_by_conditions

client = MongoClient(os.getenv('MONGODB_URI'))
db = client.vibeflows

def flow_runner(input_data):
    """
    Run a flow by following the edges and using edge_condition_checker to validate conditions.
    """
    flow_id = input_data['flow_id']
    flow = db.flows.find_one({'_id': ObjectId(flow_id)})
    user_input_data = input_data.get('input_data', {})
    
    if not flow:
        raise Exception('Flow not found')
    
    # Create a run record
    run_record = {
        **flow,
        'input_data': user_input_data,
        'status': 'running',
        'flow_id': flow_id,
        'execution_log': []
    }
    run_id = db.runs.insert_one(run_record).inserted_id
    
    # Find entry point node
    current_node_id = None
    nodes = flow.get('nodes', [])
    edges = flow.get('edges', [])
    
    # Look for entry_point field first
    if 'entry_point' in flow:
        current_node_id = flow['entry_point']
    else:
        # Find node with no incoming edges (start node)
        target_nodes = {edge.get('target') for edge in edges}
        for node in nodes:
            if node['id'] not in target_nodes:
                current_node_id = node['id']
                break
    
    if not current_node_id:
        # Fallback to first node
        current_node_id = nodes[0]['id'] if nodes else None
    
    if not current_node_id:
        raise Exception('No entry point found in flow')
    
    # Track execution
    current_data = user_input_data
    max_iterations = 20  # Prevent infinite loops
    iteration = 0
    
    while current_node_id and iteration < max_iterations:
        iteration += 1
        
        # Find current node
        current_node = None
        for node in nodes:
            if node['id'] == current_node_id:
                current_node = node
                break
        
        if not current_node:
            print(f"Node {current_node_id} not found")
            break
        
        print(f"🔄 Executing node: {current_node_id} ({current_node.get('name', 'Unnamed')})")
        
        # Execute the node
        try:
            node_output = execute_node(current_node, current_data)
            current_data = node_output
            
            # Log execution
            execution_entry = {
                'node_id': current_node_id,
                'node_name': current_node.get('name', 'Unnamed'),
                'input_data': current_data,
                'output_data': node_output,
                'status': 'success',
                'iteration': iteration
            }
            
            # Update run record
            db.runs.update_one(
                {'_id': run_id},
                {
                    '$push': {'execution_log': execution_entry},
                    '$set': {'current_data': current_data}
                }
            )
            
        except Exception as e:
            print(f"❌ Error executing node {current_node_id}: {str(e)}")
            
            # Log error
            execution_entry = {
                'node_id': current_node_id,
                'node_name': current_node.get('name', 'Unnamed'),
                'input_data': current_data,
                'error': str(e),
                'status': 'failed',
                'iteration': iteration
            }
            
            db.runs.update_one(
                {'_id': run_id},
                {
                    '$push': {'execution_log': execution_entry},
                    '$set': {'status': 'failed', 'error': str(e)}
                }
            )
            
            return {
                'status': 'failed',
                'error': str(e),
                'flow_id': flow_id,
                'run_id': str(run_id),
                'last_node': current_node_id
            }
        
        # Find next node using edge conditions
        next_node_id = get_next_node_by_conditions(edges, current_node_id, current_data)
        
        if next_node_id:
            print(f"➡️  Next node: {next_node_id}")
            current_node_id = next_node_id
        else:
            print("🏁 No more valid paths, flow complete")
            break
    
    # Update final status
    final_status = 'completed' if iteration < max_iterations else 'timeout'
    db.runs.update_one(
        {'_id': run_id},
        {'$set': {'status': final_status, 'final_data': current_data}}
    )
    
    return {
        'status': final_status,
        'flow_id': flow_id,
        'run_id': str(run_id),
        'final_data': current_data,
        'iterations': iteration
    }

def execute_node(node, input_data):
    """
    Execute a single node based on its type.
    """
    node_type = node.get('type')
    
    if node_type == 'agent':
        return execute_agent_node(node, input_data)
    elif node_type == 'flow':
        return run_flow_node(node, input_data)
    else:
        # For other node types, just pass through the data
        return input_data

def execute_agent_node(node, input_data):
    """
    Execute an agent node.
    """
    agent_id = node.get('agent_id')
    if not agent_id:
        raise Exception(f"Agent node {node['id']} missing agent_id")
    
    from agent_runner import run_agent
    result = run_agent(agent_id, input_data)
    return result

def run_flow_node(node, input_data):
    """
    Execute a nested flow node.
    """
    nested_flow_id = node.get('flow_id')
    if not nested_flow_id:
        raise Exception(f"Flow node {node['id']} missing flow_id")
    
    nested_input = {
        'flow_id': nested_flow_id,
        'input_data': input_data
    }
    result = flow_runner(nested_input)
    return result.get('final_data', input_data)