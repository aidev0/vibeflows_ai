#!/usr/bin/env python3
"""
Test the full flow development process to see database save
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

async def test_full_flow():
    """Test the complete flow development process"""
    
    print("🧪 Full Flow Development Test")
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
    
    print(f"📋 Testing: {flow_name} ({flow_id})")
    
    # Import flow developer
    from flow_developer import flow_developer_claude4_sequential
    
    input_data = {
        "flow_id": flow_id,
        "user_id": your_user_id
    }
    
    print(f"🚀 Starting COMPLETE flow development...")
    
    try:
        update_count = 0
        
        async for update in flow_developer_claude4_sequential(input_data):
            update_count += 1
            message = update.get("message", "")
            update_type = update.get("type", "unknown")
            
            # Only show important updates to avoid spam
            if update_type in ["status", "agent_complete", "complete", "error"]:
                print(f"[{update_count:03d}] {update_type}: {message}")
            
            # Stop after completion
            if update_type == "complete":
                print("✅ Flow development completed!")
                break
            
            # Safety stop
            if update_count >= 200:
                print("⏱️ Safety stop at 200 updates")
                break
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("🔍 Final Results...")
    
    # Check final state
    final_flow = db.flows.find_one({"_id": ObjectId(flow_id)})
    
    if final_flow:
        status = final_flow.get("status", "unknown")
        agents_count = final_flow.get("agents_created_count", 0)
        
        print(f"📊 Final flow state:")
        print(f"   Status: {status}")
        print(f"   Agents Created Count: {agents_count}")
        
        nodes = final_flow.get("nodes", [])
        agent_nodes = [node for node in nodes if node.get("type") == "agent"]
        nodes_with_agent_id = [node for node in agent_nodes if node.get("agent_id")]
        
        print(f"   Agent nodes: {len(agent_nodes)}")
        print(f"   Nodes with agent_id: {len(nodes_with_agent_id)}")
        
        if len(agent_nodes) > 0:
            success_rate = (len(nodes_with_agent_id) / len(agent_nodes)) * 100
            status = "✅" if success_rate == 100 else "❌" if success_rate == 0 else "⚠️"
            print(f"   {status} Success rate: {success_rate:.1f}%")
        
        if len(nodes_with_agent_id) > 0:
            print(f"\n🎉 SUCCESS! Agent IDs assigned:")
            for i, node in enumerate(agent_nodes):
                agent_id = node.get("agent_id", None)
                if agent_id:
                    print(f"   ✅ {node.get('name')} -> {agent_id}")
        else:
            print(f"\n❌ FAILURE: No agent IDs assigned despite development")

if __name__ == "__main__":
    try:
        asyncio.run(asyncio.wait_for(test_full_flow(), timeout=300.0))  # 5 minute timeout
    except asyncio.TimeoutError:
        print("⏰ Test timed out after 5 minutes")
    except Exception as e:
        print(f"❌ Test failed: {e}")