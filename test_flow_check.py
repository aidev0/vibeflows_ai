#!/usr/bin/env python3
"""
Test script to check if agent_ids are being properly saved to flow nodes
"""

import os
from pymongo import MongoClient
from bson import ObjectId
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Connect to MongoDB
client = MongoClient(os.getenv("MONGODB_URI"))
db = client.vibeflows

def check_flows_with_agents():
    """Check recent flows to see if agent_ids are being saved to nodes"""
    
    print("🔍 Checking recent flows for agent_ids in nodes...")
    print("=" * 60)
    
    # Check database connection and collection counts
    try:
        flows_count = db.flows.count_documents({})
        agents_count = db.agents.count_documents({})
        print(f"📊 Database connection OK")
        print(f"📊 Total flows in DB: {flows_count}")
        print(f"📊 Total agents in DB: {agents_count}")
        print()
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return
    
    if flows_count == 0:
        print("📭 No flows found in database")
        return
    
    # Get flows with status 'developed' to see what should have agent_ids
    developed_flows = list(db.flows.find({"status": "developed"}).sort("created_at", -1).limit(3))
    print(f"🔍 Found {len(developed_flows)} flows with status 'developed'")
    print()
    
    # Get the most recent 5 flows
    flows = list(db.flows.find().sort("created_at", -1).limit(5))
    
    for i, flow in enumerate(flows):
        flow_id = str(flow["_id"])
        flow_name = flow.get("name", "Unnamed Flow")
        status = flow.get("status", "unknown")
        
        print(f"\n📋 Flow {i+1}: {flow_name}")
        print(f"   ID: {flow_id}")
        print(f"   Status: {status}")
        print(f"   Agents Created Count: {flow.get('agents_created_count', 0)}")
        
        # Check nodes for agent_ids
        nodes = flow.get("nodes", [])
        agent_nodes = [node for node in nodes if node.get("type") == "agent"]
        
        print(f"   Total nodes: {len(nodes)}")
        print(f"   Agent nodes: {len(agent_nodes)}")
        
        for j, node in enumerate(agent_nodes):
            node_id = node.get("id", "unknown")
            node_name = node.get("name", "Unnamed Node")
            agent_id = node.get("agent_id", None)
            
            print(f"     Agent Node {j+1}: {node_name} (ID: {node_id})")
            if agent_id:
                print(f"       ✅ Has agent_id: {agent_id}")
                
                # Verify the agent exists in the agents collection
                agent = db.agents.find_one({"_id": ObjectId(agent_id)})
                if agent:
                    print(f"       ✅ Agent exists in DB: {agent.get('name', 'Unnamed Agent')}")
                else:
                    print(f"       ❌ Agent NOT found in DB!")
            else:
                print(f"       ❌ Missing agent_id")
        
        print("-" * 40)

def check_agents_collection():
    """Check recent agents in the agents collection"""
    
    print("\n🤖 Checking recent agents...")
    print("=" * 60)
    
    agents = list(db.agents.find().sort("created_at", -1).limit(10))
    
    for i, agent in enumerate(agents):
        agent_id = str(agent["_id"])
        agent_name = agent.get("name", "Unnamed Agent")
        status = agent.get("status", "unknown")
        created_at = agent.get("created_at", "unknown")
        
        print(f"Agent {i+1}: {agent_name}")
        print(f"   ID: {agent_id}")
        print(f"   Status: {status}")
        print(f"   Created: {created_at}")
        print()

if __name__ == "__main__":
    check_flows_with_agents()
    check_agents_collection()