# llm_models.py (Fixed)
import os
from typing import Dict, Any, Optional
import google.generativeai as genai
from openai import OpenAI
from anthropic import Anthropic

def run_inference(messages: list[dict], model_name: str) -> str:
    """
    Runs inference on a list of messages using the specified model.
    """
    
    # Determine provider
    if "gemini" in model_name.lower():
        provider = "google"
    elif "gpt" in model_name.lower():
        provider = "openai"
    elif "claude" in model_name.lower():
        provider = "anthropic"
    else:
        raise ValueError(f"Could not determine provider for model: {model_name}")

    try:
        if provider == "google":
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set.")
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            
            chat_history_for_google = []
            for msg in messages:
                role = "model" if msg["role"].lower() == "assistant" else msg["role"].lower()
                role = "user" if role == "system" else role
                if role not in ["user", "model"]:
                    continue
                chat_history_for_google.append({
                    "role": role,
                    "parts": [msg["content"]]
                })
            
            if not chat_history_for_google:
                return "Error: No valid messages to send to Gemini."

            response = model.generate_content(chat_history_for_google)
            return response.text

        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set.")
            client = OpenAI(api_key=api_key)

            response = client.chat.completions.create(
                model=model_name,
                messages=messages
            )
            return response.choices[0].message.content

        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set.")
            client = Anthropic(api_key=api_key)

            # Extract system prompt
            system_prompt = None
            processed_messages = []
            if messages and messages[0]["role"].lower() == "system":
                system_prompt = messages[0]["content"]
                processed_messages = messages[1:]
            else:
                processed_messages = messages
            
            # Filter messages for Anthropic
            anthropic_messages = []
            for msg in processed_messages:
                if msg["role"].lower() in ["user", "assistant"]:
                    anthropic_messages.append(msg)
            
            if not anthropic_messages:
                return "Error: No valid user/assistant messages to send to Anthropic."

            # Set max_tokens based on model
            if "claude-4" in model_name or "claude-opus-4" in model_name or "claude-sonnet-4" in model_name:
                max_tokens = 8192
            else:
                max_tokens = 4096
                
            response = client.messages.create(
                model=model_name,
                max_tokens=max_tokens,
                system=system_prompt if system_prompt else None,
                messages=anthropic_messages,
                temperature=0.7  # Add temperature to encourage more creative responses
            )
            
            print(f"Anthropic Response: {response}")
            
            # Handle empty content array
            if not response.content:
                print("Warning: Empty response content from Anthropic")
                return "Error: Empty response from Anthropic"
            
            # Check if content has text
            if hasattr(response.content[0], 'text'):
                return response.content[0].text
            else:
                print(f"Warning: Unexpected response format: {response.content[0]}")
                return "Error: Unexpected response format from Anthropic"

    except Exception as e:
        print(f"An API error occurred with provider {provider} and model {model_name}: {e}")
        raise