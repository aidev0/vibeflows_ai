#!/usr/bin/env python3
"""
Quick test to see if our fixes work with a minimal example
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

async def quick_test():
    """Quick test with timeout"""
    
    print("🧪 Quick Flow Development Test")
    print("=" * 50)
    
    # Get the latest flow
    latest_flow = db.flows.find_one({}, sort=[("created_at", -1)])
    
    if not latest_flow:
        print("❌ No flows found")
        return
    
    flow_id = str(latest_flow["_id"])
    flow_name = latest_flow.get("name", "Unnamed")
    
    print(f"📋 Testing: {flow_name} ({flow_id})")
    
    # Check current state
    nodes = latest_flow.get("nodes", [])
    agent_nodes = [node for node in nodes if node.get("type") == "agent"]
    
    print(f"📊 Agent nodes: {len(agent_nodes)}")
    
    # Show current agent_id status
    for i, node in enumerate(agent_nodes):
        agent_id = node.get("agent_id", "MISSING")
        print(f"   Node {i+1}: {node.get('name', 'Unnamed')} -> {agent_id}")
    
    if len(agent_nodes) == 0:
        print("❌ No agent nodes to test")
        return
    
    print("\n🚀 Starting development (will timeout after 30 seconds)...")
    
    # Import flow developer
    from flow_developer import flow_developer_claude4_sequential
    
    input_data = {
        "flow_id": flow_id,
        "user_id": "test_user"
    }
    
    try:
        # Run with timeout
        update_count = 0
        async for update in flow_developer_claude4_sequential(input_data):
            update_count += 1
            message = update.get("message", "")
            update_type = update.get("type", "")
            
            print(f"[{update_count:02d}] {update_type}: {message}")
            
            # Stop after first agent completion or 10 updates
            if update_type == "agent_complete" or update_count >= 10:
                print("⏱️ Stopping early for quick test...")
                break
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Quick check
    print("\n🔍 Quick check after test...")
    updated_flow = db.flows.find_one({"_id": ObjectId(flow_id)})
    if updated_flow:
        updated_nodes = updated_flow.get("nodes", [])
        updated_agent_nodes = [node for node in updated_nodes if node.get("type") == "agent"]
        
        print(f"📊 Agent nodes after: {len(updated_agent_nodes)}")
        for i, node in enumerate(updated_agent_nodes):
            agent_id = node.get("agent_id", "MISSING")
            status = "✅" if agent_id != "MISSING" else "❌"
            print(f"   {status} Node {i+1}: {node.get('name', 'Unnamed')} -> {agent_id}")

if __name__ == "__main__":
    # Run with overall timeout
    try:
        asyncio.wait_for(quick_test(), timeout=60.0)
    except asyncio.TimeoutError:
        print("⏰ Test timed out after 60 seconds")
    except Exception as e:
        print(f"❌ Test failed: {e}")