#!/usr/bin/env python3
"""
Test user_interface_claude4 with get_credential_names query
"""

import os
import asyncio
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_get_credentials():
    """Test the user interface with get credential names query"""
    
    print("🧪 Testing user_interface_claude4 with 'get my credential names'")
    print("=" * 60)
    
    # Import the Claude agent flow
    from user_interface_claude4 import run_claude_agent_flow
    
    # Test parameters
    user_query = "get my credential names"
    chat_id = "test_chat_credentials"
    user_id = os.getenv("TEST_USER_ID")
    
    if not user_id:
        print("❌ TEST_USER_ID not set")
        return
    
    print(f"📋 Query: {user_query}")
    print(f"👤 User ID: {user_id}")
    print(f"💬 Chat ID: {chat_id}")
    print("\n" + "=" * 60)
    print("🚀 Starting Claude agent flow...\n")
    
    try:
        # Run the agent flow and collect all events
        events = []
        async for event in run_claude_agent_flow(user_query, chat_id, user_id):
            # Parse the SSE event
            if event.startswith("data: "):
                try:
                    data = json.loads(event[6:])
                    event_type = data.get('type', 'unknown')
                    message = data.get('message', '')
                    
                    # Print different event types differently
                    if event_type == 'thought_stream':
                        print(message, end='', flush=True)
                    elif event_type == 'tool_result':
                        print(f"\n\n📊 TOOL RESULT:\n{'-' * 40}")
                        print(message)
                        print('-' * 40)
                    elif event_type in ['executing', 'tool_prep', 'tool_ready']:
                        print(f"\n🔧 {message}")
                    elif event_type == 'final_response':
                        print(f"\n\n🤖 FINAL RESPONSE:\n{'=' * 40}")
                        print(message)
                        print('=' * 40)
                    else:
                        print(f"\n[{event_type}] {message}")
                    
                    events.append(data)
                except json.JSONDecodeError:
                    print(f"Failed to parse: {event}")
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print(f"\n\n📈 Total events processed: {len(events)}")
    
    # Check if we got credential details
    tool_results = [e for e in events if e.get('type') == 'tool_result']
    if tool_results:
        print(f"\n✅ Found {len(tool_results)} tool result(s)")
        for i, result in enumerate(tool_results):
            msg = result.get('message', '')
            if 'credentials:' in msg:
                print(f"\n🎯 Tool result {i+1} contains credential list!")
                # Count credentials mentioned
                cred_lines = [line for line in msg.split('\n') if line.strip().startswith('-')]
                print(f"   Found {len(cred_lines)} credential entries")

if __name__ == "__main__":
    asyncio.run(test_get_credentials())