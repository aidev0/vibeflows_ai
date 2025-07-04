#!/usr/bin/env python3
"""
Test single agent development to verify the fix
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

def test_single_agent():
    """Test agent development and direct database save"""
    
    print("🧪 Single Agent Development Test")
    print("=" * 50)
    
    # Your user_id from environment
    your_user_id = os.getenv("TEST_USER_ID")
    if not your_user_id:
        print("❌ TEST_USER_ID environment variable not set")
        return
    
    # Get your latest flow
    your_flow = db.flows.find_one(
        {"user_id": your_user_id}, 
        sort=[("created_at", -1)]
    )
    
    flow_id = str(your_flow["_id"])
    flow_name = your_flow.get("name", "Unnamed")
    
    print(f"📋 Testing: {flow_name}")
    print(f"   ID: {flow_id}")
    
    # Get current state
    nodes = your_flow.get("nodes", [])
    agent_nodes = [node for node in nodes if node.get("type") == "agent"]
    
    if len(agent_nodes) == 0:
        print("❌ No agent nodes to test")
        return
    
    # Pick the first agent node
    test_node = agent_nodes[0]
    node_id = test_node["id"]
    node_name = test_node.get("name", "Unnamed")
    
    print(f"🎯 Testing node: {node_name} (ID: {node_id})")
    
    # Create an agent for this node
    print(f"🤖 Creating agent...")
    
    from agent_maker import agent_developer_claude4
    
    agent_input = {
        'requirements': str(test_node),
        'user_id': your_user_id
    }
    
    try:
        result = agent_developer_claude4(agent_input)
        agent_id = result.get('agent_id')
        
        print(f"✅ Agent created: {agent_id}")
        
        # Now manually update the flow
        print(f"🔧 Updating flow manually...")
        
        # Get fresh copy of flow
        fresh_flow = db.flows.find_one({"_id": ObjectId(flow_id)})
        
        # Update the specific node
        updated = False
        for i, node in enumerate(fresh_flow["nodes"]):
            if node.get("id") == node_id:
                fresh_flow["nodes"][i]["agent_id"] = agent_id
                updated = True
                print(f"✅ Updated node {i}: {node.get('name')} -> {agent_id}")
                break
        
        if not updated:
            print(f"❌ Failed to find node {node_id}")
            return
        
        # Update flow metadata
        fresh_flow["status"] = "developed"
        fresh_flow["agents_created_count"] = 1
        
        # Save to database
        print(f"💾 Saving to database...")
        result = db.flows.replace_one({"_id": ObjectId(flow_id)}, fresh_flow)
        
        print(f"📊 Update result: modified_count = {result.modified_count}")
        
        # Verify the save
        print(f"🔍 Verifying save...")
        verified_flow = db.flows.find_one({"_id": ObjectId(flow_id)})
        
        verified_nodes = verified_flow.get("nodes", [])
        verified_agent_nodes = [node for node in verified_nodes if node.get("type") == "agent"]
        verified_nodes_with_agent_id = [node for node in verified_agent_nodes if node.get("agent_id")]
        
        print(f"📊 Verification results:")
        print(f"   Status: {verified_flow.get('status')}")
        print(f"   Agents Created Count: {verified_flow.get('agents_created_count')}")
        print(f"   Nodes with agent_id: {len(verified_nodes_with_agent_id)}")
        
        for i, node in enumerate(verified_agent_nodes):
            agent_id = node.get("agent_id", None)
            status = "✅" if agent_id else "❌"
            print(f"     {status} {node.get('name')} -> {agent_id or 'MISSING'}")
        
        if len(verified_nodes_with_agent_id) > 0:
            print(f"\n🎉 SUCCESS! Manual update worked!")
        else:
            print(f"\n❌ FAILURE: Manual update failed")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_agent()