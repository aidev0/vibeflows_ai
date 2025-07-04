#!/usr/bin/env python3
"""
Fix agents_created_count to match actual agent_ids in flows
"""

import os
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connect to MongoDB
client = MongoClient(os.getenv("MONGODB_URI"))
db = client.vibeflows

def fix_agents_count():
    """Fix agents_created_count for all flows"""
    
    print("🔧 Fixing agents_created_count for all flows...")
    print("=" * 60)
    
    # Get all flows
    flows = list(db.flows.find({}))
    
    fixed_count = 0
    
    for flow in flows:
        flow_id = str(flow["_id"])
        flow_name = flow.get("name", "Unnamed")
        current_count = flow.get("agents_created_count", 0)
        
        # Count actual agent_ids in nodes
        nodes = flow.get("nodes", [])
        agent_nodes = [node for node in nodes if node.get("type") == "agent"]
        nodes_with_agent_id = [node for node in agent_nodes if node.get("agent_id")]
        actual_count = len(nodes_with_agent_id)
        
        if current_count != actual_count:
            print(f"📋 {flow_name}")
            print(f"   Current count: {current_count}")
            print(f"   Actual count: {actual_count}")
            
            # Update the flow
            result = db.flows.update_one(
                {"_id": flow["_id"]},
                {"$set": {"agents_created_count": actual_count}}
            )
            
            if result.modified_count > 0:
                print(f"   ✅ Fixed: {current_count} -> {actual_count}")
                fixed_count += 1
            else:
                print(f"   ❌ Failed to update")
        elif actual_count > 0:
            print(f"✅ {flow_name}: {actual_count} agents (already correct)")
    
    print(f"\n📊 Summary:")
    print(f"   Total flows checked: {len(flows)}")
    print(f"   Flows fixed: {fixed_count}")

if __name__ == "__main__":
    fix_agents_count()