import os
from pymongo import MongoClient
from datetime import datetime

INTEGRATIONS = [
   # LLM Inference integrations with tool access
   {
       "name": "inference_openai",
       "description": "OpenAI GPT models for text generation and completion with tool access",
       "type": "api",
       "function": "def inference_openai(data):\n    import openai\n    import os\n    openai.api_key = os.getenv('OPENAI_API_KEY')\n    \n    # Build messages with system prompt if provided\n    messages = data.get('messages', [])\n    if data.get('system'):\n        messages = [{'role': 'system', 'content': data['system']}] + messages\n    \n    # Prepare tools if provided\n    tools = data.get('tools', [])\n    openai_tools = []\n    for tool in tools:\n        openai_tools.append({\n            'type': 'function',\n            'function': {\n                'name': tool['name'],\n                'description': tool['description'],\n                'parameters': tool.get('input_schema', {})\n            }\n        })\n    \n    # Make API call\n    kwargs = {\n        'model': data.get('model', 'gpt-4o'),\n        'messages': messages,\n        'temperature': data.get('temperature', 0.7)\n    }\n    if openai_tools:\n        kwargs['tools'] = openai_tools\n        kwargs['tool_choice'] = 'auto'\n    \n    response = openai.ChatCompletion.create(**kwargs)\n    \n    # Handle tool calls if present\n    message = response.choices[0].message\n    result = {\n        'response': message.content,\n        'usage': response.usage,\n        'tool_calls': []\n    }\n    \n    if hasattr(message, 'tool_calls') and message.tool_calls:\n        for tool_call in message.tool_calls:\n            result['tool_calls'].append({\n                'id': tool_call.id,\n                'function': tool_call.function.name,\n                'arguments': tool_call.function.arguments\n            })\n    \n    return result",
       "input_schema": {
           "type": "object", 
           "properties": {
               "model": {"type": "string", "default": "gpt-4o"},
               "messages": {"type": "array", "items": {"type": "object"}},
               "system": {"type": "string"},
               "temperature": {"type": "number", "default": 0.7},
               "tools": {"type": "array", "items": {"type": "object"}}
           }
       },
       "output_schema": {
           "type": "object", 
           "properties": {
               "response": {"type": "string"},
               "usage": {"type": "object"},
               "tool_calls": {"type": "array"}
           }
       },
       "credentials": ["OPENAI_API_KEY"],
       "command": ["python", "inference_openai"],
       "language": "python",
       "required_packages": ["openai"]
   },
   {
       "name": "inference_anthropic",
       "description": "Anthropic Claude models for advanced reasoning and analysis with tool access",
       "type": "api",
       "function": "def inference_anthropic(data):\n    import anthropic\n    import os\n    import json\n    \n    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))\n    \n    # Prepare tools if provided\n    claude_tools = []\n    if data.get('tools'):\n        for tool in data['tools']:\n            claude_tools.append({\n                'name': tool['name'],\n                'description': tool['description'],\n                'input_schema': tool.get('input_schema', {})\n            })\n    \n    # Build kwargs\n    kwargs = {\n        'model': data.get('model', 'claude-4-sonnet-20250514'),\n        'messages': data.get('messages', []),\n        'temperature': data.get('temperature', 0.7)\n    }\n    \n    if data.get('system'):\n        kwargs['system'] = data['system']\n    \n    if claude_tools:\n        kwargs['tools'] = claude_tools\n    \n    response = client.messages.create(**kwargs)\n    \n    # Handle tool use if present\n    result = {\n        'response': '',\n        'usage': response.usage,\n        'tool_calls': []\n    }\n    \n    for content in response.content:\n        if content.type == 'text':\n            result['response'] += content.text\n        elif content.type == 'tool_use':\n            result['tool_calls'].append({\n                'id': content.id,\n                'function': content.name,\n                'arguments': json.dumps(content.input)\n            })\n    \n    return result",
       "input_schema": {
           "type": "object",
           "properties": {
               "model": {"type": "string", "default": "claude-4-sonnet-20250514"},
               "messages": {"type": "array", "items": {"type": "object"}},
               "system": {"type": "string"},
               "temperature": {"type": "number", "default": 0.7},
               "tools": {"type": "array", "items": {"type": "object"}}
           }
       },
       "output_schema": {
           "type": "object",
           "properties": {
               "response": {"type": "string"},
               "usage": {"type": "object"},
               "tool_calls": {"type": "array"}
           }
       },
       "credentials": ["ANTHROPIC_API_KEY"],
       "command": ["python", "inference_anthropic"],
       "language": "python",
       "required_packages": ["anthropic"]
   },
   {
       "name": "inference_gemini",
       "description": "Google Gemini models for multimodal AI tasks with tool access",
       "type": "api",
       "function": "def inference_gemini(data):\n    import google.generativeai as genai\n    import os\n    import json\n    \n    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))\n    \n    # Prepare tools if provided\n    gemini_tools = []\n    if data.get('tools'):\n        for tool in data['tools']:\n            gemini_tools.append(genai.protos.Tool(\n                function_declarations=[\n                    genai.protos.FunctionDeclaration(\n                        name=tool['name'],\n                        description=tool['description'],\n                        parameters=genai.protos.Schema(\n                            type=genai.protos.Type.OBJECT,\n                            properties=tool.get('input_schema', {}).get('properties', {})\n                        )\n                    )\n                ]\n            ))\n    \n    model = genai.GenerativeModel(\n        data.get('model', 'gemini-2.5-flash'),\n        tools=gemini_tools if gemini_tools else None,\n        system_instruction=data.get('system')\n    )\n    \n    # Convert messages to Gemini format\n    chat_history = []\n    if data.get('messages'):\n        for msg in data['messages']:\n            if msg['role'] == 'user':\n                chat_history.append({'role': 'user', 'parts': [msg['content']]})\n            elif msg['role'] == 'assistant':\n                chat_history.append({'role': 'model', 'parts': [msg['content']]})\n    \n    chat = model.start_chat(history=chat_history[:-1] if chat_history else [])\n    \n    # Get the last user message or use prompt\n    user_input = data.get('prompt', '')\n    if chat_history:\n        user_input = chat_history[-1]['parts'][0]\n    \n    response = chat.send_message(\n        user_input,\n        generation_config=genai.types.GenerationConfig(\n            temperature=data.get('temperature', 0.7)\n        )\n    )\n    \n    # Handle function calls if present\n    result = {\n        'response': response.text,\n        'usage': {'tokens': len(response.text.split())},\n        'tool_calls': []\n    }\n    \n    if response.candidates[0].content.parts:\n        for part in response.candidates[0].content.parts:\n            if hasattr(part, 'function_call'):\n                result['tool_calls'].append({\n                    'function': part.function_call.name,\n                    'arguments': json.dumps(dict(part.function_call.args))\n                })\n    \n    return result",
       "input_schema": {
           "type": "object",
           "properties": {
               "model": {"type": "string", "default": "gemini-2.5-flash"},
               "prompt": {"type": "string"},
               "messages": {"type": "array", "items": {"type": "object"}},
               "system": {"type": "string"},
               "temperature": {"type": "number", "default": 0.7},
               "tools": {"type": "array", "items": {"type": "object"}}
           }
       },
       "output_schema": {
           "type": "object",
           "properties": {
               "response": {"type": "string"},
               "usage": {"type": "object"},
               "tool_calls": {"type": "array"}
           }
       },
       "credentials": ["GEMINI_API_KEY"],
       "command": ["python", "inference_gemini"],
       "language": "python",
       "required_packages": ["google-generativeai"]
   },
   {
       "name": "inference_llama",
       "description": "Meta Llama models via Together AI with tool access",
       "type": "api",
       "function": "def inference_llama(data):\n    import requests\n    import os\n    import json\n    \n    headers = {\n        'Authorization': f'Bearer {os.getenv(\"LLAMA_API_KEY\")}',\n        'Content-Type': 'application/json'\n    }\n    \n    # Prepare tools if provided\n    together_tools = []\n    if data.get('tools'):\n        for tool in data['tools']:\n            together_tools.append({\n                'type': 'function',\n                'function': {\n                    'name': tool['name'],\n                    'description': tool['description'],\n                    'parameters': tool.get('input_schema', {})\n                }\n            })\n    \n    payload = {\n        'model': data.get('model', 'meta-llama/Llama-3.3-70B-Instruct-Turbo'),\n        'messages': data.get('messages', []),\n        'temperature': data.get('temperature', 0.7)\n    }\n    \n    if data.get('system'):\n        payload['messages'] = [{'role': 'system', 'content': data['system']}] + payload['messages']\n    \n    if together_tools:\n        payload['tools'] = together_tools\n        payload['tool_choice'] = 'auto'\n    \n    response = requests.post('https://api.together.xyz/v1/chat/completions', headers=headers, json=payload)\n    response_data = response.json()\n    \n    result = {\n        'response': response_data['choices'][0]['message'].get('content', ''),\n        'usage': response_data.get('usage', {}),\n        'tool_calls': []\n    }\n    \n    if 'tool_calls' in response_data['choices'][0]['message']:\n        for tool_call in response_data['choices'][0]['message']['tool_calls']:\n            result['tool_calls'].append({\n                'id': tool_call.get('id'),\n                'function': tool_call['function']['name'],\n                'arguments': tool_call['function']['arguments']\n            })\n    \n    return result",
       "input_schema": {
           "type": "object",
           "properties": {
               "model": {"type": "string", "default": "meta-llama/Llama-3.3-70B-Instruct-Turbo"},
               "messages": {"type": "array", "items": {"type": "object"}},
               "system": {"type": "string"},
               "temperature": {"type": "number", "default": 0.7},
               "tools": {"type": "array", "items": {"type": "object"}}
           }
       },
       "output_schema": {
           "type": "object",
           "properties": {
               "response": {"type": "string"},
               "usage": {"type": "object"},
               "tool_calls": {"type": "array"}
           }
       },
       "credentials": ["LLAMA_API_KEY"],
       "command": ["python", "inference_llama"],
       "language": "python",
       "required_packages": ["requests"]
   },
   {
       "name": "inference_cohere",
       "description": "Cohere Command models with tool access",
       "type": "api",
       "function": "def inference_cohere(data):\n    import cohere\n    import os\n    import json\n    \n    co = cohere.Client(os.getenv('COHERE_API_KEY'))\n    \n    # Prepare tools if provided\n    cohere_tools = []\n    if data.get('tools'):\n        for tool in data['tools']:\n            cohere_tools.append({\n                'name': tool['name'],\n                'description': tool['description'],\n                'parameter_definitions': tool.get('input_schema', {}).get('properties', {})\n            })\n    \n    # Convert messages to Cohere format\n    message = ''\n    chat_history = []\n    if data.get('messages'):\n        for msg in data['messages']:\n            if msg['role'] == 'user':\n                message = msg['content']\n            elif msg['role'] == 'assistant':\n                chat_history.append({'role': 'CHATBOT', 'message': msg['content']})\n    \n    if data.get('system'):\n        message = data['system'] + '\\n\\n' + message\n    \n    kwargs = {\n        'model': data.get('model', 'command-r-plus'),\n        'message': message,\n        'temperature': data.get('temperature', 0.7)\n    }\n    \n    if chat_history:\n        kwargs['chat_history'] = chat_history\n    \n    if cohere_tools:\n        kwargs['tools'] = cohere_tools\n    \n    response = co.chat(**kwargs)\n    \n    result = {\n        'response': response.text,\n        'usage': {'tokens': len(response.text.split())},\n        'tool_calls': []\n    }\n    \n    if hasattr(response, 'tool_calls') and response.tool_calls:\n        for tool_call in response.tool_calls:\n            result['tool_calls'].append({\n                'function': tool_call.name,\n                'arguments': json.dumps(tool_call.parameters)\n            })\n    \n    return result",
       "input_schema": {
           "type": "object",
           "properties": {
               "model": {"type": "string", "default": "command-r-plus"},
               "messages": {"type": "array", "items": {"type": "object"}},
               "system": {"type": "string"},
               "temperature": {"type": "number", "default": 0.7},
               "tools": {"type": "array", "items": {"type": "object"}}
           }
       },
       "output_schema": {
           "type": "object",
           "properties": {
               "response": {"type": "string"},
               "usage": {"type": "object"},
               "tool_calls": {"type": "array"}
           }
       },
       "credentials": ["COHERE_API_KEY"],
       "command": ["python", "inference_cohere"],
       "language": "python",
       "required_packages": ["cohere"]
   },
   {
       "name": "inference_mistral",
       "description": "Mistral AI models with tool access",
       "type": "api",
       "function": "def inference_mistral(data):\n    import requests\n    import os\n    import json\n    \n    headers = {\n        'Authorization': f'Bearer {os.getenv(\"MISTRAL_API_KEY\")}',\n        'Content-Type': 'application/json'\n    }\n    \n    # Prepare tools if provided\n    mistral_tools = []\n    if data.get('tools'):\n        for tool in data['tools']:\n            mistral_tools.append({\n                'type': 'function',\n                'function': {\n                    'name': tool['name'],\n                    'description': tool['description'],\n                    'parameters': tool.get('input_schema', {})\n                }\n            })\n    \n    messages = data.get('messages', [])\n    if data.get('system'):\n        messages = [{'role': 'system', 'content': data['system']}] + messages\n    \n    payload = {\n        'model': data.get('model', 'mistral-large-latest'),\n        'messages': messages,\n        'temperature': data.get('temperature', 0.7)\n    }\n    \n    if mistral_tools:\n        payload['tools'] = mistral_tools\n        payload['tool_choice'] = 'auto'\n    \n    response = requests.post('https://api.mistral.ai/v1/chat/completions', headers=headers, json=payload)\n    response_data = response.json()\n    \n    result = {\n        'response': response_data['choices'][0]['message'].get('content', ''),\n        'usage': response_data.get('usage', {}),\n        'tool_calls': []\n    }\n    \n    if 'tool_calls' in response_data['choices'][0]['message']:\n        for tool_call in response_data['choices'][0]['message']['tool_calls']:\n            result['tool_calls'].append({\n                'id': tool_call.get('id'),\n                'function': tool_call['function']['name'],\n                'arguments': tool_call['function']['arguments']\n            })\n    \n    return result",
       "input_schema": {
           "type": "object",
           "properties": {
               "model": {"type": "string", "default": "mistral-large-latest"},
               "messages": {"type": "array", "items": {"type": "object"}},
               "system": {"type": "string"},
               "temperature": {"type": "number", "default": 0.7},
               "tools": {"type": "array", "items": {"type": "object"}}
           }
       },
       "output_schema": {
           "type": "object",
           "properties": {
               "response": {"type": "string"},
               "usage": {"type": "object"},
               "tool_calls": {"type": "array"}
           }
       },
       "credentials": ["MISTRAL_API_KEY"],
       "command": ["python", "inference_mistral"],
       "language": "python",
       "required_packages": ["requests"]
   },
   {
       "name": "inference_perplexity",
       "description": "Perplexity AI for web-connected reasoning with tool access",
       "type": "api",
       "function": "def inference_perplexity(data):\n    import requests\n    import os\n    import json\n    \n    headers = {\n        'Authorization': f'Bearer {os.getenv(\"PERPLEXITY_API_KEY\")}',\n        'Content-Type': 'application/json'\n    }\n    \n    messages = data.get('messages', [])\n    if data.get('system'):\n        messages = [{'role': 'system', 'content': data['system']}] + messages\n    \n    payload = {\n        'model': data.get('model', 'llama-3.1-sonar-large-128k-online'),\n        'messages': messages,\n        'temperature': data.get('temperature', 0.7)\n    }\n    \n    response = requests.post('https://api.perplexity.ai/chat/completions', headers=headers, json=payload)\n    response_data = response.json()\n    \n    result = {\n        'response': response_data['choices'][0]['message']['content'],\n        'usage': response_data.get('usage', {}),\n        'tool_calls': [],\n        'citations': response_data.get('citations', [])\n    }\n    \n    return result",
       "input_schema": {
           "type": "object",
           "properties": {
               "model": {"type": "string", "default": "llama-3.1-sonar-large-128k-online"},
               "messages": {"type": "array", "items": {"type": "object"}},
               "system": {"type": "string"},
               "temperature": {"type": "number", "default": 0.7}
           }
       },
       "output_schema": {
           "type": "object",
           "properties": {
               "response": {"type": "string"},
               "usage": {"type": "object"},
               "tool_calls": {"type": "array"},
               "citations": {"type": "array"}
           }
       },
       "credentials": ["PERPLEXITY_API_KEY"],
       "command": ["python", "inference_perplexity"],
       "language": "python",
       "required_packages": ["requests"]
   },
   {
       "name": "inference_huggingface",
       "description": "Hugging Face models via Inference API",
       "type": "api",
       "function": "def inference_huggingface(data):\n    import requests\n    import os\n    \n    headers = {'Authorization': f'Bearer {os.getenv(\"HUGGINGFACE_API_KEY\")}'}\n    api_url = f'https://api-inference.huggingface.co/models/{data[\"model\"]}'\n    \n    # Convert messages to prompt format\n    prompt = ''\n    if data.get('system'):\n        prompt += data['system'] + '\\n\\n'\n    \n    if data.get('messages'):\n        for msg in data['messages']:\n            prompt += f\"{msg['role']}: {msg['content']}\\n\"\n        prompt += 'assistant: '\n    else:\n        prompt = data.get('prompt', '')\n    \n    payload = {\n        'inputs': prompt,\n        'parameters': {\n            'temperature': data.get('temperature', 0.7),\n            'max_new_tokens': 1000,\n            'return_full_text': False\n        }\n    }\n    \n    response = requests.post(api_url, headers=headers, json=payload)\n    \n    if response.status_code == 200:\n        response_data = response.json()\n        if isinstance(response_data, list) and len(response_data) > 0:\n            generated_text = response_data[0].get('generated_text', '')\n        else:\n            generated_text = str(response_data)\n    else:\n        generated_text = f'Error: {response.status_code}'\n    \n    result = {\n        'response': generated_text,\n        'usage': {'model': data['model']},\n        'tool_calls': []\n    }\n    \n    return result",
       "input_schema": {
           "type": "object",
           "properties": {
               "model": {"type": "string", "default": "microsoft/DialoGPT-large"},
               "prompt": {"type": "string"},
               "messages": {"type": "array", "items": {"type": "object"}},
               "system": {"type": "string"},
               "temperature": {"type": "number", "default": 0.7}
           }
       },
       "output_schema": {
           "type": "object",
           "properties": {
               "response": {"type": "string"},
               "usage": {"type": "object"},
               "tool_calls": {"type": "array"}
           }
       },
       "credentials": ["HUGGINGFACE_API_KEY"],
       "command": ["python", "inference_huggingface"],
       "language": "python",
       "required_packages": ["requests"]
   },
   # API Integrations (unchanged, just showing one example)
   {
       "name": "api_sendgrid",
       "description": "Send emails via SendGrid API",
       "type": "api",
       "function": "def api_sendgrid(data):\n    import requests\n    import os\n    headers = {\n        'Authorization': f'Bearer {os.getenv(\"SENDGRID_API_KEY\")}',\n        'Content-Type': 'application/json'\n    }\n    payload = {\n        'personalizations': [{'to': [{'email': data['to']}]}],\n        'from': {'email': data['from']},\n        'subject': data['subject'],\n        'content': [{'type': 'text/plain', 'value': data['body']}]\n    }\n    response = requests.post('https://api.sendgrid.com/v3/mail/send', headers=headers, json=payload)\n    return {'status': 'sent' if response.status_code == 202 else 'error', 'status_code': response.status_code}",
       "input_schema": {"type": "object", "properties": {"to": {"type": "string"}, "from": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}},
       "output_schema": {"type": "object", "properties": {"status": {"type": "string"}, "status_code": {"type": "number"}}},
       "credentials": ["SENDGRID_API_KEY"],
       "command": ["python", "api_sendgrid"],
       "language": "python",
       "required_packages": ["requests"]
   }
]

def insert_integrations_into_db():
   db = MongoClient(os.getenv("MONGODB_URI")).vibeflows

   responses = []

   for integration in INTEGRATIONS:
       integration["created_at"] = datetime.utcnow()
       response = db.integrations.insert_one(integration)
       responses.append(response)

   print(f"Created {len(INTEGRATIONS)} integrations")
   return responses

import os
from pymongo import MongoClient
from datetime import datetime

ADDITIONAL_INTEGRATIONS = [
    # CRM Integrations
    {
        "name": "crm_hubspot",
        "description": "HubSpot CRM integration for contacts, deals, and companies",
        "type": "api",
        "function": "def crm_hubspot(data):\n    import requests\n    import os\n    \n    headers = {\n        'Authorization': f'Bearer {os.getenv(\"HUBSPOT_API_KEY\")}',\n        'Content-Type': 'application/json'\n    }\n    \n    action = data.get('action', 'get_contacts')\n    base_url = 'https://api.hubapi.com/crm/v3/objects'\n    \n    if action == 'create_contact':\n        url = f'{base_url}/contacts'\n        payload = {'properties': data['properties']}\n        response = requests.post(url, headers=headers, json=payload)\n    elif action == 'get_contacts':\n        url = f'{base_url}/contacts'\n        params = {'limit': data.get('limit', 100)}\n        response = requests.get(url, headers=headers, params=params)\n    elif action == 'update_contact':\n        url = f'{base_url}/contacts/{data[\"contact_id\"]}'\n        payload = {'properties': data['properties']}\n        response = requests.patch(url, headers=headers, json=payload)\n    elif action == 'create_deal':\n        url = f'{base_url}/deals'\n        payload = {'properties': data['properties']}\n        response = requests.post(url, headers=headers, json=payload)\n    \n    return {'status_code': response.status_code, 'data': response.json() if response.status_code < 400 else None, 'error': response.text if response.status_code >= 400 else None}",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["create_contact", "get_contacts", "update_contact", "create_deal"]},
                "contact_id": {"type": "string"},
                "properties": {"type": "object"},
                "limit": {"type": "number", "default": 100}
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status_code": {"type": "number"},
                "data": {"type": "object"},
                "error": {"type": "string"}
            }
        },
        "credentials": ["HUBSPOT_API_KEY"],
        "command": ["python", "crm_hubspot"],
        "language": "python",
        "required_packages": ["requests"]
    },
    {
        "name": "crm_salesforce",
        "description": "Salesforce CRM integration for leads, accounts, and opportunities",
        "type": "api",
        "function": "def crm_salesforce(data):\n    import requests\n    import os\n    \n    # OAuth token exchange\n    auth_url = f'{os.getenv(\"SALESFORCE_INSTANCE_URL\")}/services/oauth2/token'\n    auth_data = {\n        'grant_type': 'client_credentials',\n        'client_id': os.getenv('SALESFORCE_CLIENT_ID'),\n        'client_secret': os.getenv('SALESFORCE_CLIENT_SECRET')\n    }\n    auth_response = requests.post(auth_url, data=auth_data)\n    access_token = auth_response.json()['access_token']\n    \n    headers = {\n        'Authorization': f'Bearer {access_token}',\n        'Content-Type': 'application/json'\n    }\n    \n    action = data.get('action', 'query')\n    base_url = f'{os.getenv(\"SALESFORCE_INSTANCE_URL\")}/services/data/v57.0'\n    \n    if action == 'query':\n        url = f'{base_url}/query'\n        params = {'q': data['soql']}\n        response = requests.get(url, headers=headers, params=params)\n    elif action == 'create_lead':\n        url = f'{base_url}/sobjects/Lead'\n        response = requests.post(url, headers=headers, json=data['fields'])\n    elif action == 'create_account':\n        url = f'{base_url}/sobjects/Account'\n        response = requests.post(url, headers=headers, json=data['fields'])\n    \n    return {'status_code': response.status_code, 'data': response.json() if response.status_code < 400 else None, 'error': response.text if response.status_code >= 400 else None}",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["query", "create_lead", "create_account"]},
                "soql": {"type": "string"},
                "fields": {"type": "object"}
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status_code": {"type": "number"},
                "data": {"type": "object"},
                "error": {"type": "string"}
            }
        },
        "credentials": ["SALESFORCE_INSTANCE_URL", "SALESFORCE_CLIENT_ID", "SALESFORCE_CLIENT_SECRET"],
        "command": ["python", "crm_salesforce"],
        "language": "python",
        "required_packages": ["requests"]
    },
    
    # Social Media Integrations
    {
        "name": "social_twitter",
        "description": "Twitter/X API v2 integration for posting and analytics",
        "type": "api",
        "function": "def social_twitter(data):\n    import requests\n    import os\n    \n    headers = {\n        'Authorization': f'Bearer {os.getenv(\"TWITTER_BEARER_TOKEN\")}',\n        'Content-Type': 'application/json'\n    }\n    \n    action = data.get('action', 'post_tweet')\n    \n    if action == 'post_tweet':\n        url = 'https://api.twitter.com/2/tweets'\n        payload = {'text': data['text']}\n        if data.get('media_ids'):\n            payload['media'] = {'media_ids': data['media_ids']}\n        response = requests.post(url, headers=headers, json=payload)\n    elif action == 'get_user_tweets':\n        user_id = data['user_id']\n        url = f'https://api.twitter.com/2/users/{user_id}/tweets'\n        params = {'max_results': data.get('max_results', 10)}\n        response = requests.get(url, headers=headers, params=params)\n    elif action == 'search_tweets':\n        url = 'https://api.twitter.com/2/tweets/search/recent'\n        params = {'query': data['query'], 'max_results': data.get('max_results', 10)}\n        response = requests.get(url, headers=headers, params=params)\n    \n    return {'status_code': response.status_code, 'data': response.json() if response.status_code < 400 else None, 'error': response.text if response.status_code >= 400 else None}",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["post_tweet", "get_user_tweets", "search_tweets"]},
                "text": {"type": "string"},
                "media_ids": {"type": "array"},
                "user_id": {"type": "string"},
                "query": {"type": "string"},
                "max_results": {"type": "number", "default": 10}
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status_code": {"type": "number"},
                "data": {"type": "object"},
                "error": {"type": "string"}
            }
        },
        "credentials": ["TWITTER_BEARER_TOKEN"],
        "command": ["python", "social_twitter"],
        "language": "python",
        "required_packages": ["requests"]
    },
    {
        "name": "social_linkedin",
        "description": "LinkedIn API integration for posting and company updates",
        "type": "api",
        "function": "def social_linkedin(data):\n    import requests\n    import os\n    \n    headers = {\n        'Authorization': f'Bearer {os.getenv(\"LINKEDIN_ACCESS_TOKEN\")}',\n        'Content-Type': 'application/json',\n        'X-Restli-Protocol-Version': '2.0.0'\n    }\n    \n    action = data.get('action', 'create_post')\n    \n    if action == 'create_post':\n        url = 'https://api.linkedin.com/v2/ugcPosts'\n        payload = {\n            'author': data['author_urn'],\n            'lifecycleState': 'PUBLISHED',\n            'specificContent': {\n                'com.linkedin.ugc.ShareContent': {\n                    'shareCommentary': {'text': data['text']},\n                    'shareMediaCategory': 'NONE'\n                }\n            },\n            'visibility': {'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'}\n        }\n        response = requests.post(url, headers=headers, json=payload)\n    elif action == 'get_company_updates':\n        company_id = data['company_id']\n        url = f'https://api.linkedin.com/v2/shares?q=owners&owners=urn:li:organization:{company_id}'\n        response = requests.get(url, headers=headers)\n    \n    return {'status_code': response.status_code, 'data': response.json() if response.status_code < 400 else None, 'error': response.text if response.status_code >= 400 else None}",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["create_post", "get_company_updates"]},
                "text": {"type": "string"},
                "author_urn": {"type": "string"},
                "company_id": {"type": "string"}
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status_code": {"type": "number"},
                "data": {"type": "object"},
                "error": {"type": "string"}
            }
        },
        "credentials": ["LINKEDIN_ACCESS_TOKEN"],
        "command": ["python", "social_linkedin"],
        "language": "python",
        "required_packages": ["requests"]
    },
    
    # Analytics Integrations
    {
        "name": "analytics_google",
        "description": "Google Analytics 4 integration for website analytics",
        "type": "api",
        "function": "def analytics_google(data):\n    import requests\n    import os\n    import json\n    \n    # Use service account authentication\n    from google.analytics.data_v1beta import BetaAnalyticsDataClient\n    from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest\n    \n    client = BetaAnalyticsDataClient.from_service_account_file(os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE'))\n    \n    property_id = data['property_id']\n    \n    request = RunReportRequest(\n        property=f'properties/{property_id}',\n        dimensions=[Dimension(name=dim) for dim in data.get('dimensions', ['date'])],\n        metrics=[Metric(name=metric) for metric in data.get('metrics', ['sessions'])],\n        date_ranges=[DateRange(start_date=data.get('start_date', '30daysAgo'), end_date=data.get('end_date', 'today'))]\n    )\n    \n    response = client.run_report(request=request)\n    \n    rows = []\n    for row in response.rows:\n        row_data = {}\n        for i, dim in enumerate(data.get('dimensions', ['date'])):\n            row_data[dim] = row.dimension_values[i].value\n        for i, metric in enumerate(data.get('metrics', ['sessions'])):\n            row_data[metric] = row.metric_values[i].value\n        rows.append(row_data)\n    \n    return {'status': 'success', 'data': rows, 'row_count': len(rows)}",
        "input_schema": {
            "type": "object",
            "properties": {
                "property_id": {"type": "string"},
                "dimensions": {"type": "array", "items": {"type": "string"}},
                "metrics": {"type": "array", "items": {"type": "string"}},
                "start_date": {"type": "string", "default": "30daysAgo"},
                "end_date": {"type": "string", "default": "today"}
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "data": {"type": "array"},
                "row_count": {"type": "number"}
            }
        },
        "credentials": ["GOOGLE_SERVICE_ACCOUNT_FILE"],
        "command": ["python", "analytics_google"],
        "language": "python",
        "required_packages": ["google-analytics-data"]
    },
    {
        "name": "analytics_mixpanel",
        "description": "Mixpanel analytics integration for event tracking",
        "type": "api",
        "function": "def analytics_mixpanel(data):\n    import requests\n    import os\n    import json\n    import base64\n    \n    action = data.get('action', 'track_event')\n    \n    if action == 'track_event':\n        url = 'https://api.mixpanel.com/track'\n        payload = {\n            'event': data['event_name'],\n            'properties': {\n                'token': os.getenv('MIXPANEL_TOKEN'),\n                'distinct_id': data.get('user_id', 'anonymous'),\n                **data.get('properties', {})\n            }\n        }\n        encoded_payload = base64.b64encode(json.dumps(payload).encode()).decode()\n        response = requests.post(url, data={'data': encoded_payload})\n    elif action == 'query_events':\n        auth = (os.getenv('MIXPANEL_API_SECRET'), '')\n        url = 'https://mixpanel.com/api/2.0/events'\n        params = {\n            'event': json.dumps(data.get('events', [])),\n            'type': data.get('type', 'general'),\n            'from_date': data.get('from_date'),\n            'to_date': data.get('to_date')\n        }\n        response = requests.get(url, auth=auth, params=params)\n    \n    return {'status_code': response.status_code, 'data': response.json() if response.status_code < 400 else None, 'error': response.text if response.status_code >= 400 else None}",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["track_event", "query_events"]},
                "event_name": {"type": "string"},
                "user_id": {"type": "string"},
                "properties": {"type": "object"},
                "events": {"type": "array"},
                "type": {"type": "string", "default": "general"},
                "from_date": {"type": "string"},
                "to_date": {"type": "string"}
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status_code": {"type": "number"},
                "data": {"type": "object"},
                "error": {"type": "string"}
            }
        },
        "credentials": ["MIXPANEL_TOKEN", "MIXPANEL_API_SECRET"],
        "command": ["python", "analytics_mixpanel"],
        "language": "python",
        "required_packages": ["requests"]
    },
    
    # Communication Integrations
    {
        "name": "comm_slack",
        "description": "Slack API integration for messaging and notifications",
        "type": "api",
        "function": "def comm_slack(data):\n    import requests\n    import os\n    \n    headers = {\n        'Authorization': f'Bearer {os.getenv(\"SLACK_BOT_TOKEN\")}',\n        'Content-Type': 'application/json'\n    }\n    \n    action = data.get('action', 'send_message')\n    \n    if action == 'send_message':\n        url = 'https://slack.com/api/chat.postMessage'\n        payload = {\n            'channel': data['channel'],\n            'text': data['text'],\n            'blocks': data.get('blocks')\n        }\n        response = requests.post(url, headers=headers, json=payload)\n    elif action == 'get_channels':\n        url = 'https://slack.com/api/conversations.list'\n        response = requests.get(url, headers=headers)\n    elif action == 'create_channel':\n        url = 'https://slack.com/api/conversations.create'\n        payload = {'name': data['name'], 'is_private': data.get('is_private', False)}\n        response = requests.post(url, headers=headers, json=payload)\n    \n    return {'status_code': response.status_code, 'data': response.json() if response.status_code < 400 else None, 'error': response.text if response.status_code >= 400 else None}",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["send_message", "get_channels", "create_channel"]},
                "channel": {"type": "string"},
                "text": {"type": "string"},
                "blocks": {"type": "array"},
                "name": {"type": "string"},
                "is_private": {"type": "boolean", "default": False}
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status_code": {"type": "number"},
                "data": {"type": "object"},
                "error": {"type": "string"}
            }
        },
        "credentials": ["SLACK_BOT_TOKEN"],
        "command": ["python", "comm_slack"],
        "language": "python",
        "required_packages": ["requests"]
    },
    {
        "name": "comm_twilio",
        "description": "Twilio integration for SMS and voice communications",
        "type": "api",
        "function": "def comm_twilio(data):\n    from twilio.rest import Client\n    import os\n    \n    client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))\n    \n    action = data.get('action', 'send_sms')\n    \n    if action == 'send_sms':\n        message = client.messages.create(\n            body=data['body'],\n            from_=data.get('from_number', os.getenv('TWILIO_PHONE_NUMBER')),\n            to=data['to_number']\n        )\n        return {'status': 'success', 'message_sid': message.sid, 'status': message.status}\n    elif action == 'make_call':\n        call = client.calls.create(\n            twiml=data.get('twiml', '<Response><Say>Hello from your marketing automation!</Say></Response>'),\n            from_=data.get('from_number', os.getenv('TWILIO_PHONE_NUMBER')),\n            to=data['to_number']\n        )\n        return {'status': 'success', 'call_sid': call.sid, 'status': call.status}\n    elif action == 'get_messages':\n        messages = client.messages.list(limit=data.get('limit', 20))\n        return {'status': 'success', 'messages': [{'sid': m.sid, 'body': m.body, 'from': m.from_, 'to': m.to} for m in messages]}",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["send_sms", "make_call", "get_messages"]},
                "body": {"type": "string"},
                "to_number": {"type": "string"},
                "from_number": {"type": "string"},
                "twiml": {"type": "string"},
                "limit": {"type": "number", "default": 20}
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "message_sid": {"type": "string"},
                "call_sid": {"type": "string"},
                "messages": {"type": "array"}
            }
        },
        "credentials": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER"],
        "command": ["python", "comm_twilio"],
        "language": "python",
        "required_packages": ["twilio"]
    },
    
    # E-commerce Integrations
    {
        "name": "ecom_shopify",
        "description": "Shopify API integration for products, orders, and customers",
        "type": "api",
        "function": "def ecom_shopify(data):\n    import requests\n    import os\n    \n    shop_url = os.getenv('SHOPIFY_SHOP_URL')\n    headers = {\n        'X-Shopify-Access-Token': os.getenv('SHOPIFY_ACCESS_TOKEN'),\n        'Content-Type': 'application/json'\n    }\n    \n    action = data.get('action', 'get_products')\n    \n    if action == 'get_products':\n        url = f'{shop_url}/admin/api/2023-10/products.json'\n        params = {'limit': data.get('limit', 50)}\n        response = requests.get(url, headers=headers, params=params)\n    elif action == 'create_product':\n        url = f'{shop_url}/admin/api/2023-10/products.json'\n        payload = {'product': data['product_data']}\n        response = requests.post(url, headers=headers, json=payload)\n    elif action == 'get_orders':\n        url = f'{shop_url}/admin/api/2023-10/orders.json'\n        params = {'status': data.get('status', 'any'), 'limit': data.get('limit', 50)}\n        response = requests.get(url, headers=headers, params=params)\n    elif action == 'get_customers':\n        url = f'{shop_url}/admin/api/2023-10/customers.json'\n        params = {'limit': data.get('limit', 50)}\n        response = requests.get(url, headers=headers, params=params)\n    \n    return {'status_code': response.status_code, 'data': response.json() if response.status_code < 400 else None, 'error': response.text if response.status_code >= 400 else None}",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["get_products", "create_product", "get_orders", "get_customers"]},
                "product_data": {"type": "object"},
                "status": {"type": "string"},
                "limit": {"type": "number", "default": 50}
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status_code": {"type": "number"},
                "data": {"type": "object"},
                "error": {"type": "string"}
            }
        },
        "credentials": ["SHOPIFY_SHOP_URL", "SHOPIFY_ACCESS_TOKEN"],
        "command": ["python", "ecom_shopify"],
        "language": "python",
        "required_packages": ["requests"]
    },
    {
        "name": "ecom_stripe",
        "description": "Stripe payment processing integration",
        "type": "api",
        "function": "def ecom_stripe(data):\n    import stripe\n    import os\n    \n    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')\n    \n    action = data.get('action', 'create_customer')\n    \n    try:\n        if action == 'create_customer':\n            customer = stripe.Customer.create(\n                email=data['email'],\n                name=data.get('name'),\n                metadata=data.get('metadata', {})\n            )\n            return {'status': 'success', 'customer': customer}\n        elif action == 'create_payment_intent':\n            intent = stripe.PaymentIntent.create(\n                amount=data['amount'],\n                currency=data.get('currency', 'usd'),\n                customer=data.get('customer_id'),\n                metadata=data.get('metadata', {})\n            )\n            return {'status': 'success', 'payment_intent': intent}\n        elif action == 'get_customers':\n            customers = stripe.Customer.list(limit=data.get('limit', 10))\n            return {'status': 'success', 'customers': customers}\n        elif action == 'get_charges':\n            charges = stripe.Charge.list(limit=data.get('limit', 10))\n            return {'status': 'success', 'charges': charges}\n    except stripe.error.StripeError as e:\n        return {'status': 'error', 'error': str(e)}",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["create_customer", "create_payment_intent", "get_customers", "get_charges"]},
                "email": {"type": "string"},
                "name": {"type": "string"},
                "amount": {"type": "number"},
                "currency": {"type": "string", "default": "usd"},
                "customer_id": {"type": "string"},
                "metadata": {"type": "object"},
                "limit": {"type": "number", "default": 10}
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "customer": {"type": "object"},
                "payment_intent": {"type": "object"},
                "customers": {"type": "object"},
                "charges": {"type": "object"},
                "error": {"type": "string"}
            }
        },
        "credentials": ["STRIPE_SECRET_KEY"],
        "command": ["python", "ecom_stripe"],
        "language": "python",
        "required_packages": ["stripe"]
    },
    
    # Content Management
    {
        "name": "cms_wordpress",
        "description": "WordPress REST API integration for posts and pages",
        "type": "api",
        "function": "def cms_wordpress(data):\n    import requests\n    import os\n    import base64\n    \n    site_url = os.getenv('WORDPRESS_SITE_URL')\n    username = os.getenv('WORDPRESS_USERNAME')\n    password = os.getenv('WORDPRESS_APP_PASSWORD')\n    \n    credentials = base64.b64encode(f'{username}:{password}'.encode()).decode()\n    headers = {\n        'Authorization': f'Basic {credentials}',\n        'Content-Type': 'application/json'\n    }\n    \n    action = data.get('action', 'get_posts')\n    \n    if action == 'create_post':\n        url = f'{site_url}/wp-json/wp/v2/posts'\n        payload = {\n            'title': data['title'],\n            'content': data['content'],\n            'status': data.get('status', 'draft'),\n            'categories': data.get('categories', [])\n        }\n        response = requests.post(url, headers=headers, json=payload)\n    elif action == 'get_posts':\n        url = f'{site_url}/wp-json/wp/v2/posts'\n        params = {'per_page': data.get('per_page', 10)}\n        response = requests.get(url, headers=headers, params=params)\n    elif action == 'update_post':\n        post_id = data['post_id']\n        url = f'{site_url}/wp-json/wp/v2/posts/{post_id}'\n        payload = {k: v for k, v in data.items() if k not in ['action', 'post_id']}\n        response = requests.post(url, headers=headers, json=payload)\n    \n    return {'status_code': response.status_code, 'data': response.json() if response.status_code < 400 else None, 'error': response.text if response.status_code >= 400 else None}",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["create_post", "get_posts", "update_post"]},
                "title": {"type": "string"},
                "content": {"type": "string"},
                "status": {"type": "string", "default": "draft"},
                "categories": {"type": "array"},
                "post_id": {"type": "string"},
                "per_page": {"type": "number", "default": 10}
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status_code": {"type": "number"},
                "data": {"type": "object"},
                "error": {"type": "string"}
            }
        },
        "credentials": ["WORDPRESS_SITE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"],
        "command": ["python", "cms_wordpress"],
        "language": "python",
        "required_packages": ["requests"]
    }
]

def insert_additional_integrations_into_db():
    """Insert additional integrations into MongoDB"""
    db = MongoClient(os.getenv("MONGODB_URI")).vibeflows

    responses = []

    for integration in ADDITIONAL_INTEGRATIONS:
        integration["created_at"] = datetime.utcnow()
        response = db.integrations.insert_one(integration)
        responses.append(response)

    print(f"Created {len(ADDITIONAL_INTEGRATIONS)} additional integrations")
    return responses