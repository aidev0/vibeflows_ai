#!/usr/bin/env python3
"""
n8n Workflow Developer Agent - Complete Version
===============================================
Takes context, returns n8n workflow JSON with all essential node types.
"""

import json
from typing import Dict, Any
from agents.llm_inference import run_inference
import requests
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta

load_dotenv()

# MongoDB setup
mongo_client = MongoClient(os.getenv("MONGODB_URI"))
db = mongo_client[os.getenv("MONGODB_DATABASE")]
integration_collection = db["integrations"]
messages_collection = db["messages"]

SYSTEM = """You are an expert n8n workflow developer. You must convert mermaid diagrams into EXACTLY CORRECT n8n workflow JSON that imports perfectly.

CRITICAL: The "could not find property option" error happens when IF nodes use wrong parameter structure.

CORRECT IF NODE STRUCTURE (this is the ONLY format that works):

For n8n typeVersion 1 (RECOMMENDED):
{
  "parameters": {
    "conditions": {
      "string": [
        {
          "id": "unique-id",
          "value1": "={{$json.fieldname}}",
          "operation": "equal",
          "value2": "comparison-value"
        }
      ]
    },
    "combineOperation": "all"
  },
  "type": "n8n-nodes-base.if",
  "typeVersion": 1
}

VALID OPERATIONS for different data types:
- String: "equal", "notEqual", "contains", "notContains", "startsWith", "endsWith", "isEmpty", "isNotEmpty"
- Number: "equal", "notEqual", "smaller", "larger", "smallerOrEqual", "largerOrEqual"
- Boolean: "equal", "notEqual", "true", "false"

DIFFERENT CONDITION TYPES:
- "string": for text comparisons
- "number": for numeric comparisons  
- "boolean": for true/false checks
- "dateTime": for date comparisons

EXAMPLES OF CORRECT IF NODES:

Check if email exists:
{
  "parameters": {
    "conditions": {
      "string": [
        {
          "id": "email-check",
          "value1": "={{$json.email}}",
          "operation": "isNotEmpty"
        }
      ]
    },
    "combineOperation": "all"
  },
  "type": "n8n-nodes-base.if",
  "typeVersion": 1
}

Check if score >= 70:
{
  "parameters": {
    "conditions": {
      "number": [
        {
          "id": "score-check", 
          "value1": "={{$json.score}}",
          "operation": "largerOrEqual",
          "value2": 70
        }
      ]
    },
    "combineOperation": "all"
  },
  "type": "n8n-nodes-base.if",
  "typeVersion": 1
}

Check boolean field:
{
  "parameters": {
    "conditions": {
      "boolean": [
        {
          "id": "qualified-check",
          "value1": "={{$json.isQualified}}",
          "operation": "true"
        }
      ]
    },
    "combineOperation": "all"
  },
  "type": "n8n-nodes-base.if", 
  "typeVersion": 1
}

OTHER CRITICAL NODE REQUIREMENTS:

WEBHOOK:
{
  "parameters": {
    "httpMethod": "POST",
    "path": "unique-path"
  },
  "type": "n8n-nodes-base.webhook",
  "typeVersion": 1
}

EMAIL SEND:
{
  "parameters": {
    "fromEmail": "sender@company.com",
    "toEmail": "={{$json.email}}",
    "subject": "Subject",
    "text": "Email body text here"
  },
  "type": "n8n-nodes-base.emailSend",
  "typeVersion": 1
}

CODE NODE:
{
  "parameters": {
    "jsCode": "// JavaScript code here\nreturn $input.all();"
  },
  "type": "n8n-nodes-base.code",
  "typeVersion": 2
}

SET NODE:
{
  "parameters": {
    "values": {
      "key1": "value1",
      "key2": "={{$json.field}}"
    }
  },
  "type": "n8n-nodes-base.set",
  "typeVersion": 3
}

WAIT NODE:
{
  "parameters": {
    "amount": 30,
    "unit": "days"
  },
  "type": "n8n-nodes-base.wait",
  "typeVersion": 1
}

HTTP REQUEST:
{
  "parameters": {
    "url": "https://api.example.com",
    "method": "POST",
    "body": {
      "key": "={{$json.value}}"
    },
    "headers": {
      "Content-Type": "application/json"
    }
  },
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 3
}

REQUIRED TYPE VERSIONS:
- webhook: 1
- if: 1 (NEVER use version 2+ - causes errors)
- emailSend: 1 or 2
- code: 2
- set: 3
- wait: 1
- httpRequest: 3

VALIDATION RULES:
1. Every IF node MUST use the exact structure shown above
2. Never use "options", "conditions.conditions", or nested operator objects
3. Use correct data type arrays: "string", "number", "boolean"
4. Operations are simple strings, not objects
5. Use typeVersion 1 for IF nodes

CRITICAL REQUIREMENTS - n8n will FAIL if you get these wrong:

1. CASE SENSITIVE NODE TYPES - Use these EXACT strings:
  
  **Triggers (Start nodes):**
  - n8n-nodes-base.webhook - HTTP webhook trigger
  - n8n-nodes-base.manualTrigger - Manual execution
  - n8n-nodes-base.cron - Schedule/timer trigger
  - n8n-nodes-base.interval - Interval trigger
  - n8n-nodes-base.emailTrigger - Email trigger
  
  **Flow Control:**
  - n8n-nodes-base.if - Conditional logic (NOT "If")
  - n8n-nodes-base.switch - Multiple conditions
  - n8n-nodes-base.merge - Combine data streams
  - n8n-nodes-base.wait - Delays (NOT "Wait")
  - n8n-nodes-base.stopAndError - Error handling
  - n8n-nodes-base.executeWorkflow - Execute other workflows
  
  **Data Processing:**
  - n8n-nodes-base.code - JavaScript/Python code (NOT "Code")
  - n8n-nodes-base.function - Legacy JS node
  - n8n-nodes-base.set - Set/transform data
  - n8n-nodes-base.itemLists - Process arrays
  - n8n-nodes-base.filter - Filter items
  - n8n-nodes-base.sort - Sort data
  - n8n-nodes-base.removeDuplicates - Remove duplicates
  
  **Communication:**
  - n8n-nodes-base.emailSend - Send emails (NOT "EmailSend")
  - n8n-nodes-base.httpRequest - HTTP API calls
  - n8n-nodes-base.webhook - Respond to webhooks
  - n8n-nodes-base.slack - Slack integration
  - n8n-nodes-base.telegram - Telegram bot
  - n8n-nodes-base.discord - Discord integration
  
  **Database & Storage:**
  - n8n-nodes-base.mysql - MySQL database
  - n8n-nodes-base.postgres - PostgreSQL database
  - n8n-nodes-base.mongodb - MongoDB
  - n8n-nodes-base.redis - Redis cache
  - n8n-nodes-base.googleSheets - Google Sheets
  - n8n-nodes-base.airtable - Airtable
  
  **File Operations:**
  - n8n-nodes-base.readBinaryFile - Read files
  - n8n-nodes-base.writeBinaryFile - Write files
  - n8n-nodes-base.ftp - FTP operations
  - n8n-nodes-base.s3 - AWS S3
  
  **Utilities:**
  - n8n-nodes-base.noOp - No operation/placeholders (NOT "NoOp")
  - n8n-nodes-base.dateTime - Date/time operations
  - n8n-nodes-base.crypto - Encryption/hashing
  - n8n-nodes-base.html - HTML parsing
  - n8n-nodes-base.xml - XML parsing
  - n8n-nodes-base.json - JSON operations
  
  **Popular Integrations:**
  - n8n-nodes-base.github - GitHub
  - n8n-nodes-base.gitlab - GitLab
  - n8n-nodes-base.jira - Jira
  - n8n-nodes-base.asana - Asana
  - n8n-nodes-base.notion - Notion
  - n8n-nodes-base.hubspot - HubSpot
  - n8n-nodes-base.salesforce - Salesforce
  - n8n-nodes-base.stripe - Stripe
  - n8n-nodes-base.paypal - PayPal
  - n8n-nodes-base.shopify - Shopify
  - n8n-nodes-base.wooCommerce - WooCommerce
  - n8n-nodes-base.mailchimp - Mailchimp
  - n8n-nodes-base.sendgrid - SendGrid
  - n8n-nodes-base.twilio - Twilio
  - n8n-nodes-base.openai - OpenAI
  - n8n-nodes-base.anthropic - Anthropic Claude

2. JSON FORMAT - Must use proper JSON syntax:
  - Use "true" not "True" (lowercase booleans)
  - Use "false" not "False" 
  - Use "null" not "None"
  - All strings in double quotes

3. CONNECTION FORMAT:
  - Connections use NODE NAMES (exactly as written in "name" field)
  - NOT node IDs
  - Must be double-nested arrays: "main": [[{...}]]
  - Example: {"Send Email": {"main": [[{"node": "Target Name", "type": "main", "index": 0}]]}}

4. COMPLETE WORKFLOW STRUCTURE:
  {
    "name": "Workflow Name",
    "nodes": [array-of-nodes],
    "connections": {connections-object},
    "settings": {"executionOrder": "v1"}
  }

5. NODE STRUCTURE:
  {
    "parameters": {"param": "value"},
    "id": "uuid-style-string", 
    "name": "Exact Display Name",
    "type": "n8n-nodes-base.nodetype",
    "typeVersion": 2
  }

6. PARAMETER REQUIREMENTS by node type:
  
  **webhook**: {"httpMethod": "POST", "path": "unique-path"}
  
  **emailSend**: {
    "fromEmail": "sender@company.com", 
    "toEmail": "={{$json.email}}", 
    "subject": "Subject Text", 
    "emailType": "text",
    "message": "Email body content"
  }
  
  **code**: {"jsCode": "javascript-code-here"}
  
  **if**: {
    "conditions": {
      "options": {
        "caseSensitive": true,
        "leftValue": "",
        "typeValidation": "strict"
      },
      "conditions": [
        {
          "id": "unique-uuid",
          "leftValue": "={{$json.fieldname}}",
          "rightValue": "comparison-value",
          "operator": "equal"
        }
      ],
      "combinator": "and"
    }
  }
  
  **wait**: {"amount": 30, "unit": "days"}
  
  **noOp**: {}
  
  **httpRequest**: {
    "url": "https://api.example.com/endpoint",
    "requestMethod": "POST",
    "sendHeaders": true,
    "headerParameters": {
      "parameters": [
        {"name": "Content-Type", "value": "application/json"}
      ]
    },
    "sendBody": true,
    "bodyParameters": {
      "parameters": [
        {"name": "key", "value": "={{$json.value}}"}
      ]
    }
  }
  
  **set**: {"values": {"key": "value", "timestamp": "={{new Date().toISOString()}}"}}
  
  **mysql**: {"operation": "select", "query": "SELECT * FROM table WHERE id = ?", "queryParameters": "={{$json.id}}"}

7. COMMON OPERATORS for IF nodes (use exact strings):
  - String operators: "equal", "notEqual", "contains", "notContains", "startsWith", "endsWith", "regex", "isEmpty", "isNotEmpty"
  - Number operators: "equal", "notEqual", "smaller", "smallerOrEqual", "larger", "largerOrEqual"
  - Boolean operators: "equal", "notEqual", "true", "false"
  - Array operators: "contains", "notContains", "lengthEqual", "lengthNotEqual", "lengthSmaller", "lengthLarger"

8. TYPE VERSIONS - Use current versions:
  - Most nodes: typeVersion: 2
  - Newer nodes (code, set, httpRequest): typeVersion: 2 or higher
  - Legacy nodes (noOp, wait): typeVersion: 1

9. VALIDATION CHECKLIST - Before responding, verify:
  ✓ Every node type uses EXACT lowercase/camelCase from list above
  ✓ Every connection uses exact node names from "name" fields
  ✓ All node IDs are unique UUID-style strings
  ✓ JSON uses lowercase booleans (true/false)
  ✓ Complete workflow structure with ALL required fields
  ✓ All required parameters included for each node type
  ✓ IF nodes use simple operator strings, not objects
  ✓ Email nodes use "message" not "text" parameter
  ✓ Code nodes use "jsCode" not "code" parameter
  ✓ HTTP nodes use proper parameter structure with arrays

10. DO NOT INCLUDE these fields (they cause import errors):
  - active (workflow level)
  - pinData (workflow level)
  - meta (workflow level)
  - id (workflow level)
  - webhookId (node level)
  - createdAt/updatedAt (any level)

COMMON ERROR FIXES:
- "Could not find property option" = Wrong IF node operator format
- "Invalid node type" = Wrong case in node type string
- "Connection target not found" = Using node ID instead of node name in connections
- "Missing required parameter" = Check parameter requirements above

RESPOND WITH ONLY VALID JSON - NO markdown, explanations, or code blocks."""

def post_workflow_to_n8n(workflow_json: Dict[str, Any], N8N_API_KEY: str, N8N_URL: str):
    """Post workflow to n8n API."""

    if isinstance(workflow_json, str):
        workflow_json = json.loads(workflow_json)
    
    headers = {
        "X-N8N-API-KEY": N8N_API_KEY,
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{N8N_URL}/api/v1/workflows",
        headers=headers,
        json=workflow_json  # Use json= instead of data=
    )
    
    print(f"Status Code: {response.status_code}")
    if response.status_code not in [200, 201]:
        print(f"Response: {response.text}")
    
    if response.status_code in [200, 201]:
        return response.json()
    else:
        return {"error": f"HTTP {response.status_code}", "message": response.text}


def create_n8n_workflow(context: Dict[str, Any]) -> str:
    """Convert context to n8n workflow JSON."""
    
    mermaid_diagram = context.get('last_mermaid') or context.get('current_mermaid') or ''
    understanding = context.get('last_understanding') or context.get('current_understanding') or {}
    user_message = context.get('user_message', '')
    
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"""
MERMAID: {mermaid_diagram}
REQUIREMENTS: {json.dumps(understanding, indent=2)}
MESSAGE: {user_message}

Convert to n8n workflow JSON.
"""}
    ]
    
    try:
        response = run_inference(messages, model_name="claude-sonnet-4-20250514")
        
        # Clean the response
        cleaned_response = response.replace("```json", "").replace("```", "").strip()
        
        # Try to parse the JSON
        try:
            n8n_workflow = json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            print(f"Error parsing n8n workflow JSON: {e}")
            print(f"Raw response: {cleaned_response}")
            return {"error": f"Failed to parse n8n workflow JSON: {str(e)}"}
        
        print("n8n_workflow json")
        print(n8n_workflow)
        
        if context.get("user_id"):
            n8n_integrations = integration_collection.find_one({"user_id": context.get("user_id"), "type": "n8n"})
            if n8n_integrations:
                DATA = n8n_integrations.get("data")
                N8N_API_KEY = DATA.get("N8N_API_KEY")
                N8N_URL = DATA.get("N8N_URL")
                if N8N_API_KEY and N8N_URL:
                    n8n_api_response = post_workflow_to_n8n(n8n_workflow, N8N_API_KEY, N8N_URL)
                    print(n8n_api_response)
                else:
                    print("No n8n credentials found")
                if n8n_api_response:
                    print(n8n_api_response)
                    user_timezone = timezone(timedelta(hours=-8))  # PST timezone
                    current_time = datetime.now(user_timezone)
                    messages_collection.insert_one({
                        "chatId": context.get("chat_id"),
                        "id": f"n8n_workflow-api-response-{int(current_time.timestamp() * 1000)}",
                        "text": "N8N Workflow created successfully.",
                        "sender": "ai",
                        "type": "n8n_api_response_json",
                        "json": n8n_workflow,
                        "timestamp": current_time
                    })
        return n8n_workflow
        
    except Exception as e:
        print(f"Error in create_n8n_workflow: {e}")
        return {"error": f"Failed to create n8n workflow: {str(e)}"}
