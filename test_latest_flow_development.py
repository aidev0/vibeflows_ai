#!/usr/bin/env python3
"""
Test script to get the latest flow for a user and run flow development
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

async def test_latest_flow_development():
    """Get latest flow for user and test flow development"""
    
    print("🔍 Finding latest flow for user...")
    print("=" * 60)
    
    # Get user_id from environment
    test_user_id = os.getenv("TEST_USER_ID")
    
    # Get the latest flow for this user or any flow if user-specific doesn't exist
    latest_flow = None
    if test_user_id:
        latest_flow = db.flows.find_one(
            {"user_id": test_user_id}, 
            sort=[("created_at", -1)]
        )
    
    if not latest_flow:
        print(f"No flows found for user_id: {test_user_id}")
        print("Getting latest flow from any user...")
        latest_flow = db.flows.find_one({}, sort=[("created_at", -1)])
    
    if not latest_flow:
        print("❌ No flows found in database")
        return
    
    flow_id = str(latest_flow["_id"])
    flow_name = latest_flow.get("name", "Unnamed Flow")
    flow_user_id = latest_flow.get("user_id", "unknown")
    status = latest_flow.get("status", "unknown")
    created_at = latest_flow.get("created_at")
    
    print(f"📋 Selected flow: {flow_name}")
    print(f"   ID: {flow_id}")
    print(f"   User ID: {flow_user_id}")
    print(f"   Status: {status}")
    print(f"   Created: {created_at}")
    
    # Check current agent nodes
    nodes = latest_flow.get("nodes", [])
    agent_nodes = [node for node in nodes if node.get("type") == "agent"]
    nodes_with_agent_id = [node for node in agent_nodes if node.get("agent_id")]
    
    print(f"   Total nodes: {len(nodes)}")
    print(f"   Agent nodes: {len(agent_nodes)}")
    print(f"   Nodes with agent_id: {len(nodes_with_agent_id)}")
    
    if len(nodes_with_agent_id) == len(agent_nodes) and len(agent_nodes) > 0:
        print("   ✅ This flow already has all agent_ids assigned")
        print("   🔄 We'll test anyway to see if the fix works...")
    elif len(agent_nodes) == 0:
        print("   ❌ This flow has no agent nodes to develop")
        return
    else:
        print("   🎯 Perfect! This flow has missing agent_ids - ideal for testing")
    
    print(f"\n🚀 Starting flow development test...")
    print("-" * 40)
    
    # Import and run flow developer
    from flow_developer import flow_developer_claude4_sequential
    
    input_data = {
        "flow_id": flow_id,
        "user_id": flow_user_id or test_user_id
    }
    
    try:
        print("Starting flow development...")
        
        # Run flow development and capture all output
        iteration_count = 0
        async for update in flow_developer_claude4_sequential(input_data):
            iteration_count += 1
            message = update.get("message", "")
            update_type = update.get("type", "unknown")
            
            print(f"[{iteration_count:03d}] [{update_type.upper()}] {message}")
            
            # If it's an agent completion, show the details
            if update_type == "agent_complete":
                node_id = update.get("node_id")
                agent_id = update.get("agent_id")
                print(f"      🔗 Node '{node_id}' -> Agent '{agent_id}'")
            
            # Break after reasonable number of updates to avoid infinite loop
            if iteration_count > 100:
                print("⚠️ Breaking after 100 updates to avoid timeout")
                break
    
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
        updated_nodes_with_agent_id = [node for node in updated_agent_nodes if node.get("agent_id")]
        
        print(f"   Agent nodes after development: {len(updated_agent_nodes)}")
        print(f"   Nodes with agent_id after development: {len(updated_nodes_with_agent_id)}")
        
        if len(updated_agent_nodes) > 0:
            success_rate = (len(updated_nodes_with_agent_id) / len(updated_agent_nodes)) * 100
            status = "✅" if success_rate == 100 else "❌"
            print(f"   {status} Success rate: {success_rate:.1f}%")
            
            if success_rate == 100:
                print("\n🎉 SUCCESS! All agent nodes now have agent_ids assigned!")
            else:
                print(f"\n⚠️ PARTIAL SUCCESS: {len(updated_nodes_with_agent_id)}/{len(updated_agent_nodes)} nodes have agent_ids")
        
        print("\n📊 Detailed node status:")
        for i, node in enumerate(updated_agent_nodes):
            node_id = node.get("id", "unknown")
            node_name = node.get("name", "Unnamed Node")
            agent_id = node.get("agent_id", None)
            status = "✅" if agent_id else "❌"
            print(f"     {status} Node {i+1}: {node_name} (ID: {node_id}) -> agent_id: {agent_id or 'MISSING'}")

if __name__ == "__main__":
    asyncio.run(test_latest_flow_development())