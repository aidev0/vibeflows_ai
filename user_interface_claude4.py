import os
import json
from bson import ObjectId
from datetime import datetime
from pymongo import MongoClient
import asyncio
import anthropic
from typing import AsyncGenerator, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
import time

# === TOOL IMPORTS ===
from tools import get_tool_schemas, TOOLS

# === DATABASE ===
client = MongoClient(os.getenv("MONGODB_URI"))
db = client.vibeflows


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
    Claude agent flow with streaming thoughts and responses - Fixed with proper N8N timeouts
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

    # Build system prompt with user context
    system_prompt = f"""You are an expert automation assistant. Think through problems step by step and explain your reasoning clearly.

Current session context:
- User ID: {user_id}
- Chat ID: {chat_id}

Available tools:
- query_analyzer: Analyze user queries for intent and requirements
- flow_designer: Design automation flows from requirements  
- flow_developer: Develop agents within flows using Claude 4 sequential processing
- flow_developer_gemini: Develop agents within flows using Gemini with multiprocessing
- n8n_developer: Generate and deploy n8n workflows (may take up to 3 minutes)
- mongodb_tool: Query MongoDB collections (agents, flows, runs, n8n_workflows only)
- check_credentials: Check if user has access to required credentials
- get_n8n_workflows: Get user's n8n workflows and display their N8N URLs
- get_credential_names: Get user's credential names and descriptions

Approach each task systematically:
1. First understand what the user wants (use query_analyzer if needed)
2. Explain your reasoning and planned approach
3. Use tools in logical sequence
4. Provide clear progress updates
5. Think aloud about your decisions

When querying databases, you can use the current user_id ({user_id}) and chat_id ({chat_id}) to filter results appropriately.

If user asks for n8n deploy, use the n8n_developer tool. 
Don't ask for credentials, just deploy. 
You are not allowed to send the credentials to the user.
Do not send the credentials to the user in any way.

If API call fails because of missing credentials, send the message with key "missing_credentials" and a list of credentials as a string.

Be conversational and share your thought process as you work through the automation challenge.
Note: N8N deployments can take up to 3 minutes - this is normal for complex workflows."""

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
                model="claude-sonnet-4-20250514",  # Claude 4 Sonnet
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
                tools=get_tool_schemas()
            ) as stream:
                
                current_text = ""
                tool_calls = []
                current_tool_input = ""
                last_tool_input_time = 0
                
                print("🤖 Claude AI Streaming Response:")
                print("=" * 60)
                
                for event in stream:
                    if event.type == "message_start":
                        print("🚀 [STREAM START]")
                        yield _stream_event("🧠 Analyzing the request...", "thinking")
                        await asyncio.sleep(0.1)  # Small delay for readability
                    
                    elif event.type == "content_block_start":
                        if event.content_block.type == "text":
                            print("💭 [TEXT BLOCK START]")
                            yield _stream_event("💭 Thinking through the problem...", "reasoning_start")
                        elif event.content_block.type == "tool_use":
                            tool_name = event.content_block.name
                            print(f"🔧 [TOOL START] {tool_name}")
                            yield _stream_event(f"🔧 Preparing to use {tool_name}...", "tool_prep")
                            current_tool_input = ""
                    
                    elif event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            # Stream Claude's reasoning in chunks for better readability
                            text_chunk = event.delta.text
                            print(text_chunk, end="", flush=True)  # Print Claude's thoughts in real-time
                            current_text += text_chunk
                            
                            # Stream all text chunks immediately for real-time experience
                            yield _stream_event(text_chunk, "thought_stream")
                            await asyncio.sleep(0.02)  # Small delay between chunks
                        
                        elif event.delta.type == "input_json_delta":
                            # Throttle tool input updates to avoid spam
                            current_time = time.time()
                            current_tool_input += event.delta.partial_json
                            print(f"[TOOL_INPUT] {event.delta.partial_json}", end="", flush=True)
                            
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
                            print(f"\n✅ [TOOL COMPLETE] {event.content_block.name}")
                            print(f"🔧 [TOOL INPUT] {json.dumps(event.content_block.input, indent=2)}")
                            yield _stream_event(f"✅ Ready to execute {event.content_block.name}", "tool_ready")
                            await asyncio.sleep(0.2)
                        elif hasattr(event.content_block, 'type') and event.content_block.type == "text":
                            print("\n💭 [TEXT BLOCK COMPLETE]")
                
                print("\n" + "=" * 60)
                print("🤖 Claude streaming complete!")
                
                # Save Claude's reasoning
                if current_text.strip():
                    save_message(chat_id, "assistant", "text", current_text)
                    yield _stream_event("💡 Reasoning complete", "reasoning_done")
                    await asyncio.sleep(0.3)
                
                # === ENHANCED TOOL EXECUTION WITH PROPER TIMEOUTS ===
                tool_results = []
                for i, tool_call in enumerate(tool_calls):
                    tool_name = tool_call["name"]
                    tool_input = tool_call["input"]
                    tool_id = tool_call["id"]
                    
                    # Add user_id and chat_id to all tool inputs
                    tool_input["user_id"] = user_id
                    tool_input["chat_id"] = chat_id
                    
                    # Set appropriate timeout based on tool type
                    timeout = 240                    
                    yield _stream_event(f"🚀 Executing {tool_name} ({i+1}/{len(tool_calls)})...", "executing")
                    
                    # Special handling for n8n with progress updates
                    progress_task = None
                    if tool_name == "n8n_developer":
                        yield _stream_event("⏱️ N8N deployment may take up to 3 minutes...", "info")
                        
                        # Create a simple progress tracking task
                        async def n8n_progress_tracker():
                            """Track n8n deployment progress"""
                            progress_msgs = [
                                "📡 Connecting to n8n server...",
                                "📋 Validating workflow structure...", 
                                "⚙️ Creating workflow nodes...",
                                "🔗 Setting up node connections...",
                                "🎯 Configuring triggers and actions...",
                                "✅ Almost done, finalizing deployment..."
                            ]
                            try:
                                for idx, msg in enumerate(progress_msgs):
                                    await asyncio.sleep(30)  # Every 30 seconds
                                    print(f"📈 N8N Progress: {msg} ({idx+1}/{len(progress_msgs)})")
                            except asyncio.CancelledError:
                                print("🛑 N8N progress tracking cancelled")
                        
                        progress_task = asyncio.create_task(n8n_progress_tracker())
                    
                    await asyncio.sleep(0.2)
                    
                    try:
                        if tool_name in TOOLS:
                            # Special handling for streaming flow_developer
                            if tool_name == "flow_developer":
                                yield _stream_event("🚀 Starting flow development with Claude 4 sequential processing...", "executing")
                                
                                from flow_developer import flow_developer_claude4_sequential
                                
                                # Stream flow development updates in real-time
                                async for update in flow_developer_claude4_sequential(tool_input):
                                    message = update.get("message", "")
                                    update_type = update.get("type", "status")
                                    
                                    # Format different types of updates differently
                                    if update_type == "agent_stream":
                                        # This is the captured Gemini streaming output
                                        yield _stream_event(f"🤖 {message}", "agent_ai_stream")
                                    elif update_type == "agent_stream_error":
                                        # This is captured output from failed agent creation
                                        yield _stream_event(f"❌ {message}", "agent_ai_error")
                                    elif update_type in ["process_update", "agent_complete", "progress_update"]:
                                        # Regular flow development updates
                                        yield _stream_event(message, "flow_progress")
                                    else:
                                        # Other messages
                                        yield _stream_event(message, "tool_stream")
                                    
                                    await asyncio.sleep(0.05)  # Small delay for readability
                                
                                # Set result for Claude
                                result_msg = "✅ Flow development completed with Claude 4 sequential agent creation"
                                yield _stream_event(result_msg, "tool_result")
                                save_message(chat_id, "assistant", "text", result_msg)
                                
                                tool_results.append({
                                    "tool_use_id": tool_id,
                                    "type": "tool_result",
                                    "content": result_msg
                                })
                                continue  # Skip the normal executor path
                            
                            # Run ALL other tools in thread pool to prevent blocking
                            def run_tool_sync():
                                """Run tool synchronously in thread"""
                                if tool_name == "n8n_developer":
                                    # Check credentials first
                                    from pymongo import MongoClient
                                    import os
                                    db = MongoClient(os.getenv("MONGODB_URI")).vibeflows
                                    
                                    print(f"🔍 Checking N8N credentials for user_id: {user_id}")
                                    
                                    # Simple fix: Replace URL-encoded pipe with actual pipe
                                    clean_user_id = str(user_id).replace('%7C', '|').replace('%7c', '|')
                                    print(f"🔍 Cleaned user_id: {clean_user_id}")
                                    
                                    creds = list(db.credentials.find({"user_id": clean_user_id}))
                                    print(f"🔍 Found {len(creds)} credentials for this user")
                                    
                                    has_url = any(c["name"] == "N8N_URL" for c in creds)
                                    has_key = any(c["name"] == "N8N_API_KEY" for c in creds)
                                    
                                    if not (has_url and has_key):
                                        return {"status": "skipped", "message": "⚠️ Missing N8N credentials (N8N_URL and N8N_API_KEY)", "credentials": creds}
                                    else:
                                        return TOOLS[tool_name](tool_input)
                                
                                else:
                                    # Regular synchronous tools
                                    return TOOLS[tool_name](tool_input)
                            
                            # Execute tool with proper timeout
                            loop = asyncio.get_event_loop()
                            with ThreadPoolExecutor(max_workers=1) as executor:
                                result = await asyncio.wait_for(
                                    loop.run_in_executor(executor, run_tool_sync),
                                    timeout=timeout
                                )
                            
                            # Cancel progress updates if they're running
                            if progress_task and not progress_task.done():
                                progress_task.cancel()
                                try:
                                    await progress_task
                                except asyncio.CancelledError:
                                    pass
                            
                            # Format result message with better context
                            if tool_name == "flow_designer" and result.get("_id"):
                                flow_id = str(result["_id"])
                                flow_name = result.get("name", "Unnamed Flow")
                                result_msg = f"✅ Flow '{flow_name}' created successfully with ID: {flow_id}. Use this flow_id for development: {flow_id}"
                                result["flow_id"] = flow_id
                            elif tool_name == "mongodb_tool":
                                docs = result.get("results", [])
                                if docs and "flows" in tool_input.get("collection", ""):
                                    flow_list = []
                                    for doc in docs:
                                        flow_list.append(f"- {doc.get('name', 'Unnamed')}: {doc.get('_id')}")
                                    result_msg = f"✅ Found {len(docs)} flows:\n" + "\n".join(flow_list)
                                else:
                                    result_msg = result.get("message", f"✅ {tool_name} completed")
                            elif tool_name == "n8n_developer":
                                # Special handling for n8n results
                                if result.get("status") == "deployed":
                                    result_msg = f"🎉 {result.get('message', 'N8N workflow deployed successfully!')}"
                                    if result.get("workflow_url"):
                                        result_msg += f"\n🔗 Workflow URL: {result['workflow_url']}"
                                elif result.get("status") == "timeout":
                                    result_msg = f"⏰ {result.get('message', 'N8N deployment timed out')}"
                                elif result.get("status") == "skipped":
                                    result_msg = result.get("message", "N8N deployment skipped")
                                else:
                                    result_msg = result.get("summary") or result.get("message") or "✅ N8N workflow processed"
                            else:
                                result_msg = result.get("summary") or result.get("message") or f"✅ {tool_name} completed"
                            
                            yield _stream_event(result_msg, "tool_result")
                            save_message(chat_id, "assistant", "text", result_msg)
                            await asyncio.sleep(0.2)
                            
                            # Store result for Claude with better formatting
                            tool_result_content = result_msg
                            if tool_name == "flow_designer" and result.get("flow_id"):
                                tool_result_content = f"{result_msg}\n\nFlow ID for development: {result['flow_id']}"
                            elif tool_name == "mongodb_tool" and result.get("results"):
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
                    
                    except asyncio.TimeoutError:
                        # Cancel progress updates if they're running
                        if progress_task and not progress_task.done():
                            progress_task.cancel()
                            try:
                                await progress_task
                            except asyncio.CancelledError:
                                pass
                        
                        # Handle timeout based on tool type
                        if tool_name == "n8n_developer":
                            timeout_msg = "⏰ N8N deployment timed out after 4 minutes. This might be due to server load or network connectivity issues."
                            suggestion_msg = "💡 You can try deploying again, or I can provide the workflow JSON for manual import."
                            
                            yield _stream_event(timeout_msg, "timeout")
                            yield _stream_event(suggestion_msg, "suggestion")
                            
                            # Store timeout info for potential fallback
                            save_message(chat_id, "system", "timeout", "n8n_deployment_timeout", {
                                "tool_input": tool_input,
                                "timestamp": datetime.now().isoformat()
                            })
                            
                            tool_results.append({
                                "tool_use_id": tool_id,
                                "type": "tool_result",
                                "is_error": True,
                                "content": f"{timeout_msg} {suggestion_msg}"
                            })
                        else:
                            timeout_msg = f"⏰ {tool_name} timed out after {timeout} seconds"
                            yield _stream_event(timeout_msg, "timeout")
                            tool_results.append({
                                "tool_use_id": tool_id,
                                "type": "tool_result",
                                "is_error": True,
                                "content": timeout_msg
                            })
                    
                    except Exception as e:
                        # Cancel progress updates if they're running
                        if progress_task and not progress_task.done():
                            progress_task.cancel()
                            try:
                                await progress_task
                            except asyncio.CancelledError:
                                pass
                        
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
                    # Add assistant message with tool calls
                    assistant_content = []
                    if current_text.strip():
                        assistant_content.append({"type": "text", "text": current_text})
                    
                    # Add tool use blocks
                    for tc in tool_calls:
                        assistant_content.append({
                            "type": "tool_use", 
                            "id": tc["id"], 
                            "name": tc["name"], 
                            "input": tc["input"]
                        })
                    
                    messages.append({
                        "role": "assistant",
                        "content": assistant_content
                    })
                    
                    # Add tool results as user message
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