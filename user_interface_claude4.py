import os
import json
from bson import ObjectId
from datetime import datetime
from pymongo import MongoClient
import asyncio
import anthropic
from typing import AsyncGenerator, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor

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
            "description": "Develops agents inside the flow",
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
            "description": "Reads from any MongoDB collection with a filter",
            "input_schema": {
                "type": "object",
                "properties": {
                    "collection": {"type": "string"},
                    "filter": {"type": "object"}
                },
                "required": ["collection"]
            }
        }
    ]

# === DATABASE ===
client = MongoClient(os.getenv("MONGODB_URI"))
db = client.vibeflows

# === TOOL MAPPINGS ===
from query_analyzer import query_analyzer
from flow_designer import flow_designer
from flow_developer import flow_developer_streaming
from n8n_developer import n8n_developer
from flow_runner import flow_runner

def mongodb_tool(input_data):
    collection_name = input_data["collection"]
    query_filter = input_data.get("filter", {})

    try:
        collection = db[collection_name]
        docs = list(collection.find(query_filter).limit(10))
        for doc in docs:
            doc["_id"] = str(doc["_id"])
        return {"results": docs, "message": f"✅ Retrieved {len(docs)} document(s) from `{collection_name}`"}
    except Exception as e:
        return {"error": str(e), "message": "❌ Failed to run MongoDB query"}

TOOLS = {
    "query_analyzer": query_analyzer,
    "flow_designer": flow_designer,
    "flow_developer": flow_developer_streaming,
    "n8n_developer": n8n_developer,
    "flow_runner": flow_runner,
    "mongodb_tool": mongodb_tool
}

# === HELPERS ===
def save_message(chat_id, role, msg_type, text, content=None):
    db.messages.insert_one({
        "chat_id": chat_id,
        "role": role,
        "type": msg_type,
        "text": text,
        "content": content or {},
        "timestamp": datetime.now()
    })

def _stream_event(text, type="status", final=False):
    return f"data: {json.dumps({'type': type, 'message': text, 'final': final})}\n\n"

# === CLAUDE SETUP ===
claude_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

async def run_claude_agent_flow(user_query: str, chat_id: str, user_id: str) -> AsyncGenerator[str, None]:
    """
    Claude agent flow with streaming thoughts and responses
    """
    
    if not user_query.strip():
        # Handle empty query
        try:
            response = claude_client.messages.create(
                model="claude-sonnet-4-20250514",  # Claude 4 Sonnet
                max_tokens=1024,
                messages=[{"role": "user", "content": "Hello! Please greet me as an automation assistant."}]
            )
            greeting = response.content[0].text
            save_message(chat_id, "assistant", "text", greeting)
            yield _stream_event(greeting, final=True)
            return
        except Exception as e:
            yield _stream_event(f"❌ Error: {str(e)}", "error", final=True)
            return

    # Build system prompt
    system_prompt = """You are an expert automation assistant. Think through problems step by step and explain your reasoning clearly.

Available tools:
- query_analyzer: Analyze user queries for intent and requirements
- flow_designer: Design automation flows from requirements  
- flow_developer: Develop agents within flows
- n8n_developer: Generate and deploy n8n workflows
- mongodb_tool: Query MongoDB collections (flows, agents, credentials, integrations, llm_models)

Approach each task systematically:
1. First understand what the user wants (use query_analyzer if needed)
2. Explain your reasoning and planned approach
3. Use tools in logical sequence
4. Provide clear progress updates
5. Think aloud about your decisions

Be conversational and share your thought process as you work through the automation challenge."""

    # Get conversation history
    previous_messages = list(db.messages.find({"chat_id": chat_id}).sort("timestamp", 1))[-8:]
    
    # Build messages array
    messages = []
    
    # Add conversation history
    for msg in previous_messages:
        if msg["role"] in ["user", "assistant"] and msg["type"] == "text":
            messages.append({
                "role": msg["role"],
                "content": msg["text"]
            })
    
    # Add current user query
    messages.append({
        "role": "user",
        "content": user_query
    })

    max_iterations = 5
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        yield _stream_event(f"🤖 Agent iteration {iteration}/{max_iterations}", "iteration")
        
        try:
            # Stream Claude 4's response with tool use
            with claude_client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
                tools=get_tool_schemas()
            ) as stream:
                
                current_text = ""
                tool_calls = []
                current_tool_input = ""
                last_tool_input_time = 0
                import time
                
                for event in stream:
                    if event.type == "message_start":
                        yield _stream_event("🧠 Analyzing the request...", "thinking")
                        await asyncio.sleep(0.1)  # Small delay for readability
                    
                    elif event.type == "content_block_start":
                        if event.content_block.type == "text":
                            yield _stream_event("💭 Thinking through the problem...", "reasoning_start")
                        elif event.content_block.type == "tool_use":
                            tool_name = event.content_block.name
                            yield _stream_event(f"🔧 Preparing to use {tool_name}...", "tool_prep")
                            current_tool_input = ""
                    
                    elif event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            # Stream Claude's reasoning in chunks for better readability
                            text_chunk = event.delta.text
                            current_text += text_chunk
                            
                            # Buffer text and send in meaningful chunks
                            if len(text_chunk) > 20 or text_chunk.endswith(('.', '!', '?', ':')):
                                yield _stream_event(text_chunk, "thought_stream")
                                await asyncio.sleep(0.05)  # Small delay between thoughts
                        
                        elif event.delta.type == "input_json_delta":
                            # Throttle tool input updates to avoid spam
                            current_time = time.time()
                            current_tool_input += event.delta.partial_json
                            
                            if current_time - last_tool_input_time > 0.5:  # Update every 500ms max
                                yield _stream_event("📝 Building tool parameters...", "tool_input")
                                last_tool_input_time = current_time
                                await asyncio.sleep(0.1)
                    
                    elif event.type == "content_block_stop":
                        if hasattr(event.content_block, 'type') and event.content_block.type == "tool_use":
                            tool_calls.append({
                                "name": event.content_block.name,
                                "input": event.content_block.input,
                                "id": event.content_block.id
                            })
                            yield _stream_event(f"✅ Ready to execute {event.content_block.name}", "tool_ready")
                            await asyncio.sleep(0.2)
                
                # Save Claude's reasoning
                if current_text.strip():
                    save_message(chat_id, "assistant", "text", current_text)
                    yield _stream_event("💡 Reasoning complete", "reasoning_done")
                    await asyncio.sleep(0.3)
                
                # Execute tools sequentially
                tool_results = []
                for i, tool_call in enumerate(tool_calls):
                    tool_name = tool_call["name"]
                    tool_input = tool_call["input"]
                    tool_id = tool_call["id"]
                    
                    yield _stream_event(f"🚀 Executing {tool_name} ({i+1}/{len(tool_calls)})...", "executing")
                    await asyncio.sleep(0.2)
                    
                    try:
                        if tool_name in TOOLS:
                            # Run ALL tools in thread pool to prevent blocking
                            def run_tool_sync():
                                """Run tool synchronously in thread"""
                                if tool_name == "flow_developer":
                                    if not tool_input.get("flow_id"):
                                        return {"status": "error", "message": "❌ Missing flow_id"}
                                    
                                    # Collect streaming updates
                                    messages = []
                                    from flow_developer import flow_developer_streaming
                                    import asyncio
                                    
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    
                                    try:
                                        async def collect():
                                            async for update in flow_developer_streaming(tool_input):
                                                messages.append(update.get("message", ""))
                                        
                                        loop.run_until_complete(collect())
                                    finally:
                                        loop.close()
                                    
                                    return {"status": "completed", "message": "Flow development finished", "details": messages}
                                
                                elif tool_name == "n8n_developer":
                                    # Check credentials first
                                    from pymongo import MongoClient
                                    import os
                                    db = MongoClient(os.getenv("MONGODB_URI")).vibeflows
                                    
                                    creds = list(db.credentials.find({"user_id": str(user_id)}))
                                    has_url = any(c["name"] == "N8N_URL" for c in creds)
                                    has_key = any(c["name"] == "N8N_API_KEY" for c in creds)
                                    
                                    if not (has_url and has_key):
                                        return {"status": "skipped", "message": "⚠️ Missing N8N credentials (N8N_URL and N8N_API_KEY)"}
                                    else:
                                        tool_input["user_id"] = str(user_id)
                                        return TOOLS[tool_name](tool_input)
                                
                                else:
                                    # Regular synchronous tools
                                    return TOOLS[tool_name](tool_input)
                            
                            # Execute tool in thread pool
                            loop = asyncio.get_event_loop()
                            with ThreadPoolExecutor(max_workers=1) as executor:
                                result = await loop.run_in_executor(executor, run_tool_sync)
                            
                            # Handle flow_developer special case
                            if tool_name == "flow_developer" and result.get("details"):
                                for detail_msg in result["details"]:
                                    if detail_msg.strip():
                                        yield _stream_event(detail_msg, "tool_stream")
                                        save_message(chat_id, "assistant", "text", detail_msg)
                                        await asyncio.sleep(0.1)
                            
                            # Format result message with better context
                            if tool_name == "flow_designer" and result.get("_id"):
                                # Include flow_id in the message for Claude to use
                                flow_id = str(result["_id"])
                                flow_name = result.get("name", "Unnamed Flow")
                                result_msg = f"✅ Flow '{flow_name}' created successfully with ID: {flow_id}. Use this flow_id for development: {flow_id}"
                                # Store the ID for easy access
                                result["flow_id"] = flow_id
                            elif tool_name == "mongodb_tool":
                                # Better formatting for MongoDB results
                                docs = result.get("results", [])
                                if docs and "flows" in tool_input.get("collection", ""):
                                    flow_list = []
                                    for doc in docs:
                                        flow_list.append(f"- {doc.get('name', 'Unnamed')}: {doc.get('_id')}")
                                    result_msg = f"✅ Found {len(docs)} flows:\n" + "\n".join(flow_list)
                                else:
                                    result_msg = result.get("message", f"✅ {tool_name} completed")
                            else:
                                result_msg = result.get("summary") or result.get("message") or f"✅ {tool_name} completed"
                            
                            yield _stream_event(result_msg, "tool_result")
                            save_message(chat_id, "assistant", "text", result_msg)
                            await asyncio.sleep(0.2)
                            
                            # Store result for Claude with better formatting
                            tool_result_content = result_msg
                            if tool_name == "flow_designer" and result.get("flow_id"):
                                # Include structured data for Claude
                                tool_result_content = f"{result_msg}\n\nFlow ID for development: {result['flow_id']}"
                            elif tool_name == "mongodb_tool" and result.get("results"):
                                # Include the actual data structure
                                tool_result_content = f"{result_msg}\n\nData: {json.dumps(result['results'], indent=2)}"
                            
                            tool_results.append({
                                "tool_use_id": tool_id,
                                "type": "tool_result",
                                "content": tool_result_content
                            })
                        
                        else:
                            error_msg = f"❌ Unknown tool: {tool_name}"
                            yield _stream_event(error_msg, "error")
                            tool_results.append({
                                "tool_use_id": tool_id,
                                "type": "tool_result", 
                                "is_error": True,
                                "content": error_msg
                            })
                    
                    except Exception as e:
                        error_msg = f"❌ Error in {tool_name}: {str(e)}"
                        yield _stream_event(error_msg, "error")
                        save_message(chat_id, "assistant", "text", error_msg)
                        tool_results.append({
                            "tool_use_id": tool_id,
                            "type": "tool_result",
                            "is_error": True,
                            "content": error_msg
                        })
                
                # If we executed tools, continue conversation with results
                if tool_results:
                    # Add assistant message and tool results to conversation
                    if current_text.strip():
                        messages.append({
                            "role": "assistant",
                            "content": [
                                {"type": "text", "text": current_text}
                            ] + [
                                {"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc["input"]}
                                for tc in tool_calls
                            ]
                        })
                    
                    # Add tool results
                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })
                    
                    yield _stream_event("🔄 Continuing with tool results...", "continue")
                    await asyncio.sleep(0.5)  # Pause before next iteration
                else:
                    # No tools used, we're done
                    break
        
        except Exception as e:
            yield _stream_event(f"❌ Agent error: {str(e)}", "error")
            break
    
    yield _stream_event("🎉 Agent workflow completed!", "final", final=True)

# === EXAMPLE USAGE ===
async def example_usage():
    """Example of using the streaming agent"""
    chat_id = "example_chat_123"
    user_id = "google-oauth2|102802339888461716238"
    user_query = "Create a marketing automation flow to segment customers based on email engagement"
    
    print("🚀 Starting streaming agent...")
    
    async for stream_event in run_claude_agent_flow(user_query, chat_id, user_id):
        print(stream_event.rstrip())

if __name__ == "__main__":
    # For regular Python scripts
    try:
        asyncio.run(example_usage())
    except RuntimeError:
        # For Jupyter notebooks or environments with existing event loops
        import nest_asyncio
        nest_asyncio.apply()
        asyncio.run(example_usage())

# Alternative for Jupyter/notebook environments:
# await example_usage()