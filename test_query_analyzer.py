#!/usr/bin/env python3

from query_analyzer import query_analyzer

# Test the query analyzer directly
test_query = "create a workflow to send daily email reports from my database"

input_data = {
    "user_query": test_query,
    "conversation_history": []
}

print("🔍 Testing Query Analyzer")
print(f"Query: {test_query}")
print("="*50)

result = query_analyzer(input_data)

import json
print("Result:")
print(json.dumps(result, indent=2)) 