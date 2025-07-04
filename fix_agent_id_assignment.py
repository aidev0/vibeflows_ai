#!/usr/bin/env python3
"""
Script to fix agent_id assignment issue in flow developer
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

def analyze_broken_flows():
    """Analyze flows that are marked as developed but missing agent_ids"""
    
    print("🔍 Analyzing broken flows...")
    print("=" * 60)
    
    # Get flows that are marked as developed but have no agent_ids
    broken_flows = list(db.flows.find({
        "status": "developed",
        "agents_created_count": 0
    }).sort("created_at", -1))
    
    print(f"Found {len(broken_flows)} broken flows")
    
    for flow in broken_flows:
        flow_id = str(flow["_id"])
        flow_name = flow.get("name", "Unnamed")
        created_at = flow.get("created_at")
        
        print(f"\n📋 {flow_name}")
        print(f"   ID: {flow_id}")
        print(f"   Created: {created_at}")
        
        # Get agent nodes
        nodes = flow.get("nodes", [])
        agent_nodes = [node for node in nodes if node.get("type") == "agent"]
        
        print(f"   Agent nodes: {len(agent_nodes)}")
        
        # Find agents created around the same time
        if created_at:
            from datetime import timedelta
            
            time_start = created_at - timedelta(minutes=30)
            time_end = created_at + timedelta(minutes=30)
            
            related_agents = list(db.agents.find({
                "created_at": {
                    "$gte": time_start,
                    "$lte": time_end
                }
            }).sort("created_at", 1))
            
            print(f"   Related agents found: {len(related_agents)}")
            
            # Try to match agents to nodes by name similarity
            matched_pairs = []
            for node in agent_nodes:
                node_name = node.get("name", "").lower()
                node_id = node.get("id", "")
                
                # Find best matching agent
                best_match = None
                best_score = 0
                
                for agent in related_agents:
                    agent_name = agent.get("name", "").lower()
                    agent_id = str(agent["_id"])
                    
                    # Simple scoring based on name similarity
                    score = 0
                    if node_name in agent_name or agent_name in node_name:
                        score += 50
                    if node_id.replace("_", " ") in agent_name:
                        score += 30
                    
                    # Check for keyword matches
                    node_words = set(node_name.replace("_", " ").split())
                    agent_words = set(agent_name.replace("_", " ").split())
                    common_words = node_words.intersection(agent_words)
                    score += len(common_words) * 10
                    
                    if score > best_score:
                        best_score = score
                        best_match = agent
                
                if best_match and best_score > 20:  # Threshold for good match
                    matched_pairs.append({
                        "node": node,
                        "agent": best_match,
                        "score": best_score
                    })
                    print(f"     ✅ {node.get('name')} -> {best_match.get('name')} (score: {best_score})")
                else:
                    print(f"     ❌ No match for {node.get('name')}")
            
            # Ask if we should fix this flow
            if matched_pairs and len(matched_pairs) == len(agent_nodes):
                print(f"\n   🔧 Can auto-fix this flow with {len(matched_pairs)} matches")
                return flow, matched_pairs
    
    return None, None

def fix_flow_agent_assignments(flow, matched_pairs):
    """Fix agent_id assignments for a flow"""
    
    flow_id = flow["_id"]
    flow_name = flow.get("name", "Unnamed")
    
    print(f"\n🔧 Fixing flow: {flow_name}")
    print("=" * 60)
    
    # Update the flow nodes with agent_ids
    updated_nodes = []
    
    for node in flow.get("nodes", []):
        updated_node = node.copy()
        
        # Find matching agent for this node
        for match in matched_pairs:
            if match["node"]["id"] == node["id"]:
                agent_id = str(match["agent"]["_id"])
                updated_node["agent_id"] = agent_id
                print(f"✅ {node.get('name')} -> {agent_id}")
                break
        
        updated_nodes.append(updated_node)
    
    # Update the flow in database
    update_data = {
        "$set": {
            "nodes": updated_nodes,
            "agents_created_count": len(matched_pairs)
        }
    }
    
    result = db.flows.update_one({"_id": flow_id}, update_data)
    
    if result.modified_count > 0:
        print(f"✅ Successfully fixed flow {flow_name}")
        return True
    else:
        print(f"❌ Failed to update flow {flow_name}")
        return False

def main():
    """Main function"""
    
    print("🚀 Agent ID Assignment Fixer")
    print("=" * 60)
    
    # Analyze broken flows
    flow, matched_pairs = analyze_broken_flows()
    
    if flow and matched_pairs:
        print(f"\n🤔 Found fixable flow: {flow.get('name')}")
        response = input("Do you want to fix this flow? (y/N): ").strip().lower()
        
        if response == 'y':
            success = fix_flow_agent_assignments(flow, matched_pairs)
            if success:
                print("\n🎉 Flow fixed successfully!")
                
                # Verify the fix
                fixed_flow = db.flows.find_one({"_id": flow["_id"]})
                agent_nodes = [node for node in fixed_flow.get("nodes", []) if node.get("type") == "agent"]
                nodes_with_agent_id = [node for node in agent_nodes if node.get("agent_id")]
                
                print(f"✅ Verification: {len(nodes_with_agent_id)}/{len(agent_nodes)} nodes now have agent_ids")
            else:
                print("\n❌ Failed to fix flow")
        else:
            print("\n⏭️ Skipping fix")
    else:
        print("\n📭 No fixable flows found")

if __name__ == "__main__":
    main()