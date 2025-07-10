#!/usr/bin/env python3
"""
N8N Workflow Runner
==================
Executes n8n workflows by workflow_id with comprehensive error handling and debugging.
Retrieves user credentials, constructs workflow URLs, and provides detailed error analysis.
"""

import os
import sys
import json
import requests
import time
from typing import Dict, Any, Optional, List, Generator
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
from datetime import datetime, timezone

class N8NRunner:
    """Handle n8n workflow execution with error handling and debugging."""
    
    def __init__(self):
        """Initialize N8N Runner with database connection."""
        load_dotenv()
        self.mongo_client = MongoClient(os.getenv('MONGODB_URI'))
        self.db = self.mongo_client.vibeflows
        
    def get_user_credentials(self, user_id: str) -> Dict[str, Any]:
        """
        Retrieve user credentials including N8N_URL and N8N_API_KEY from credentials collection.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary containing user credentials
            
        Raises:
            Exception: If user not found or credentials missing
        """
        try:
            # Apply URL decoding fix for user_id (handle %7C -> | encoding)
            clean_user_id = str(user_id).replace('%7C', '|').replace('%7c', '|')
            
            # Query N8N_URL credential
            n8n_url_cred = self.db.credentials.find_one({'user_id': clean_user_id, 'name': 'N8N_URL'})
            if not n8n_url_cred:
                raise Exception(f"N8N_URL credential not found for user_id: {user_id}")
            
            # Query N8N_API_KEY credential
            n8n_api_key_cred = self.db.credentials.find_one({'user_id': clean_user_id, 'name': 'N8N_API_KEY'})
            if not n8n_api_key_cred:
                raise Exception(f"N8N_API_KEY credential not found for user_id: {user_id}")
            
            # Extract credential values
            n8n_url = n8n_url_cred.get('value')
            n8n_api_key = n8n_api_key_cred.get('value')
            
            if not n8n_url:
                raise Exception(f"N8N_URL value is empty for user_id: {user_id}")
            
            if not n8n_api_key:
                raise Exception(f"N8N_API_KEY value is empty for user_id: {user_id}")
            
            return {
                'n8n_url': n8n_url,
                'n8n_api_key': n8n_api_key,
                'user_id': user_id
            }
            
        except Exception as e:
            raise Exception(f"Error retrieving user credentials: {str(e)}")
    
    def construct_workflow_url(self, n8n_url: str, workflow_id: str) -> str:
        """
        Construct the full n8n workflow execution URL.
        
        Args:
            n8n_url: Base N8N URL from user credentials
            workflow_id: Workflow identifier
            
        Returns:
            Complete workflow execution URL
        """
        # Remove trailing slash if present
        base_url = n8n_url.rstrip('/')
        
        # Construct workflow URL for workflow execution
        workflow_url = f"{base_url}/workflow/{workflow_id}"
        
        return workflow_url
    
    def log_run(self, run_data: Dict[str, Any]) -> str:
        """
        Log workflow run to n8n_runs collection.
        
        Args:
            run_data: Dictionary containing run information
            
        Returns:
            Run ID for tracking
        """
        try:
            run_record = {
                'timestamp': datetime.now(timezone.utc),
                'user_id': run_data.get('user_id'),
                'workflow_id': run_data.get('workflow_id'),
                'workflow_url': run_data.get('workflow_url'),
                'input_data': run_data.get('input_data'),
                'status': run_data.get('status', 'pending'),
                'execution_time': run_data.get('execution_time'),
                'response_data': run_data.get('response_data'),
                'error_details': run_data.get('error_details'),
                'debugging_info': run_data.get('debugging_info')
            }
            
            result = self.db.n8n_runs.insert_one(run_record)
            return str(result.inserted_id)
            
        except Exception as e:
            print(f"⚠️  Failed to log run: {str(e)}")
            return None
    
    def update_run_log(self, run_id: str, update_data: Dict[str, Any]):
        """
        Update existing run log.
        
        Args:
            run_id: Run ID to update
            update_data: Data to update
        """
        try:
            if run_id:
                self.db.n8n_runs.update_one(
                    {'_id': ObjectId(run_id)},
                    {'$set': update_data}
                )
        except Exception as e:
            print(f"⚠️  Failed to update run log: {str(e)}")
    
    def stream_message(self, message: str, run_id: str = None):
        """
        Stream a message to console and optionally log it.
        
        Args:
            message: Message to stream
            run_id: Optional run ID for logging
        """
        # Print to console for streaming
        print(message)
        
        # Optionally log message to database
        if run_id:
            try:
                self.db.n8n_runs.update_one(
                    {'_id': ObjectId(run_id)},
                    {'$push': {'messages': {
                        'timestamp': datetime.now(timezone.utc),
                        'message': message
                    }}}
                )
            except:
                pass  # Don't fail execution for logging issues
    
    def execute_workflow(self, workflow_url: str, api_key: str, input_data: Dict[str, Any] = None, run_id: str = None) -> Dict[str, Any]:
        """
        Execute n8n workflow with input data and comprehensive error handling.
        
        Args:
            workflow_url: Complete workflow URL
            api_key: N8N API key for authentication
            input_data: Data to send to workflow
            
        Returns:
            Dictionary containing execution results and metadata
        """
        # Prepare request data
        if input_data is None:
            input_data = {}
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'User-Agent': 'VibeFlows-N8N-Runner/1.0'
        }
        
        execution_result = {
            'success': False,
            'workflow_url': workflow_url,
            'input_data': input_data,
            'response_data': None,
            'error_details': None,
            'execution_time': None,
            'status_code': None,
            'debugging_info': {
                'request_headers': headers,
                'request_payload': input_data
            }
        }
        
        try:
            self.stream_message(f"🚀 Executing workflow: {workflow_url}", run_id)
            self.stream_message(f"📦 Input data: {json.dumps(input_data, indent=2)}", run_id)
            
            start_time = time.time()
            
            # Execute POST request to workflow
            response = requests.post(
                workflow_url,
                json=input_data,
                headers=headers,
                timeout=300  # 5 minute timeout
            )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Update execution result with response details
            execution_result.update({
                'status_code': response.status_code,
                'execution_time': execution_time,
                'debugging_info': {
                    **execution_result['debugging_info'],
                    'response_headers': dict(response.headers),
                    'response_status': response.status_code,
                    'execution_time_seconds': execution_time
                }
            })
            
            # Handle successful response
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    execution_result.update({
                        'success': True,
                        'response_data': response_data
                    })
                    self.stream_message(f"✅ Workflow executed successfully in {execution_time:.2f}s", run_id)
                    
                except json.JSONDecodeError:
                    # Handle non-JSON response
                    execution_result.update({
                        'success': True,
                        'response_data': {'raw_response': response.text}
                    })
                    self.stream_message(f"✅ Workflow executed successfully (non-JSON response) in {execution_time:.2f}s", run_id)
            
            else:
                # Handle error response
                error_details = self._analyze_error_response(response)
                execution_result.update({
                    'success': False,
                    'error_details': error_details
                })
                self.stream_message(f"❌ Workflow execution failed: {error_details['summary']}", run_id)
        
        except requests.exceptions.Timeout:
            error_details = {
                'error_type': 'timeout',
                'summary': 'Workflow execution timed out after 5 minutes',
                'troubleshooting_steps': [
                    'Check if the workflow is running correctly in n8n',
                    'Verify the workflow doesn\'t have infinite loops or blocking operations',
                    'Consider optimizing the workflow for better performance',
                    'Check n8n server resources and performance'
                ]
            }
            execution_result['error_details'] = error_details
            self.stream_message(f"❌ Workflow execution timed out", run_id)
        
        except requests.exceptions.ConnectionError:
            error_details = {
                'error_type': 'connection_error',
                'summary': 'Failed to connect to n8n server',
                'troubleshooting_steps': [
                    'Verify the N8N_URL is correct and accessible',
                    'Check if n8n server is running and healthy',
                    'Verify network connectivity to n8n server',
                    'Check firewall settings and port accessibility'
                ]
            }
            execution_result['error_details'] = error_details
            self.stream_message(f"❌ Connection error to n8n server", run_id)
        
        except Exception as e:
            error_details = {
                'error_type': 'unexpected_error',
                'summary': f'Unexpected error: {str(e)}',
                'troubleshooting_steps': [
                    'Check the error message for specific details',
                    'Verify all required parameters are provided',
                    'Check n8n server logs for additional information',
                    'Validate the workflow configuration in n8n'
                ]
            }
            execution_result['error_details'] = error_details
            self.stream_message(f"❌ Unexpected error: {str(e)}", run_id)
        
        return execution_result
    
    def _analyze_error_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Analyze HTTP error response and provide troubleshooting guidance.
        
        Args:
            response: HTTP response object
            
        Returns:
            Dictionary with error analysis and troubleshooting steps
        """
        error_details = {
            'status_code': response.status_code,
            'error_type': 'http_error',
            'summary': '',
            'response_body': '',
            'troubleshooting_steps': []
        }
        
        try:
            error_details['response_body'] = response.text
        except:
            error_details['response_body'] = 'Unable to read response body'
        
        # Analyze specific status codes
        if response.status_code == 400:
            error_details.update({
                'summary': 'Bad Request - Invalid input data or workflow configuration',
                'troubleshooting_steps': [
                    'Verify the input data format matches workflow expectations',
                    'Check if all required fields are provided',
                    'Validate JSON structure and data types',
                    'Review the workflow\'s webhook node configuration'
                ]
            })
        
        elif response.status_code == 401:
            error_details.update({
                'summary': 'Unauthorized - Invalid or missing API key',
                'troubleshooting_steps': [
                    'Verify the N8N_API_KEY is correct and valid',
                    'Check if the API key has expired',
                    'Ensure the API key has permissions for workflow execution',
                    'Regenerate API key in n8n if necessary'
                ]
            })
        
        elif response.status_code == 403:
            error_details.update({
                'summary': 'Forbidden - Insufficient permissions',
                'troubleshooting_steps': [
                    'Check user permissions in n8n',
                    'Verify the workflow is accessible to the API key user',
                    'Review n8n security settings and access controls',
                    'Ensure the workflow is active and published'
                ]
            })
        
        elif response.status_code == 404:
            error_details.update({
                'summary': 'Not Found - Workflow or endpoint not found',
                'troubleshooting_steps': [
                    'Verify the workflow_id is correct',
                    'Check if the workflow exists in n8n',
                    'Ensure the workflow has a webhook trigger configured',
                    'Verify the N8N_URL is pointing to the correct instance'
                ]
            })
        
        elif response.status_code == 422:
            error_details.update({
                'summary': 'Unprocessable Entity - Workflow execution error',
                'troubleshooting_steps': [
                    'Check n8n workflow logs for execution errors',
                    'Verify all workflow nodes are properly configured',
                    'Review input data validation in the workflow',
                    'Test the workflow manually in n8n interface'
                ]
            })
        
        elif response.status_code == 500:
            error_details.update({
                'summary': 'Internal Server Error - n8n server error',
                'troubleshooting_steps': [
                    'Check n8n server logs for error details',
                    'Verify n8n server health and resources',
                    'Review workflow for potential infinite loops or errors',
                    'Contact n8n administrator if issue persists'
                ]
            })
        
        elif response.status_code == 502:
            error_details.update({
                'summary': 'Bad Gateway - Proxy or load balancer error',
                'troubleshooting_steps': [
                    'Check if n8n server is running behind a proxy',
                    'Verify proxy/load balancer configuration',
                    'Check network connectivity to n8n server',
                    'Review proxy timeout settings'
                ]
            })
        
        elif response.status_code == 503:
            error_details.update({
                'summary': 'Service Unavailable - n8n server temporarily unavailable',
                'troubleshooting_steps': [
                    'Wait and retry the request after a few minutes',
                    'Check n8n server status and health',
                    'Verify server resources and capacity',
                    'Contact n8n administrator if issue persists'
                ]
            })
        
        else:
            error_details.update({
                'summary': f'HTTP {response.status_code} error',
                'troubleshooting_steps': [
                    f'Review HTTP {response.status_code} error documentation',
                    'Check n8n server logs for additional details',
                    'Verify workflow and server configuration',
                    'Contact support if issue persists'
                ]
            })
        
        return error_details
    
    def run_workflow(self, user_id: str, workflow_id: str, input_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main method to execute n8n workflow for a user with logging.
        
        Args:
            user_id: User identifier for credential lookup
            workflow_id: N8N workflow identifier
            input_data: Optional data to send to workflow
            
        Returns:
            Dictionary containing execution results and debugging information
        """
        # Initialize run log
        run_data = {
            'user_id': user_id,
            'workflow_id': workflow_id,
            'input_data': input_data,
            'status': 'starting'
        }
        run_id = self.log_run(run_data)
        
        self.stream_message(f"🚀 Starting n8n workflow execution", run_id)
        self.stream_message(f"   User ID: {user_id}", run_id)
        self.stream_message(f"   Workflow ID: {workflow_id}", run_id)
        self.stream_message(f"   Run ID: {run_id}", run_id)
        
        try:
            # Step 1: Get user credentials
            self.stream_message("📋 Retrieving user credentials...", run_id)
            credentials = self.get_user_credentials(user_id)
            self.stream_message(f"   ✅ Credentials found for user: {user_id}", run_id)
            self.stream_message(f"   🔗 N8N URL: {credentials['n8n_url']}", run_id)
            
            # Step 2: Construct workflow URL
            self.stream_message("🔗 Constructing workflow URL...", run_id)
            workflow_url = self.construct_workflow_url(credentials['n8n_url'], workflow_id)
            self.stream_message(f"   ✅ Workflow URL: {workflow_url}", run_id)
            
            # Update run log with workflow URL
            self.update_run_log(run_id, {
                'workflow_url': workflow_url,
                'status': 'executing'
            })
            
            # Step 3: Execute workflow
            self.stream_message("⚡ Executing workflow...", run_id)
            result = self.execute_workflow(
                workflow_url=workflow_url,
                api_key=credentials['n8n_api_key'],
                input_data=input_data,
                run_id=run_id
            )
            
            # Add user context to result
            result['user_context'] = {
                'user_id': user_id,
                'workflow_id': workflow_id,
                'n8n_url': credentials['n8n_url'],
                'run_id': run_id
            }
            
            # Update final run log
            final_status = 'completed' if result['success'] else 'failed'
            self.update_run_log(run_id, {
                'status': final_status,
                'execution_time': result.get('execution_time'),
                'response_data': result.get('response_data'),
                'error_details': result.get('error_details'),
                'debugging_info': result.get('debugging_info')
            })
            
            return result
            
        except Exception as e:
            error_result = {
                'success': False,
                'user_context': {
                    'user_id': user_id,
                    'workflow_id': workflow_id,
                    'run_id': run_id
                },
                'error_details': {
                    'error_type': 'setup_error',
                    'summary': f'Failed to set up workflow execution: {str(e)}',
                    'troubleshooting_steps': [
                        'Verify user_id exists in the database',
                        'Check if user has valid N8N credentials configured',
                        'Ensure N8N_URL and N8N_API_KEY are properly set',
                        'Verify database connectivity and permissions'
                    ]
                }
            }
            
            self.stream_message(f"❌ Setup error: {str(e)}", run_id)
            
            # Update run log with error
            self.update_run_log(run_id, {
                'status': 'failed',
                'error_details': error_result['error_details']
            })
            
            return error_result
    
    def __del__(self):
        """Clean up database connection."""
        if hasattr(self, 'mongo_client'):
            self.mongo_client.close()

def run_n8n_workflow(user_id: str, workflow_id: str, input_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute n8n workflow based on parameters.
    
    Args:
        user_id: User identifier
        workflow_id: N8N workflow identifier
        input_data: Additional workflow parameters
        
    Returns:
        Workflow execution results
    """
    runner = N8NRunner()
    workflow_data = input_data or {}
    return runner.run_workflow(user_id, workflow_id, workflow_data)

def execute_n8n_workflow(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    AI Tool: Execute n8n workflow with comprehensive logging and error handling.
    
    This function provides AI agents with the ability to execute n8n workflows.
    All runs are logged to the n8n_runs collection with streaming messages.
    
    Args:
        input_data: Dictionary containing:
            - user_id: User identifier (required, format: "provider|id")
            - workflow_id: N8N workflow identifier (required)
            - workflow_input: Data to send to the workflow (optional, dict)
            - Additional parameters are passed to the workflow
    
    Returns:
        Dictionary with execution results:
        {
            "success": bool,
            "response_data": dict,  # Workflow response (if successful)
            "error_details": dict,  # Error info and troubleshooting (if failed)
            "user_context": {
                "user_id": str,
                "workflow_id": str,
                "n8n_url": str,
                "run_id": str  # For tracking in n8n_runs collection
            },
            "execution_time": float,  # Seconds
            "debugging_info": dict
        }
    
    Examples:
        # Basic workflow execution
        result = execute_n8n_workflow({
            "user_id": "google-oauth2|123456789",
            "workflow_id": "my-workflow-webhook-id",
            "workflow_input": {
                "message": "Hello World",
                "data": {"key": "value"}
            }
        })
        
        # Alternative: direct parameters (merged with workflow_input)
        result = execute_n8n_workflow({
            "user_id": "google-oauth2|123456789", 
            "workflow_id": "my-workflow-webhook-id",
            "message": "Hello World",
            "data": {"key": "value"}
        })
        
        # Check if successful
        if result["success"]:
            print("Workflow completed:", result["response_data"])
        else:
            print("Error:", result["error_details"]["summary"])
            for step in result["error_details"]["troubleshooting_steps"]:
                print(f"- {step}")
    
    Error Types:
        - validation_error: Missing required fields
        - setup_error: Database/credential issues
        - http_error: N8N API errors (400, 401, 403, 404, 422, 500, etc.)
        - timeout: Workflow execution timeout
        - connection_error: Network connectivity issues
        - unexpected_error: Other runtime errors
    
    Logging:
        All executions are logged to the 'n8n_runs' MongoDB collection with:
        - Timestamp and run tracking
        - Input/output data
        - Streaming messages during execution
        - Error details and troubleshooting steps
        - Performance metrics
    """   
    # Extract and validate required fields
    user_id = input_data.get('user_id')
    workflow_id = input_data.get('workflow_id')
    
    if not user_id:
        return {
            'success': False,
            'error_details': {
                'error_type': 'validation_error',
                'summary': 'Missing required field: user_id',
                'troubleshooting_steps': ['Provide user_id in input_data']
            }
        }
    
    if not workflow_id:
        return {
            'success': False,
            'error_details': {
                'error_type': 'validation_error',
                'summary': 'Missing required field: workflow_id',
                'troubleshooting_steps': ['Provide workflow_id in input_data']
            }
        }
    
    try:
        # Handle workflow_input and other parameters
        workflow_input = input_data.get('workflow_input', {})
        other_params = {k: v for k, v in input_data.items() if k not in ['user_id', 'workflow_id', 'workflow_input']}
        workflow_data = {**workflow_input, **other_params}
        
        return run_n8n_workflow(user_id, workflow_id, workflow_data)
        
    except Exception as e:
        return {
            'success': False,
            'error_details': {
                'error_type': 'unexpected_error',
                'summary': f'Tool execution error: {str(e)}',
                'troubleshooting_steps': [
                    'Check input data format and required fields',
                    'Verify database connectivity',
                    'Ensure n8n_runner.py dependencies are installed',
                    'Check system logs for additional details'
                ]
            }
        }

if __name__ == "__main__":
    """Command line interface for n8n workflow execution."""
    
    if len(sys.argv) < 3:
        print("Usage: python n8n_runner.py <user_id> <workflow_id> [input_json]")
        print("\nExamples:")
        print('  python n8n_runner.py user123 workflow456')
        print('  python n8n_runner.py user123 workflow456 \'{"name": "test", "value": 42}\'')
        sys.exit(1)
    
    user_id = sys.argv[1]
    workflow_id = sys.argv[2]
    
    # Parse optional input data
    input_data = None
    if len(sys.argv) > 3:
        try:
            input_data = json.loads(sys.argv[3])
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON input: {str(e)}")
            sys.exit(1)
    
    # Execute workflow
    try:
        result = run_n8n_workflow(user_id, workflow_id, input_data)
        
        print("\n" + "="*60)
        print("📊 EXECUTION RESULTS")
        print("="*60)
        
        if result['success']:
            print("✅ Status: SUCCESS")
            print(f"⏱️  Execution Time: {result.get('execution_time', 'N/A')}s")
            print("\n📦 Response Data:")
            print(json.dumps(result['response_data'], indent=2))
        else:
            print("❌ Status: FAILED")
            print(f"🚨 Error: {result['error_details']['summary']}")
            print("\n🔧 Troubleshooting Steps:")
            for i, step in enumerate(result['error_details']['troubleshooting_steps'], 1):
                print(f"   {i}. {step}")
            
            if 'response_body' in result['error_details'] and result['error_details']['response_body']:
                print(f"\n📄 Response Body:")
                print(result['error_details']['response_body'])
        
        print("\n🔍 Debugging Information:")
        print(json.dumps(result.get('debugging_info', {}), indent=2))
        
    except KeyboardInterrupt:
        print("\n⚠️  Execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Fatal error: {str(e)}")
        sys.exit(1)