#!/usr/bin/env python3
"""
Test flow development on your specific user flow
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

async def test_user_flow():
    """Test flow development on your user's latest flow"""
    
    print("🧪 Testing Flow Development on Your Flow")
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
    
    if not your_flow:
        print("❌ No flows found for your user_id")
        return
    
    flow_id = str(your_flow["_id"])
    flow_name = your_flow.get("name", "Unnamed")
    
    print(f"📋 Your flow: {flow_name}")
    print(f"   ID: {flow_id}")
    print(f"   User: {your_user_id}")
    
    # Check current agent nodes
    nodes = your_flow.get("nodes", [])
    agent_nodes = [node for node in nodes if node.get("type") == "agent"]
    nodes_with_agent_id = [node for node in agent_nodes if node.get("agent_id")]
    
    print(f"📊 Current state:")
    print(f"   Total nodes: {len(nodes)}")
    print(f"   Agent nodes: {len(agent_nodes)}")
    print(f"   Nodes with agent_id: {len(nodes_with_agent_id)}")
    
    print(f"\n📝 Agent nodes details:")
    for i, node in enumerate(agent_nodes):
        node_id = node.get("id", "unknown")
        node_name = node.get("name", "Unnamed")
        agent_id = node.get("agent_id", None)
        status = "✅" if agent_id else "❌"
        print(f"   {status} {i+1}. {node_name} (ID: {node_id}) -> {agent_id or 'MISSING'}")
    
    if len(agent_nodes) == 0:
        print("❌ No agent nodes to develop")
        return
    
    print(f"\n🚀 Starting flow development...")
    print("-" * 40)
    
    # Import flow developer
    from flow_developer import flow_developer_claude4_sequential
    
    input_data = {
        "flow_id": flow_id,
        "user_id": your_user_id
    }
    
    try:
        update_count = 0
        agent_complete_count = 0
        
        async for update in flow_developer_claude4_sequential(input_data):
            update_count += 1
            message = update.get("message", "")
            update_type = update.get("type", "unknown")
            
            print(f"[{update_count:03d}] [{update_type.upper()}] {message}")
            
            # Track agent completions
            if update_type == "agent_complete":
                agent_complete_count += 1
                node_id = update.get("node_id")
                agent_id = update.get("agent_id")
                print(f"      🎯 Agent {agent_complete_count}: Node '{node_id}' -> Agent '{agent_id}'")
                
                # Stop after first successful agent to check if fix works
                if agent_complete_count >= 1:
                    print("\n⏱️ Stopping after first agent to verify fix...")
                    break
            
            # Stop after reasonable number of updates
            if update_count >= 50:
                print("\n⏱️ Stopping after 50 updates...")
                break
    
    except Exception as e:
        print(f"❌ Error during flow development: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("🔍 Checking results...")
    
    # Check the flow after development
    updated_flow = db.flows.find_one({"_id": ObjectId(flow_id)})
    
    if updated_flow:
        print(f"📊 Flow after development:")
        print(f"   Status: {updated_flow.get('status', 'unknown')}")
        print(f"   Agents Created Count: {updated_flow.get('agents_created_count', 0)}")
        
        updated_nodes = updated_flow.get("nodes", [])
        updated_agent_nodes = [node for node in updated_nodes if node.get("type") == "agent"]
        updated_nodes_with_agent_id = [node for node in updated_agent_nodes if node.get("agent_id")]
        
        print(f"   Agent nodes: {len(updated_agent_nodes)}")
        print(f"   Nodes with agent_id: {len(updated_nodes_with_agent_id)}")
        
        if len(updated_agent_nodes) > 0:
            success_rate = (len(updated_nodes_with_agent_id) / len(updated_agent_nodes)) * 100
            status = "✅" if success_rate > 0 else "❌"
            print(f"   {status} Success rate: {success_rate:.1f}%")
        
        print(f"\n📝 Updated agent nodes:")
        for i, node in enumerate(updated_agent_nodes):
            node_id = node.get("id", "unknown")
            node_name = node.get("name", "Unnamed")
            agent_id = node.get("agent_id", None)
            status = "✅" if agent_id else "❌"
            print(f"   {status} {i+1}. {node_name} (ID: {node_id}) -> {agent_id or 'MISSING'}")
        
        # Check if we fixed at least one
        if len(updated_nodes_with_agent_id) > len(nodes_with_agent_id):
            improvement = len(updated_nodes_with_agent_id) - len(nodes_with_agent_id)
            print(f"\n🎉 SUCCESS! Fixed {improvement} node(s) with agent_id assignment!")
        elif len(updated_nodes_with_agent_id) == 0:
            print(f"\n❌ FAILURE: Still no agent_ids assigned to nodes")
        else:
            print(f"\n⚠️ PARTIAL: No new agent_ids assigned")

if __name__ == "__main__":
    try:
        asyncio.run(asyncio.wait_for(test_user_flow(), timeout=120.0))
    except asyncio.TimeoutError:
        print("⏰ Test timed out after 2 minutes")
    except Exception as e:
        print(f"❌ Test failed: {e}")