#!/usr/bin/env python3
"""
Test script for /api/ai/stream endpoint
Shows real-time streaming responses
"""

import requests
import json
import time

def test_ai_stream(payload):
    """Test the /api/ai/stream endpoint"""
    
    # API endpoint
    url = "http://localhost:8000/api/ai/stream"
    
    # Test payload
    print("🚀 Testing /api/ai/stream endpoint")
    print(f"📤 Sending: {json.dumps(payload, indent=2)}")
    print("\n" + "="*60)
    print("📡 STREAMING RESPONSE:")
    print("="*60)
    
    try:
        # Make streaming request
        with requests.post(url, json=payload, stream=True, timeout=300) as response:
            if response.status_code != 200:
                print(f"❌ Error: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return
            
            # Process streaming data
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith('data: '):
                    data_str = line[6:]  # Remove 'data: ' prefix
                    try:
                        data = json.loads(data_str)
                        step = data.get('step', 'unknown')
                        message = data.get('message', '')
                        msg_type = data.get('type', 'info')
                        
                        # Format output based on type
                        if msg_type == 'thinking':
                            print(f"💭 {message}")
                        elif msg_type == 'status':
                            print(f"✅ {message}")
                        elif msg_type == 'response':
                            print(f"🤖 FINAL: {message}")
                        elif msg_type == 'error':
                            print(f"❌ ERROR: {message}")
                        else:
                            print(f"📋 {step}: {message}")
                            
                        # Check if this is the final response
                        if data.get('final'):
                            print("\n" + "="*60)
                            print("✅ STREAMING COMPLETED")
                            break
                            
                    except json.JSONDecodeError:
                        print(f"📄 Raw: {data_str}")
                        
    except requests.exceptions.Timeout:
        print("❌ Request timed out after 5 minutes")
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - is the server running on localhost:8000?")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

if __name__ == "__main__":
    payload = {
        "user_query": "create a workflow to send daily email reports from my database",
        "chat_id": f"test-chat-{int(time.time())}",
        "user_id": "google-oauth2|102802339888461716238"
    }
    test_ai_stream(payload) 