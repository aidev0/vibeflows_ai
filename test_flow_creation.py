#!/usr/bin/env python3

from test_ai_stream import test_ai_stream

# More explicit flow creation request
payload = {
    "user_query": "I need to create a new flow that sends email reports daily from database",
    "chat_id": "test-explicit-flow",
    "user_id": "google-oauth2|102802339888461716238"
}

print("🧪 Testing with explicit flow creation language...")
test_ai_stream(payload) 