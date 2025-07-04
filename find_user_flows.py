#!/usr/bin/env python3
"""
Find actual user_ids and their flows in the database
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Connect to MongoDB
client = MongoClient(os.getenv("MONGODB_URI"))
db = client.vibeflows

def find_user_flows():
    """Find all user_ids and their flows"""
    
    print("🔍 Finding user_ids and their flows...")
    print("=" * 60)
    
    # Get all unique user_ids from flows
    user_ids = db.flows.distinct("user_id")
    print(f"📊 Found {len(user_ids)} unique user_ids in flows:")
    
    for i, user_id in enumerate(user_ids):
        if user_id:  # Skip None/null user_ids
            # Count flows for this user
            flow_count = db.flows.count_documents({"user_id": user_id})
            
            # Get latest flow for this user
            latest_flow = db.flows.find_one(
                {"user_id": user_id}, 
                sort=[("created_at", -1)]
            )
            
            if latest_flow:
                flow_name = latest_flow.get("name", "Unnamed")
                created_at = latest_flow.get("created_at", "unknown")
                status = latest_flow.get("status", "unknown")
                
                print(f"\n👤 User {i+1}: {user_id}")
                print(f"   Total flows: {flow_count}")
                print(f"   Latest flow: {flow_name}")
                print(f"   Created: {created_at}")
                print(f"   Status: {status}")
                
                # Check agent nodes in latest flow
                nodes = latest_flow.get("nodes", [])
                agent_nodes = [node for node in nodes if node.get("type") == "agent"]
                nodes_with_agent_id = [node for node in agent_nodes if node.get("agent_id")]
                
                if len(agent_nodes) > 0:
                    success_rate = (len(nodes_with_agent_id) / len(agent_nodes)) * 100
                    status = "✅" if success_rate == 100 else "❌"
                    print(f"   {status} Agent nodes: {len(nodes_with_agent_id)}/{len(agent_nodes)} have agent_ids ({success_rate:.1f}%)")
    
    # Also show flows without user_id
    flows_without_user = db.flows.count_documents({"user_id": {"$in": [None, ""]}})
    if flows_without_user > 0:
        print(f"\n📭 {flows_without_user} flows have no user_id")
        
        latest_no_user = db.flows.find_one(
            {"user_id": {"$in": [None, ""]}}, 
            sort=[("created_at", -1)]
        )
        
        if latest_no_user:
            flow_name = latest_no_user.get("name", "Unnamed")
            created_at = latest_no_user.get("created_at", "unknown")
            print(f"   Latest: {flow_name} ({created_at})")
    
    print(f"\n📋 All flows (most recent first):")
    all_flows = list(db.flows.find({}, {
        "_id": 1, 
        "name": 1, 
        "user_id": 1, 
        "created_at": 1, 
        "status": 1
    }).sort("created_at", -1).limit(10))
    
    for i, flow in enumerate(all_flows):
        flow_id = str(flow["_id"])
        flow_name = flow.get("name", "Unnamed")
        user_id = flow.get("user_id", "NO_USER")
        created_at = flow.get("created_at", "unknown")
        status = flow.get("status", "unknown")
        
        print(f"   {i+1:2d}. {flow_name}")
        print(f"       ID: {flow_id}")
        print(f"       User: {user_id}")
        print(f"       Created: {created_at}")
        print(f"       Status: {status}")
        print()

if __name__ == "__main__":
    find_user_flows()