import os
import json
from bson import ObjectId
from datetime import datetime
from pymongo import MongoClient

# === DATABASE CONNECTION ===
client = MongoClient(os.getenv("MONGODB_URI"))
db = client.vibeflows

def mongodb_tool(input_data):
    """
    Reads from MongoDB collections with restricted access to specific collections only.
    Only allows access to: agents, flows, runs, n8n_workflows
    Returns only _id, name, and description fields for security.
    """
    def convert_for_json(obj):
        """Recursively convert MongoDB objects to JSON-serializable format"""
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: convert_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_for_json(item) for item in obj]
        else:
            return obj
    
    collection_name = input_data["collection"]
    query_filter = input_data.get("filter", {})
    
    # Restrict access to only allowed collections
    allowed_collections = ["agents", "flows", "runs", "n8n_workflows"]
    if collection_name not in allowed_collections:
        return {"error": f"Access denied. Only allowed collections: {', '.join(allowed_collections)}", "message": "❌ Unauthorized collection access"}

    try:
        collection = db[collection_name]
        # Only return _id, name, and description fields
        docs = list(collection.find(query_filter, {"_id": 1, "name": 1, "description": 1}))
        
        # Recursively convert all MongoDB objects to JSON-serializable format
        serializable_docs = [convert_for_json(doc) for doc in docs]
        
        # Test JSON serialization to catch any remaining issues
        try:
            json.dumps(serializable_docs)
        except TypeError as e:
            print(f"❌ Still have serialization issue: {e}")
            # Fallback: convert everything to strings
            for doc in serializable_docs:
                for key, value in doc.items():
                    if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                        doc[key] = str(value)
        
        return {"results": serializable_docs, "message": f"✅ Retrieved {len(docs)} document(s) from `{collection_name}`"}
    except Exception as e:
        return {"error": str(e), "message": "❌ Failed to run MongoDB query"}

def check_credentials(input_data):
    """Check if user has access to required credentials"""
    user_id = input_data["user_id"]
    required_credentials = input_data["required_credentials"]
    
    # Clean user_id (handle URL encoding)
    clean_user_id = str(user_id).replace('%7C', '|').replace('%7c', '|')
    
    try:
        # Get user's credentials from database
        user_creds = list(db.credentials.find({"user_id": clean_user_id}))
        
        # Extract credential names
        available_creds = [cred["name"] for cred in user_creds]
        
        # Check which required credentials are missing
        missing_creds = [cred for cred in required_credentials if cred not in available_creds]
        
        if missing_creds:
            return {
                "has_access": False,
                "missing_credentials": missing_creds,
                "available_credentials": available_creds,
                "message": f"❌ Missing required credentials: {', '.join(missing_creds)}"
            }
        else:
            return {
                "has_access": True,
                "available_credentials": available_creds,
                "message": f"✅ User has access to all required credentials"
            }
    except Exception as e:
        return {"error": str(e), "message": "❌ Failed to check credentials"}

def get_n8n_workflows(input_data):
    """Get user's n8n workflows and display their N8N URLs"""
    user_id = input_data["user_id"]
    limit = input_data.get("limit", 10)
    
    # Clean user_id (handle URL encoding)
    clean_user_id = str(user_id).replace('%7C', '|').replace('%7c', '|')
    
    try:
        # Get user's N8N URL credential
        n8n_url_cred = db.credentials.find_one({"user_id": clean_user_id, "name": "N8N_URL"})
        if not n8n_url_cred:
            return {"error": "N8N_URL credential not found", "message": "❌ User doesn't have N8N_URL credential configured"}
        
        n8n_base_url = n8n_url_cred["value"].rstrip('/')
        
        # Get user's n8n workflows, sorted by most recent
        workflows = list(db.n8n_workflows.find(
            {"user_id": clean_user_id}, 
            {"_id": 1, "n8n_response": 1, "created_at": 1}
        ).sort("created_at", -1).limit(limit))
        
        workflow_urls = []
        for workflow in workflows:
            # Extract workflow ID from n8n_response
            n8n_response = workflow.get("n8n_response", {})
            workflow_id = n8n_response.get("id")
            
            if workflow_id:
                workflow_url = f"{n8n_base_url}/workflow/{workflow_id}"
                workflow_urls.append({
                    "_id": str(workflow["_id"]),
                    "n8n_workflow_id": workflow_id,
                    "n8n_url": workflow_url,
                    "created_at": workflow.get("created_at")
                })
        
        if not workflow_urls:
            return {"workflows": [], "message": "📭 No N8N workflows found for this user"}
        
        return {
            "workflows": workflow_urls,
            "count": len(workflow_urls),
            "n8n_base_url": n8n_base_url,
            "message": f"✅ Found {len(workflow_urls)} N8N workflow(s) for user"
        }
        
    except Exception as e:
        return {"error": str(e), "message": "❌ Failed to get N8N workflows"}

def get_credential_names(input_data):
    """Get user's credential names and descriptions"""
    user_id = input_data["user_id"]
    
    # Clean user_id (handle URL encoding)
    clean_user_id = str(user_id).replace('%7C', '|').replace('%7c', '|')
    
    try:
        # Get user's credentials from database
        user_creds = list(db.credentials.find(
            {"user_id": clean_user_id}, 
            {"name": 1, "description": 1, "type": 1, "created_at": 1}
        ))
        
        if not user_creds:
            return {"credentials": [], "message": "📭 No credentials found for this user"}
        
        # Format credentials for display
        formatted_creds = []
        for cred in user_creds:
            formatted_creds.append({
                "name": cred.get("name", ""),
                "description": cred.get("description", "No description"),
                "type": cred.get("type", "unknown"),
                "created_at": cred.get("created_at")
            })
        
        return {
            "credentials": formatted_creds,
            "count": len(formatted_creds),
            "message": f"✅ Found {len(formatted_creds)} credential(s) for user"
        }
        
    except Exception as e:
        return {"error": str(e), "message": "❌ Failed to get credentials"}