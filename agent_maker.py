import google.generativeai as genai
import json
import os
from pymongo import MongoClient
from datetime import datetime
import asyncio

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
db = MongoClient(os.getenv("MONGODB_URI")).vibeflows

AGENT_PROMPT = """You are an expert agent architect. 
Create an agent specification for this node:

REQUIREMENTS: {requirements}

Design an agent with interconnected nodes and edges using available resources.

AGENT SCHEMA:
{agent_schema}

NODE SCHEMA:
{node_schema}

EDGE SCHEMA:
{edge_schema}

Each agent should have a function that has access to the other functions in the agent node.
The function should be able to call the other functions in the agent node.
You don't have to redefine the nodes function here. Just use the function name.
The agent's funciton is the main function, it is a pipeline that will be called to run the agent.
It needs to do the flow of the agent, meaning what exactly happens in the edges.
It needs to make sure the input and output of the function calls are correct.

The nodes need to have working function. 
No assumptions, placeholder functions, no tests, no other code outside of the function.
The function should be able to handle the input and output of the node.
We prefer LLM nodes for complex tasks. Do not create if/else, use case matching, etc.
Instead, use the LLM node to generate the output based on the input.
Obviously, sometimes we don't need an LLM node, but we prefer it for complex tasks.

In nodes, the parameters are more static and the input_schema is more dynamic.
e.g. system, model is static, but the input_schema is user_query, chat_history.
Integrations, MCP clients, tools use input_schema for all the parameters & dynamic input.

In LLM nodes, we use integrations to call the LLM.
The paramters store the system, model, max_tokens, temperature, etc.
You don't need to define these parameters in the function.
Please do not duplicate the integration function, just use it.

Assume that the input_data to the function with LLM node is a JSON object.
The INPUT JSON object has the following keys:
- system
- model
- max_tokens
- temperature
- integration_name

If you wanna use system, use input_data['system']
if you wanna use the integration_name, use input_data['integration_name']

this is  how to inference the LLM models:

client = MongoClient(os.getenv('MONGODB_URI'))
db = client.vibeflows
integration_name = input_data['integration_name']
function_name = input_data['integration_name']
integration = db.integrations.find_one({{'name': integration_name}})
function_code = integration['function']
exec(function_code, globals())
result = globals()[function_name](input_data)

convert the input_data and parameters to input proper for the integration function 
(takes messages list in addition to the system and model from parameters)
and call the integration function.

TOOL SCHEMA:
{tool_schema}

INTEGRATION SCHEMA:
{integration_schema}

MCP CLIENT SCHEMA:
{mcp_client_schema}

LLM NODE SCHEMA:
{llm_node_schema}

CREDENTIALS:
{credentials}

Our Preferred LLM MODELS: claude-sonnet-4-20250514

AVAILABLE RESOURCES:
Tools: {tools}
Integrations: {integrations}

Preferred LLM model: claude-sonnet-4-20250514

IMPORTANT: Return ONLY valid JSON. Do NOT use ObjectId(), use regular strings for IDs.
For credentials, use strings like "gemini_api_key" instead of ObjectId constructs.

Return ONLY valid JSON matching the agent schema."""

AGENT_SCHEMA = {
    "name": "string",
    "description": "string", 
    "nodes": "array",
    "edges": "array",
    "input_schema": "object",
    "output_schema": "object",
    "function": "string",
    "tools": "array",
    "integrations": "array",
    "mcp_clients": "array",
    "status": "string"
}

LLM_NODE_SCHEMA = {
    "type": "llm", 
    "name": "string",
    "description": "string",
    "parameters": {
        "system": "string",
        "model": "string",
        "max_tokens": "number",
        "temperature": "number",
        "integration_name": "string",
        "prompt": "string",
        "integrations": "array",
        "mcp_clients": "array",
        "tools": "array",
    },  
    "input_schema": "messages: list[object{role: string, content: string}]",
    "output_schema": "object",
    "language": "string",
    "function": "string",
    "credentials": "array",
    "created_at": "date",
    "required_packages": "array"
}

INTEGRATION_SCHEMA = {
  "name": "string",
  "description": "string",
  "type": "api|oauth|llm",
  "function": "def inference_anthropic(data):\n    import anthropic\n    import os\n    import json\n    \n    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))\n    \n    # Prepare tools if provided\n    claude_tools = []\n    if data.get('tools'):\n        for tool in data['tools']:\n            claude_tools.append({\n                'name': tool['name'],\n                'description': tool['description'],\n                'input_schema': tool.get('input_schema', {})\n            })\n    \n    # Build kwargs\n    kwargs = {\n        'model': data.get('model', 'claude-4-sonnet-20250514'),\n        'messages': data.get('messages', []),\n        'temperature': data.get('temperature', 0.7),\n        'max_tokens': data.get('max_tokens', 8192)\n    }\n    \n    if data.get('system'):\n        kwargs['system'] = data['system']\n    \n    if claude_tools:\n        kwargs['tools'] = claude_tools\n    \n    response = client.messages.create(**kwargs)\n    \n    # Handle tool use if present\n    result = {\n        'response': '',\n        'usage': response.usage,\n        'tool_calls': []\n    }\n    \n    for content in response.content:\n        if content.type == 'text':\n            result['response'] += content.text\n        elif content.type == 'tool_use':\n            result['tool_calls'].append({\n                'id': content.id,\n                'function': content.name,\n                'arguments': json.dumps(content.input)\n            })\n    \n    return result",
  "input_schema": "object",
  "output_schema": "object",
  "credentials": "array",
  "language": "string",
  "required_packages": "array",
  "created_at": "date",
}

MCP_CLIENT_SCHEMA = {
    "name": "string",
    "description": "string",
    "type": "mcp_client",
    "command": "string",
    "args": "array",
    "language": "string",
    "required_packages": "array",
    "credentials": "array",
    "env": "object",
    "created_at": "date",
}

NODE_SCHEMA = {
    "id": "string",
    "type": "string - llm|api|oauth|mcp_client|tool|function|trigger|webhook|scheduler|pause|wait",
    "name": "string",
    "description": "string",
    "input_schema": "object",
    "parameters": "object",
    "output_schema": "object",
    "credentials": "array",
    "function": "string",
    "language": "string",
    "required_packages": "array",
    "created_at": "date",
}

TOOL_NODE_SCHEMA = {
    "name": "string",
    "description": "string",
    "type": "tool",
    "function": "string",
    "input_schema": "object",
    "output_schema": "object",
    "language": "string",
    "required_packages": "array",
    "credentials": "object",
    "created_at": "date",
}

EDGE_SCHEMA = {
    "id": "string",
    "source": "string",
    "target": "string", 
    "sourceHandle": "string",
    "targetHandle": "string",
    "label": "string",
    "condition": "string",
    "animated": "boolean"
}

def agent_developer(input_data: dict) -> dict:
    """
    Design an executable agent from a flow node specification
    
    Args:
        input_data: Dictionary containing:
            - requirements: Stringified agent node or additional requirements
        
    Returns:
        Dictionary containing agent specification and agent_id
    """

    requirements = input_data.get("requirements", "")
    
    try:
        # Get available resources
        tools = list(db.tools.find({}))
        integrations = list(db.integrations.find({}))
        credentials = list(db.credentials.find({}, {"name": 1}))
        
        system = AGENT_PROMPT.format(
            requirements=requirements,
            tools="",
            integrations="",
            credentials=str(credentials),
            agent_schema=str(AGENT_SCHEMA),
            node_schema=json.dumps(NODE_SCHEMA, indent=2),
            edge_schema=json.dumps(EDGE_SCHEMA, indent=2),
            tool_schema=json.dumps(TOOL_NODE_SCHEMA, indent=2),
            integration_schema=json.dumps(INTEGRATION_SCHEMA, indent=2),
            mcp_client_schema=json.dumps(MCP_CLIENT_SCHEMA, indent=2),
            llm_node_schema=json.dumps(LLM_NODE_SCHEMA, indent=2)
        )
        
        # Prepare input data context for Gemini
        context = "Input Data: " + str(input_data)
        
        # Add system prompt and input data context
        prompt = f"{system}\n\n{context}\n\nYou are an expert agent architect. Return only valid JSON matching the agent schema."
        
        print("🤖 Streaming AI response:")
        print("=" * 50)
        
        # Use streaming to see the response as it comes in
        response = genai.GenerativeModel("gemini-2.5-pro").generate_content(
            prompt, 
            stream=True
        )
        
        # Collect and print the streaming response (but completely block JSON)
        full_text = ""
        json_mode = False
        brace_count = 0
        
        for chunk in response:
            if chunk.text:
                chunk_text = chunk.text
                full_text += chunk_text
                
                # Detect start of JSON in various formats
                if not json_mode:
                    # Look for JSON indicators
                    if (chunk_text.strip().startswith('{"') or 
                        chunk_text.strip().startswith('{\n') or
                        '{"' in chunk_text or
                        "```json" in chunk_text.lower() or
                        chunk_text.strip().startswith('{') and len(chunk_text.strip()) > 1):
                        json_mode = True
                        brace_count = 0
                        print("\n🔧 Generating agent specification...")
                        print("⏳ Please wait while the agent is being created...")
                
                # Count braces to track JSON structure
                if json_mode:
                    brace_count += chunk_text.count('{')
                    brace_count -= chunk_text.count('}')
                    
                    # Check if JSON is complete
                    if brace_count <= 0 and (chunk_text.endswith('}') or 
                                           chunk_text.strip().endswith('}') or
                                           "```" in chunk_text):
                        json_mode = False
                        print("✅ Agent specification complete!")
                
                # Only print if NOT in JSON mode
                if not json_mode:
                    print(chunk_text, end="", flush=True)
        
        print("\n" + "=" * 50)
        print("🤖 AI response complete!")
        
        text = full_text.strip()
        
        # Clean response of markdown code blocks if present
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        # Parse JSON with error handling
        try:
            agent_spec = json.loads(text)
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse agent JSON: {str(e)}")
            print(f"📄 Raw response length: {len(text)} characters")
            print(f"📄 Raw response (first 500 chars):")
            print(text[:500])
            print("\n📄 Raw response (last 500 chars):")
            print(text[-500:])
            
            # Save problematic response for debugging
            debug_file = f"debug_agent_response_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            with open(debug_file, 'w') as f:
                f.write(text)
            print(f"💾 Saved raw response to {debug_file}")
            
            # Try to fix common JSON issues
            print("🔧 Attempting to fix JSON...")
            
            # Fix 1: Replace single quotes with double quotes
            fixed_text = text.replace("'", '"')
            
            # Fix 2: Fix Python boolean/null values
            fixed_text = fixed_text.replace('True', 'true').replace('False', 'false').replace('None', 'null')
            
            # Fix 3: Try to handle unterminated strings by finding the error location
            try:
                # Try to find where the JSON breaks
                lines = fixed_text.split('\n')
                if len(lines) >= 39:  # Error was at line 39
                    print(f"🔍 Problem line 39: {lines[38]}")
                
                # Fix 4: Try to escape unescaped quotes in strings
                import re
                # Find content within double quotes and escape internal quotes
                def fix_quotes(match):
                    content = match.group(1)
                    # Escape internal quotes that aren't already escaped
                    content = re.sub(r'(?<!\\)"', r'\\"', content)
                    return f'"{content}"'
                
                # Apply quote fixing to string values
                fixed_text = re.sub(r'"([^"]*(?:[^"\\]|\\.)*)(?="[,\]}])', fix_quotes, fixed_text)
                
                agent_spec = json.loads(fixed_text)
                print("✅ Successfully fixed JSON!")
                
            except json.JSONDecodeError as e2:
                print(f"❌ Still failed after fixes: {str(e2)}")
                
                # Try one more approach - truncate at the error position and see if we can salvage
                try:
                    error_pos = e.pos if hasattr(e, 'pos') else 2178
                    truncated = text[:error_pos] + '}'  # Try to close the JSON
                    agent_spec = json.loads(truncated)
                    print("✅ Partially recovered JSON by truncation!")
                except:
                    print("❌ Could not recover JSON. Generating minimal fallback agent.")
                    # Create a minimal fallback agent
                    agent_spec = {
                        "name": "Fallback Agent",
                        "description": "Generated due to JSON parsing error",
                        "nodes": [],
                        "edges": [],
                        "input_schema": {},
                        "output_schema": {},
                        "function": "def fallback_agent(input_data):\n    return {'error': 'Agent generation failed', 'input': input_data}",
                        "tools": [],
                        "integrations": [],
                        "mcp_clients": [],
                        "status": "error"
                    }
        
        # Store agent in database
        result = db.agents.insert_one({
            **agent_spec,
            "created_at": datetime.utcnow(),
            "status": "ready"
        })
        
        return {**agent_spec, "agent_id": str(result.inserted_id)}
        
    except Exception as e:
        print(f"❌ Error in agent_developer: {str(e)}")
        raise
