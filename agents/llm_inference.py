import os
from typing import Dict, Any, Optional
import google.generativeai as genai
from openai import OpenAI
from anthropic import Anthropic

# --- Configuration ---
# Ensure your API keys are set as environment variables:
# GOOGLE_API_KEY for Google Gemini
# OPENAI_API_KEY for OpenAI GPT
# ANTHROPIC_API_KEY for Anthropic Claude

# --- Model Name Mapping (for reference, more robust mapping might be needed for production) ---
# This dictionary was discussed previously and helps map common names to specific API identifiers.
# For this example function, we'll assume the model_name passed is the direct API identifier.
model_name_mapping = {
    "Google_Gemini": {
        "Gemini 2.5 Pro (latest preview)": "gemini-2.5-pro-preview-05-06",
        "Gemini 2.5 Pro": "gemini-2.5-pro",
        "Gemini 2.5 Flash": "gemini-2.5-flash",
        "Gemini 2.0 Pro": "gemini-2.0-pro"
    },
    "OpenAI_GPT": {
        "GPT-4.5": "gpt-4.5",
        "GPT-4.1": "gpt-4.1",
        "GPT-4.1 mini": "gpt-4.1-mini",
        "GPT-4.1 nano": "gpt-4.1-nano",
        "GPT-o3": "gpt-o3",
        "GPT-4o": "gpt-4o"
    },
    "Anthropic_Claude": {
        "Claude 4 Opus": "claude-opus-4-20250514",
        "Claude 4 Sonnet": "claude-sonnet-4-20250514",
        "Claude 3.7 Sonnet": "claude-3.7-sonnet-20250224",
        "Claude 3.5 Sonnet": "claude-3.5-sonnet-20240620",
        "Claude 3.5 Haiku": "claude-3.5-haiku-20241022",
        "Claude 3 Opus (original)": "claude-3-opus-20240229",
        "Claude 3 Sonnet (original)": "claude-3-sonnet-20240229",
        "Claude 3 Haiku (original)": "claude-3-haiku-20240307"
    }
}

def run_inference(messages: list[dict], model_name: str) -> str:
    """
    Runs inference on a list of messages using the specified model.

    Args:
        messages: A list of message dictionaries, where each dictionary
                  has 'role' (e.g., 'user', 'assistant', 'system')
                  and 'content' keys.
        model_name: The specific API identifier for the LLM model
                    (e.g., "gemini-1.5-pro-latest", "gpt-4o", "claude-sonnet-4-20250514").

    Returns:
        A string containing the model's response content.

    Raises:
        ValueError: If the model provider cannot be determined or API key is missing.
        Exception: For API-related errors.
    """
    # print(f"Attempting inference with model: {model_name}")
    # print(f"Input messages: {messages}")

    # Determine the provider based on the model_name (simplified heuristic)
    provider = None
    if "gemini" in model_name.lower():
        provider = "google"
    elif "gpt" in model_name.lower():
        provider = "openai"
    elif "claude" in model_name.lower():
        provider = "anthropic"
    else:
        raise ValueError(f"Could not determine provider for model: {model_name}. "
                         "Ensure model_name includes 'gemini', 'gpt', or 'claude'.")

    try:
        if provider == "google":
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set.")
            genai.configure(api_key=api_key)
            
            model = genai.GenerativeModel(model_name)

            # Convert messages to Google's format
            # Google expects roles 'user' and 'model'. System prompts are handled differently
            # or can be part of the first user message.
            # For simplicity, we'll assume alternating user/model roles and no explicit system prompt here.
            # A more robust conversion would be needed for complex scenarios.
            chat_history_for_google = []
            for msg in messages:
                # Gemini API expects 'model' for assistant role.
                role = "model" if msg["role"].lower() == "assistant" else msg["role"].lower()
                role = "user" if role == "system" else role
                # Ensure roles are only 'user' or 'model'
                if role not in ["user", "model"]:
                    print(f"Warning: Skipping message with unhandled role '{msg['role']}' for Gemini.")
                    continue
                chat_history_for_google.append({
                    "role": role,
                    "parts": [msg["content"]]
                })
            
            # Ensure history starts with 'user' if not empty, or handle appropriately
            if not chat_history_for_google or chat_history_for_google[0]['role'] != 'user':
                 # This is a simplified handling. Production code might prepend a user message
                 # or raise an error if the sequence is not valid for the API.
                 # For now, we'll attempt to send what we have, but Gemini API is strict.
                 print("Warning: Gemini chat history should ideally start with a 'user' role.")


            # If the last message was from the 'model', Gemini might not respond as expected
            # if we are asking it to continue. For a fresh user query, the last message should be 'user'.
            # This example assumes the last message in `messages` is the one to respond to.
            
            if not chat_history_for_google:
                return "Error: No valid messages to send to Gemini."

            response = model.generate_content(chat_history_for_google)
            print(f"Google Gemini Response: {response.text}")
            return response.text

        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set.")
            client = OpenAI(api_key=api_key)

            # OpenAI messages format is [{role: "user", content: "..."}, {role: "assistant", ...}]
            # System messages are also supported as the first message.
            response = client.chat.completions.create(
                model=model_name,
                messages=messages # Directly use the input messages
            )
            print(f"OpenAI Response: {response.choices[0].message.content}")
            return response.choices[0].message.content

        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set.")
            client = Anthropic(api_key=api_key)

            system_prompt = None
            processed_messages = []
            if messages and messages[0]["role"].lower() == "system":
                system_prompt = messages[0]["content"]
                processed_messages = messages[1:]
            else:
                processed_messages = messages
            
            # Ensure roles are 'user' or 'assistant' for Anthropic messages array
            anthropic_messages = []
            for msg in processed_messages:
                if msg["role"].lower() in ["user", "assistant"]:
                    anthropic_messages.append(msg)
                else:
                    print(f"Warning: Skipping message with unhandled role '{msg['role']}' for Anthropic.")
            
            if not anthropic_messages:
                 return "Error: No valid user/assistant messages to send to Anthropic."

            # Use higher max_tokens for Claude 4 models
            max_tokens = 8192 if "claude-4" in model_name or "claude-opus-4" in model_name or "claude-sonnet-4" in model_name else 4096

            response = client.messages.create(
                model=model_name,
                max_tokens=max_tokens,
                system=system_prompt if system_prompt else None, # Pass system prompt if it exists
                messages=anthropic_messages
            )
            print(f"Anthropic Response: {response}")
            return response.content[0].text

    except ValueError as ve: # Catch our own ValueErrors for API keys etc.
        print(f"Configuration Error: {ve}")
        raise
    except Exception as e:
        print(f"An API error occurred with provider {provider} and model {model_name}: {e}")
        raise

# --- Example Usage (you can run this file directly to test) ---
def test_llm_models():
    print("Running LLM inference examples...")
    print("Ensure you have GOOGLE_API_KEY, OPENAI_API_KEY, and ANTHROPIC_API_KEY set in your environment.")
    print("Also, make sure you have installed: pip install google-generativeai openai anthropic\n")

    # --- Test Messages ---
    sample_messages_user_query = [
        {"role": "user", "content": "Hello! Can you tell me a fun fact about the Python programming language?"}
    ]
    
    sample_messages_with_system_and_history = [
        {"role": "system", "content": "You are a helpful assistant that provides concise answers."},
        {"role": "user", "content": "What is the capital of France?"},
        {"role": "assistant", "content": "The capital of France is Paris."},
        {"role": "user", "content": "And what is its population?"}
    ]

    # --- Select Models to Test (use actual model IDs you have access to) ---
    # Replace with valid model IDs you have access to and whose provider API key is set.
    # These are examples and might not be the latest or might require specific access.
    
    # test_model_google = "gemini-1.5-flash-latest" # Or another accessible Gemini model
    test_model_openai = "gpt-3.5-turbo" # A commonly accessible OpenAI model
    test_model_claude4 = "claude-sonnet-4-20250514" # Claude 4 Sonnet
    # test_model_anthropic = "claude-3-haiku-20240307" # Or another accessible Claude model

    # --- Run Tests (Uncomment the ones you want to try if API keys are set) ---

    # Test OpenAI
    # if os.getenv("OPENAI_API_KEY"):
    #     try:
    #         print(f"\n--- Testing OpenAI ({test_model_openai}) ---")
    #         response_openai = run_inference(sample_messages_user_query, test_model_openai)
    #         print(f"OpenAI Response: {response_openai}")

    #         response_openai_hist = run_inference(sample_messages_with_system_and_history, test_model_openai)
    #         print(f"OpenAI Response (with history): {response_openai_hist}")
    #     except Exception as e:
    #         print(f"Error during OpenAI test: {e}")
    # else:
    #     print("\nSkipping OpenAI tests: OPENAI_API_KEY not set.")

    # Test Google Gemini
    # Note: The Gemini example below uses `sample_messages_user_query`.
    # For `sample_messages_with_system_and_history`, the system prompt handling for Gemini
    # would need to be more explicitly managed (e.g., prepended to the first user message
    # or handled via specific API features if available for system instructions).
    # The current Gemini message conversion is basic.
    # if os.getenv("GOOGLE_API_KEY"):
    #     try:
    #         print(f"\n--- Testing Google Gemini ({test_model_google}) ---")
    #         response_google = run_inference(sample_messages_user_query, test_model_google)
    #         print(f"Google Gemini Response: {response_google}")
    #     except Exception as e:
    #         print(f"Error during Google Gemini test: {e}")
    # else:
    #     print("\nSkipping Google Gemini tests: GOOGLE_API_KEY not set.")


    # Test Anthropic Claude 4
    # if os.getenv("ANTHROPIC_API_KEY"):
    #     try:
    #         print(f"\n--- Testing Anthropic Claude 4 ({test_model_claude4}) ---")
    #         response_anthropic = run_inference(sample_messages_with_system_and_history, test_model_claude4)
    #         print(f"Anthropic Claude 4 Response: {response_anthropic}")
    #     except Exception as e:
    #         print(f"Error during Anthropic Claude 4 test: {e}")
    # else:
    #     print("\nSkipping Anthropic Claude 4 tests: ANTHROPIC_API_KEY not set.")

    print("\n--- End of examples ---")