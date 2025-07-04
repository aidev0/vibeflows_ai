#!/usr/bin/env python3
"""
Test script to run flow development on the latest flow_id
"""

import os
import asyncio
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Connect to MongoDB
client = MongoClient(os.getenv("MONGODB_URI"))
db = client.vibeflows

async def test_flow_development():
    """Test flow development on the latest flow"""
    
    print("🧪 Testing flow development on latest flow...")
    print("=" * 60)
    
    # Get the latest flow
    latest_flow = db.flows.find_one({}, sort=[("created_at", -1)])
    
    if not latest_flow:
        print("❌ No flows found in database")
        return
    
    flow_id = str(latest_flow["_id"])
    flow_name = latest_flow.get("name", "Unnamed Flow")
    status = latest_flow.get("status", "unknown")
    
    print(f"📋 Testing flow: {flow_name}")
    print(f"   ID: {flow_id}")
    print(f"   Status: {status}")
    
    # Check current nodes
    nodes = latest_flow.get("nodes", [])
    agent_nodes = [node for node in nodes if node.get("type") == "agent"]
    
    print(f"   Total nodes: {len(nodes)}")
    print(f"   Agent nodes: {len(agent_nodes)}")
    
    # Show current agent_id status
    for i, node in enumerate(agent_nodes):
        node_id = node.get("id", "unknown")
        node_name = node.get("name", "Unnamed Node")
        agent_id = node.get("agent_id", None)
        print(f"     Node {i+1}: {node_name} (ID: {node_id}) -> agent_id: {agent_id or 'MISSING'}")
    
    print("\n🚀 Starting flow development test...")
    print("-" * 40)
    
    # Import and run flow developer
    from flow_developer import flow_developer_claude4_sequential
    
    input_data = {
        "flow_id": flow_id,
        "user_id": "test_user_123"
    }
    
    try:
        # Run flow development and capture all output
        async for update in flow_developer_claude4_sequential(input_data):
            message = update.get("message", "")
            update_type = update.get("type", "unknown")
            
            print(f"[{update_type.upper()}] {message}")
            
            # If it's an agent completion, show the details
            if update_type == "agent_complete":
                node_id = update.get("node_id")
                agent_id = update.get("agent_id")
                print(f"   🔗 Node {node_id} -> Agent {agent_id}")
    
    except Exception as e:
        print(f"❌ Error during flow development: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🔍 Checking flow after development...")
    
    # Check the flow again after development
    updated_flow = db.flows.find_one({"_id": ObjectId(flow_id)})
    
    if updated_flow:
        print(f"   Status: {updated_flow.get('status', 'unknown')}")
        print(f"   Agents Created Count: {updated_flow.get('agents_created_count', 0)}")
        
        updated_nodes = updated_flow.get("nodes", [])
        updated_agent_nodes = [node for node in updated_nodes if node.get("type") == "agent"]
        
        print(f"   Agent nodes after development:")
        for i, node in enumerate(updated_agent_nodes):
            node_id = node.get("id", "unknown")
            node_name = node.get("name", "Unnamed Node")
            agent_id = node.get("agent_id", None)
            status = "✅" if agent_id else "❌"
            print(f"     {status} Node {i+1}: {node_name} (ID: {node_id}) -> agent_id: {agent_id or 'MISSING'}")

if __name__ == "__main__":
    asyncio.run(test_flow_development())