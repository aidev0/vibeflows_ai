import anthropic
import json
import os
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
db = MongoClient(os.getenv("MONGODB_URI")).vibeflows

def flow_designer(input_data: dict) -> dict:
    requirements = input_data.get('requirements', '')
    
    system_prompt = """You are a workflow architect. Design flows that break down user requirements into executable nodes.

Return ONLY valid JSON with proper flow structure. No markdown, no explanations."""

    prompt = f"""Create a flow for these requirements: {requirements}

Design a flow that breaks down the user query into nodes (which can be flows, agents, apps, or functions).

Return ONLY valid JSON with this structure:
{{
   "name": "flow_name",
   "description": "what this flow accomplishes",
   "input_schema": {{"type": "object", "properties": {{}}}},
   "output_schema": {{"type": "object", "properties": {{}}}},
   "nodes": [
       {{
           "id": "node_id", 
           "type": "flow|agent",
           "name": "node_name",
           "description": "specific node description",
           "input_schema": {{"type": "object", "properties": {{}}}},
           "output_schema": {{"type": "object", "properties": {{}}}},
       }}
   ],
   "edges": [
       {{
           "id": "edge_1",
           "source": "node1", 
           "target": "node2", 
           "sourceHandle": "output",
           "targetHandle": "input",
           "label": "success path",
           "condition": "result.status == 'success'"
       }}
   ]
}}"""
   
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = response.content[0].text.strip()
        
        # Clean response of markdown code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        # Parse the JSON response
        flow_spec = json.loads(response_text)
        
        # Save to database
        result = db.flows.insert_one({
            **flow_spec,
            "created_at": datetime.utcnow()
        })
        _id = result.inserted_id  
        flow_spec['_id'] = str(_id)
        
        return flow_spec
        
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse flow design JSON: {str(e)}")
        print(f"Raw response: {response_text}")
        return {
            "error": f"Failed to parse flow design: {str(e)}",
            "name": "Error Flow",
            "_id": None
        }
    except Exception as e:
        print(f"❌ Error in flow_designer: {str(e)}")
        return {
            "error": f"Flow design failed: {str(e)}",
            "name": "Error Flow", 
            "_id": None
        }