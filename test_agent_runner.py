#!/usr/bin/env python3
"""Test script for agent_runner"""

import os
from dotenv import load_dotenv
load_dotenv()

import agent_runner

# Test with Content Planning agent
agent_id = '686772472b0bba1cb2e237be'
input_data = {
    'topic': 'Introduction to Python Programming',
    'target_audience': 'beginners with no programming experience', 
    'content_type': 'tutorial blog post',
    'brand_guidelines': {
        'tone': 'friendly and approachable',
        'style': 'conversational',
        'voice': 'educational'
    }
}

print("Testing Content Planning & Ideation Agent")
print("=" * 50)

try:
    result = agent_runner.run_agent(agent_id, input_data)
    print("\nSuccess! Result:")
    print(result)
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()