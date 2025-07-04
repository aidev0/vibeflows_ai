#!/usr/bin/env python3
"""
Debug script to understand why agent_ids are not being assigned to flow nodes
"""

import os
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Connect to MongoDB
client = MongoClient(os.getenv("MONGODB_URI"))
db = client.vibeflows

def debug_flow_node_structure():
    """Debug the flow node structure to understand the issue"""
    
    print("🔍 Debugging flow node structure...")
    print("=" * 60)
    
    # Get recent developed flows to compare
    recent_flows = list(db.flows.find({"status": "developed"}).sort("created_at", -1).limit(5))
    
    if not recent_flows:
        print("❌ No developed flows found")
        return
    
    print(f"📊 Analyzing {len(recent_flows)} recent developed flows...\n")
    
    for i, developed_flow in enumerate(recent_flows):
        flow_id = str(developed_flow["_id"])
        flow_name = developed_flow.get("name", "Unnamed Flow")
        created_at = developed_flow.get("created_at", "unknown")
        
        print(f"📋 Flow {i+1}: {flow_name}")
        print(f"   ID: {flow_id}")
        print(f"   Created: {created_at}")
        print(f"   Status: {developed_flow.get('status')}")
        print(f"   Agents Created Count: {developed_flow.get('agents_created_count', 0)}")
        
        # Analyze the nodes structure
        nodes = developed_flow.get("nodes", [])
        agent_nodes = [node for node in nodes if node.get("type") == "agent"]
        nodes_with_agent_id = [node for node in agent_nodes if node.get("agent_id")]
        
        print(f"   Total nodes: {len(nodes)}")
        print(f"   Agent nodes: {len(agent_nodes)}")
        print(f"   Nodes with agent_id: {len(nodes_with_agent_id)}")
        
        if len(agent_nodes) > 0:
            success_rate = (len(nodes_with_agent_id) / len(agent_nodes)) * 100
            status = "✅" if success_rate == 100 else "❌"
            print(f"   {status} Agent ID assignment rate: {success_rate:.1f}%")
        
        print("-" * 40)
    
    # Pick the first flow for detailed analysis
    developed_flow = recent_flows[0]
    flow_id = str(developed_flow["_id"])
    flow_name = developed_flow.get("name", "Unnamed Flow")
    
    print(f"\n🔍 Detailed analysis of: {flow_name}")
    print(f"   ID: {flow_id}")
    
    # Analyze the nodes structure
    nodes = developed_flow.get("nodes", [])
    print(f"\n📊 Flow has {len(nodes)} total nodes")
    
    for i, node in enumerate(nodes):
        print(f"\nNode {i+1}:")
        print(f"   Type: {node.get('type', 'unknown')}")
        print(f"   ID: {node.get('id', 'unknown')}")
        print(f"   Name: {node.get('name', 'Unnamed')}")
        
        # Check all keys in the node
        all_keys = list(node.keys())
        print(f"   All keys: {all_keys}")
        
        if 'agent_id' in node:
            print(f"   ✅ Has agent_id: {node['agent_id']}")
        else:
            print(f"   ❌ Missing agent_id")
        
        # If it's an agent node, print full structure
        if node.get('type') == 'agent':
            print(f"   📝 Full agent node structure:")
            for key, value in node.items():
                if isinstance(value, str) and len(value) > 100:
                    print(f"      {key}: {value[:100]}...")
                else:
                    print(f"      {key}: {value}")
    
    print("\n" + "=" * 60)
    print("🤖 Checking recent agents that might belong to this flow...")
    
    # Get recent agents around the time this flow was created/updated
    flow_created = developed_flow.get("created_at")
    if flow_created:
        # Look for agents created around the same time
        from datetime import datetime, timedelta
        
        time_window_start = flow_created - timedelta(hours=1)
        time_window_end = flow_created + timedelta(hours=1)
        
        related_agents = list(db.agents.find({
            "created_at": {
                "$gte": time_window_start,
                "$lte": time_window_end
            }
        }).sort("created_at", -1))
        
        print(f"📊 Found {len(related_agents)} agents created around flow time")
        
        for i, agent in enumerate(related_agents[:5]):  # Show first 5
            agent_id = str(agent["_id"])
            agent_name = agent.get("name", "Unnamed Agent")
            agent_created = agent.get("created_at")
            
            print(f"   Agent {i+1}: {agent_name}")
            print(f"      ID: {agent_id}")
            print(f"      Created: {agent_created}")
            
            # Check if any node names match this agent name
            matching_nodes = [n for n in nodes if n.get('name', '').lower() in agent_name.lower() or agent_name.lower() in n.get('name', '').lower()]
            if matching_nodes:
                print(f"      🔗 Potential matches: {[n.get('name') for n in matching_nodes]}")

def test_node_id_matching():
    """Test how node ID matching works"""
    
    print("\n🧪 Testing node ID matching logic...")
    print("=" * 60)
    
    # Get a sample flow
    flow = db.flows.find_one({})
    if not flow:
        return
    
    nodes = flow.get("nodes", [])
    agent_nodes = [node for node in nodes if node.get("type") == "agent"]
    
    if not agent_nodes:
        return
    
    sample_node = agent_nodes[0]
    node_id = sample_node.get('id')
    
    print(f"📋 Testing with sample node:")
    print(f"   Node ID: '{node_id}' (type: {type(node_id)})")
    print(f"   Node name: {sample_node.get('name', 'Unnamed')}")
    
    # Test the matching logic used in flow_developer
    print(f"\n🔍 Testing matching logic:")
    
    matches_found = 0
    for j, n in enumerate(nodes):
        test_id = n.get('id')
        print(f"   Node {j}: ID='{test_id}' (type: {type(test_id)})")
        
        # Test exact match
        if n.get('id') == node_id:
            print(f"      ✅ Exact match with n.get('id') == node_id")
            matches_found += 1
        
        # Test string conversion match
        if str(n.get('id')) == str(node_id):
            print(f"      ✅ String match with str comparison")
    
    print(f"\n📊 Total matches found: {matches_found}")

if __name__ == "__main__":
    debug_flow_node_structure()
    test_node_id_matching()