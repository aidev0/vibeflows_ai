#!/usr/bin/env python3
"""Test script for n8n_runner.py"""

import os
from dotenv import load_dotenv
load_dotenv()

from n8n_runner import run_n8n_workflow

# Test data - you'll need to provide actual user_id and workflow_id
test_input = {
    'user_id': os.getenv('TEST_USER_ID', 'test_user'),  # Replace with actual user_id
    'workflow_id': 'test_workflow',  # Replace with actual workflow_id
    'message': 'Hello from n8n_runner test',
    'timestamp': '2025-01-07T12:00:00Z'
}

print("Testing n8n_runner...")
print(f"Input data: {test_input}")

try:
    result = run_n8n_workflow(test_input)
    
    if result['success']:
        print("\n✅ Workflow executed successfully!")
        print(f"Response: {result['response_data']}")
    else:
        print("\n❌ Workflow execution failed!")
        print(f"Error: {result['error_details']['summary']}")
        print("\nTroubleshooting steps:")
        for step in result['error_details']['troubleshooting_steps']:
            print(f"  - {step}")
            
except Exception as e:
    print(f"\n💥 Error: {str(e)}")