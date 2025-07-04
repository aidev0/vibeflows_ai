# === TOOL SCHEMAS ===
def get_tool_schemas():
    """Claude tool schema format"""
    return [
        {
            "name": "query_analyzer",
            "description": "Analyzes the user's query and extracts intent and requirements",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_query": {"type": "string"},
                    "conversation_history": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string"},
                                "content": {"type": "string"}
                            },
                            "required": ["role", "content"]
                        }
                    }
                },
                "required": ["user_query"]
            }
        },
        {
            "name": "flow_designer",
            "description": "Designs a flow from the user requirements",
            "input_schema": {
                "type": "object",
                "properties": {
                    "requirements": {"type": "string"}
                },
                "required": ["requirements"]
            }
        },
        {
            "name": "flow_developer",
            "description": "Develops agents inside the flow using Claude 4 sequential processing",
            "input_schema": {
                "type": "object",
                "properties": {
                    "flow_id": {"type": "string"}
                },
                "required": ["flow_id"]
            }
        },
        {
            "name": "flow_developer_gemini",
            "description": "Develops agents inside the flow using Gemini with multiprocessing",
            "input_schema": {
                "type": "object",
                "properties": {
                    "flow_id": {"type": "string"}
                },
                "required": ["flow_id"]
            }
        },
        {
            "name": "n8n_developer",
            "description": "Generates and deploys n8n workflow from requirements",
            "input_schema": {
                "type": "object",
                "properties": {
                    "requirements": {"type": "string"}
                },
                "required": ["requirements"]
            }
        },
        {
            "name": "mongodb_tool",
            "description": "Reads from MongoDB collections (agents, flows, runs, n8n_workflows only) with a filter",
            "input_schema": {
                "type": "object",
                "properties": {
                    "collection": {"type": "string", "enum": ["agents", "flows", "runs", "n8n_workflows"]},
                    "filter": {"type": "object"}
                },
                "required": ["collection"]
            }
        },
        {
            "name": "check_credentials",
            "description": "Checks if user has access to required credentials",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "required_credentials": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["user_id", "required_credentials"]
            }
        },
        {
            "name": "get_n8n_workflows",
            "description": "Gets user's n8n workflows and displays their N8N URLs",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "limit": {"type": "number", "default": 10}
                },
                "required": ["user_id"]
            }
        },
        {
            "name": "get_credential_names",
            "description": "Gets user's available CREDENTIALS (not agents) - returns credential names, types, and descriptions for authentication/API access",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"}
                },
                "required": ["user_id"]
            }
        },
        {
            "name": "get_flow_and_agents",
            "description": "Gets all agents for a given flow_id by fetching agents from flow nodes with agent_id",
            "input_schema": {
                "type": "object",
                "properties": {
                    "flow_id": {"type": "string"}
                },
                "required": ["flow_id"]
            }
        }
    ]

# === TOOL IMPORTS ===
from query_analyzer import query_analyzer
from flow_designer import flow_designer
from flow_developer import flow_developer_streaming, flow_developer_claude4_sequential, flow_developer_gemini
from n8n_developer import n8n_developer
from flow_runner import flow_runner
from mongodb_tool import mongodb_tool, check_credentials, get_n8n_workflows, get_credential_names, get_flow_and_agents

# === TOOL MAPPINGS ===
TOOLS = {
    "query_analyzer": query_analyzer,
    "flow_designer": flow_designer,
    "flow_developer": flow_developer_claude4_sequential,
    "flow_developer_gemini": flow_developer_gemini,
    "n8n_developer": n8n_developer,
    "flow_runner": flow_runner,
    "mongodb_tool": mongodb_tool,
    "check_credentials": check_credentials,
    "get_n8n_workflows": get_n8n_workflows,
    "get_credential_names": get_credential_names,
    "get_flow_and_agents": get_flow_and_agents
}