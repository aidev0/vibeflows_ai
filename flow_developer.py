from pymongo import MongoClient
from bson import ObjectId
import os
import json
import asyncio
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

client = MongoClient(os.getenv('MONGODB_URI'))
db = client.vibeflows

def flow_developer(input_data):
    """
    This function is used to develop a flow.
    """

    flow_id = input_data['flow_id']
    flow = db.flows.find_one({'_id': ObjectId(flow_id)})
    print(flow)

    new_flow = flow.copy()
    if not flow:
        raise Exception('Flow not found')
    
    from agent_maker import agent_developer
    
    agents_created = []
    agent_ids = []
    
    for node in flow['nodes']:
        if node['type'] == 'agent' and not node.get('agent_id'):
            requirements = str(node)
            agent_input = {'requirements': requirements}
            result = agent_developer(agent_input)
            agent_id = result['agent_id']
            
            # Update node with agent_id
            for i, n in enumerate(new_flow['nodes']):
                if n['id'] == node['id']:
                    new_flow['nodes'][i]['agent_id'] = agent_id
                    break
            
            agents_created.append(result)
            agent_ids.append(agent_id)
    
    # Update flow in database
    new_flow['status'] = 'developed'
    new_flow['agents_created_count'] = len(agent_ids)
    db.flows.replace_one({'_id': ObjectId(flow_id)}, new_flow)
    
    return {
        "status": "Flow developed",
        "agents_created": agents_created,
        "agent_ids": agent_ids,
        "development_complete": True
    }

async def flow_developer_streaming(input_data):
    """
    Develops a flow by generating agents for each node using TRUE MULTIPROCESSING.
    Streams updates as agents are created in separate processes.
    """
    flow_id = input_data['flow_id']
    flow = db.flows.find_one({'_id': ObjectId(flow_id)})
    if not flow:
        yield {"message": "❌ Flow not found", "type": "error"}
        return

    yield {"message": f"🔍 Found flow: {flow.get('name', 'Unnamed')}", "type": "status"}
    new_flow = flow.copy()
    
    agents_created = []
    agent_ids = []
    
    # Count agent nodes to process
    agent_nodes = [node for node in flow['nodes'] if node['type'] == 'agent' and not node.get('agent_id')]
    
    if not agent_nodes:
        yield {"message": "ℹ️ No agent nodes to process", "type": "info"}
        return

    yield {"message": f"🚀 Processing {len(agent_nodes)} agent nodes with MULTIPROCESSING...", "type": "status"}

    # Prepare data for multiprocessing
    node_data_list = [(node, i) for i, node in enumerate(agent_nodes)]
    
    # Determine number of processes (max 4 to avoid overwhelming the API)
    max_workers = min(4, len(agent_nodes), mp.cpu_count())
    yield {"message": f"⚡ Starting {max_workers} parallel processes...", "type": "parallel_start"}

    try:
        # Use ProcessPoolExecutor for true parallel processing
        loop = asyncio.get_event_loop()
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks to the process pool
            futures = [
                loop.run_in_executor(executor, create_agent_sync, node_data)
                for node_data in node_data_list
            ]
            
            yield {"message": f"📊 Submitted {len(futures)} agent creation jobs to process pool", "type": "status"}
            
            # Wait for completion with periodic updates
            completed = 0
            successful = 0
            failed = 0
            
            # Process results as they complete
            for future in asyncio.as_completed(futures):
                try:
                    result = await future
                    completed += 1
                    
                    # Stream the result message
                    yield {
                        "message": result['message'],
                        "type": "process_update",
                        "node_id": result['node']['id'],
                        "progress": f"{completed}/{len(futures)}"
                    }
                    
                    if result['success']:
                        successful += 1
                        agent_result = result['agent_result']
                        agent_id = agent_result.get('agent_id')
                        node = result['node']
                        
                        # Update node with agent_id
                        for j, n in enumerate(new_flow['nodes']):
                            if n['id'] == node['id']:
                                new_flow['nodes'][j]['agent_id'] = agent_id
                                break

                        agents_created.append(agent_result)
                        agent_ids.append(agent_id)
                        
                        yield {
                            "message": f"✅ [{completed}/{len(futures)}] Agent created: {agent_result.get('name', 'Unnamed')}",
                            "type": "agent_complete",
                            "node_id": node['id'],
                            "agent_id": agent_id
                        }
                    else:
                        failed += 1
                        yield {
                            "message": f"❌ [{completed}/{len(futures)}] Agent creation failed: {result.get('error', 'Unknown error')}",
                            "type": "agent_error",
                            "node_id": result['node']['id'],
                            "error": result.get('error')
                        }
                        
                    # Progress update
                    if completed % 2 == 0 or completed == len(futures):
                        yield {
                            "message": f"📈 Progress: {completed}/{len(futures)} complete (✅ {successful}, ❌ {failed})",
                            "type": "progress_update"
                        }
                        
                except Exception as e:
                    failed += 1
                    yield {
                        "message": f"❌ Process execution error: {str(e)}",
                        "type": "process_error",
                        "error": str(e)
                    }

    except Exception as e:
        yield {
            "message": f"❌ Multiprocessing setup error: {str(e)}",
            "type": "multiprocessing_error",
            "error": str(e)
        }
        return

    # Update flow in database
    try:
        new_flow['status'] = 'developed'
        new_flow['agents_created_count'] = len(agent_ids)
        db.flows.replace_one({'_id': ObjectId(flow_id)}, new_flow)
        
        yield {
            "message": f"🎉 MULTIPROCESSING COMPLETE! ✅ {successful} successful, ❌ {failed} failed in parallel processes",
            "type": "complete",
            "agents_created": successful,
            "agents_failed": failed,
            "total_nodes": len(agent_nodes),
            "agent_ids": agent_ids,
            "multiprocessing": True,
            "result": {
                "status": "Flow developed",
                "agents_created": agents_created,
                "agent_ids": agent_ids,
                "development_complete": True,
                "parallel_processing": True,
                "multiprocessing": True
            }
        }
        
    except Exception as e:
        yield {
            "message": f"❌ Error updating flow: {str(e)}",
            "type": "database_error",
            "error": str(e)
        }

def create_agent_sync(node_data):
    """Synchronous function to create a single agent - runs in separate process"""
    try:
        # Import here to avoid pickling issues
        from agent_maker import agent_developer
        
        node, node_index = node_data
        agent_input = {'requirements': str(node)}
        
        print(f"🔨 [Process {node_index+1}] Starting agent creation for {node.get('name', node['id'])}")
        
        # Create agent synchronously
        result = agent_developer(agent_input)
        
        return {
            'node': node,
            'node_index': node_index,
            'agent_result': result,
            'success': True,
            'message': f"✅ [Process {node_index+1}] Agent '{result.get('name', 'Unnamed')}' created successfully"
        }
        
    except Exception as e:
        return {
            'node': node,
            'node_index': node_index,
            'agent_result': None,
            'success': False,
            'error': str(e),
            'message': f"❌ [Process {node_index+1}] Failed: {str(e)}"
        }
