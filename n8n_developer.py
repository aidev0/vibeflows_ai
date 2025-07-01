import os
import json
import requests
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

# Database connection
client = MongoClient(os.getenv('MONGODB_URI'))
db = client.vibeflows

def workflow_generator(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates complete n8n workflow JSON from requirements using LLM
    """
    
    integration_name = "inference_anthropic"
    integration = db.integrations.find_one({'name': integration_name})
    
    if not integration:
        return {'workflow_json': {'error': 'Anthropic integration not found'}}
    
    function_code = integration['function']
    exec(function_code, globals())
    
    # System prompt for n8n workflow generation
    system_prompt = """You are an expert n8n workflow developer. You must convert mermaid diagrams into EXACTLY CORRECT n8n workflow JSON that imports perfectly.

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

RESPOND WITH ONLY VALID JSON - NO markdown, explanations, or code blocks."""
    
    # Prepare prompt with requirements
    prompt = f"""REQUIREMENTS: {input_data.get('requirements', '')}

Convert to n8n workflow JSON."""
    
    llm_input = {
        'model': "claude-sonnet-4-20250514",
        'system': system_prompt,
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 8192,
        'temperature': 0.1
    }
    
    try:
        result = globals()[integration_name](llm_input)
        
        # Parse JSON response
        response_text = result['response'].replace('```json', '').replace('```', '').strip()
        workflow_json = json.loads(response_text)
        return {'workflow_json': workflow_json}
        
    except json.JSONDecodeError as e:
        return {'workflow_json': {'error': f'Failed to parse n8n workflow JSON: {str(e)}', 'raw_response': result.get('response', '')}}
    except Exception as e:
        return {'workflow_json': {'error': f'Error generating workflow: {str(e)}'}}

def n8n_publisher(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Posts the generated workflow to n8n instance and saves to database
    """
    
    workflow_json = input_data['workflow_json']
    user_id = input_data.get('user_id')
    
    # Check if workflow has errors
    if 'error' in workflow_json:
        return {
            'n8n_response': workflow_json,
            'status': 'error',
            'message': workflow_json.get('error', 'Unknown error in workflow generation')
        }
    
    # Try to publish to n8n if credentials exist
    n8n_response = None
    if user_id:
        # Get n8n credentials
        n8n_url_cred = db.credentials.find_one({'user_id': user_id, 'name': 'N8N_URL'})
        n8n_api_key_cred = db.credentials.find_one({'user_id': user_id, 'name': 'N8N_API_KEY'})
        
        if n8n_url_cred and n8n_api_key_cred:
            n8n_url = n8n_url_cred.get('value')
            n8n_api_key = n8n_api_key_cred.get('value')
            
            if n8n_api_key and n8n_url:
                try:
                    headers = {
                        'X-N8N-API-KEY': n8n_api_key,
                        'Content-Type': 'application/json'
                    }
                    
                    response = requests.post(
                        f'{n8n_url}/api/v1/workflows',
                        headers=headers,
                        json=workflow_json
                    )
                    
                    if response.status_code in [200, 201]:
                        n8n_response = response.json()
                        
                        # Save workflow to database
                        user_timezone = timezone(timedelta(hours=-8))
                        current_time = datetime.now(user_timezone)
                        db.n8n_workflows.insert_one({
                            'user_id': user_id,
                            'workflow_json': workflow_json,
                            'n8n_response': n8n_response,
                            'status': 'published',
                            'created_at': current_time
                        })
                        
                        return {
                            'n8n_response': n8n_response,
                            'status': 'published',
                            'message': 'Workflow successfully published to n8n'
                        }
                    else:
                        return {
                            'n8n_response': {'error': f'HTTP {response.status_code}', 'message': response.text},
                            'status': 'publish_failed',
                            'message': f'Failed to publish to n8n: HTTP {response.status_code}'
                        }
                        
                except Exception as e:
                    return {
                        'n8n_response': {'error': str(e)},
                        'status': 'publish_error',
                        'message': f'Error publishing to n8n: {str(e)}'
                    }
    
    # Return workflow JSON even if not published
    return {
        'n8n_response': workflow_json,
        'status': 'generated',
        'message': 'Workflow generated successfully (not published - no n8n credentials)'
    }

def n8n_developer(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main orchestration function that converts requirements to n8n workflows
    
    Input:
        - requirements: string describing the workflow requirements
        - user_id: optional user ID for publishing to n8n
        - mermaid_diagram: optional mermaid diagram
        - understanding: optional analysis data
        - user_message: optional user message
        - chat_id: optional chat ID
    
    Output:
        - workflow_json: generated n8n workflow
        - n8n_response: response from n8n API or workflow JSON
        - status: published/generated/error/publish_failed/publish_error
        - message: status message
    """
    
    # Step 1: Generate workflow JSON
    generator_input = {
        'requirements': input_data.get('requirements', '')
    }
    
    generator_result = workflow_generator(generator_input)
    workflow_json = generator_result['workflow_json']
    
    # Step 2: Publish to n8n (if possible)
    publisher_input = {
        'workflow_json': workflow_json,
        'user_id': input_data.get('user_id')
    }
    publisher_result = n8n_publisher(publisher_input)
    
    return {
        'workflow_json': workflow_json,
        'n8n_response': publisher_result['n8n_response'],
        'status': publisher_result['status'],
        'message': publisher_result['message']
    } 