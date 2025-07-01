#!/bin/bash
# Quick cURL test for /api/ai/stream endpoint

echo "🚀 Testing /api/ai/stream with cURL"
echo "=================================="

curl -X POST http://localhost:8000/api/ai/stream \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "create a workflow to send daily email reports from my database",
    "chat_id": "test-curl-chat-'$(date +%s)'",
    "user_id": "google-oauth2|102802339888461716238"
  }' \
  --no-buffer 