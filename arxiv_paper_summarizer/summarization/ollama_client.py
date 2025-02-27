import os
import requests
import time
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

def query_ollama(
    prompt: str, 
    model: str = DEFAULT_MODEL, 
    max_tokens: int = 1000, 
    temperature: float = 0.1,
    retries: int = 3,
    retry_delay: int = 3
) -> str:
    """
    Send a prompt to the Ollama API and return the response.
    
    Args:
        prompt: The text prompt to send to Ollama
        model: The model to use (e.g., "mistral", "llama2")
        max_tokens: Maximum number of tokens in the response
        temperature: Temperature for sampling (0.0-1.0)
        retries: Number of retry attempts if request fails
        retry_delay: Seconds to wait between retries
        
    Returns:
        The model's response as a string
    """
    # Check if we should use the older API format or the new streaming API
    # Try the streaming API first as it's more reliable
    url = f"{OLLAMA_BASE_URL}/api/chat"
    
    data = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens
        }
    }
    
    for attempt in range(retries):
        try:
            # Try the chat API first
            response = requests.post(url, json=data, timeout=120)  # 2-minute timeout
            
            if response.status_code == 200:
                try:
                    return response.json().get("message", {}).get("content", "")
                except Exception as json_err:
                    print(f"Error parsing JSON from chat API: {str(json_err)}")
                    # Fall back to the generate API below
            else:
                print(f"Chat API returned status code {response.status_code}, trying generate API...")
            
            # If chat API failed, try the generate API
            url = f"{OLLAMA_BASE_URL}/api/generate"
            
            data = {
                "model": model,
                "prompt": prompt,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            response = requests.post(url, json=data, timeout=120)
            
            if response.status_code == 200:
                try:
                    # Handle the response as text first to inspect any issues
                    resp_text = response.text
                    
                    # Check if it's a streaming response (multiple JSON objects)
                    if resp_text.count('{') > 1:
                        # Handle streaming response - take the last complete JSON object
                        json_objects = []
                        lines = resp_text.strip().split('\n')
                        for line in lines:
                            if line.strip():
                                try:
                                    json_objects.append(json.loads(line))
                                except json.JSONDecodeError:
                                    print(f"Warning: Could not parse JSON line: {line[:50]}...")
                        
                        # Get the last complete response
                        if json_objects:
                            return json_objects[-1].get("response", "")
                        else:
                            return ""
                    else:
                        # Regular JSON response
                        return response.json().get("response", "")
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {str(e)}")
                    print(f"Response preview: {response.text[:100]}...")
                    # Return what we can from the raw text
                    if "response" in response.text:
                        try:
                            return response.text.split('"response":"')[1].split('"')[0]
                        except:
                            pass
                    return f"Error parsing response: {str(e)}"
            else:
                error_msg = f"Error: Received status code {response.status_code} from Ollama API"
                print(error_msg)
                
                # If we have retries left, wait and try again
                if attempt < retries - 1:
                    print(f"Retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{retries})")
                    time.sleep(retry_delay)
                else:
                    return error_msg
                    
        except requests.exceptions.RequestException as e:
            error_msg = f"Connection error with Ollama API: {str(e)}"
            print(error_msg)
            
            # If we have retries left, wait and try again
            if attempt < retries - 1:
                print(f"Retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{retries})")
                time.sleep(retry_delay)
            else:
                return error_msg
    
    return "Failed to get a response after multiple retries"

def get_available_models() -> list:
    """
    Get a list of available models from Ollama.
    
    Returns:
        List of model names
    """
    url = f"{OLLAMA_BASE_URL}/api/tags"
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            models_data = response.json().get("models", [])
            return [model.get("name") for model in models_data]
        else:
            print(f"Error fetching models: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error connecting to Ollama: {str(e)}")
        return []

def check_ollama_status() -> Dict[str, Any]:
    """
    Check if Ollama is running and return status information.
    
    Returns:
        Dictionary with status information
    """
    try:
        # Try to get the list of models as a simple API test
        models = get_available_models()
        
        if models:
            return {
                "status": "running",
                "available_models": models,
                "default_model": DEFAULT_MODEL,
                "base_url": OLLAMA_BASE_URL
            }
        else:
            return {
                "status": "running_but_no_models",
                "message": "Ollama is running but no models were found",
                "base_url": OLLAMA_BASE_URL
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error connecting to Ollama: {str(e)}",
            "base_url": OLLAMA_BASE_URL
        }

# Test function to verify Ollama is working
def test_ollama(test_prompt: str = "Hello, how are you?") -> Dict[str, Any]:
    """
    Test if Ollama is working by sending a simple prompt.
    
    Args:
        test_prompt: A simple prompt to test the connection
        
    Returns:
        Dictionary with test results
    """
    start_time = time.time()
    
    try:
        response = query_ollama(
            test_prompt, 
            max_tokens=50, 
            temperature=0.0
        )
        
        elapsed_time = time.time() - start_time
        
        return {
            "status": "success",
            "response": response,
            "response_time": f"{elapsed_time:.2f} seconds",
            "model": DEFAULT_MODEL
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error testing Ollama: {str(e)}",
            "model": DEFAULT_MODEL
        }

if __name__ == "__main__":
    # Simple test if run directly
    print("Checking Ollama status...")
    status = check_ollama_status()
    print(f"Status: {status['status']}")
    
    if status['status'] == 'running':
        print(f"Available models: {', '.join(status['available_models'])}")
        print(f"Default model: {status['default_model']}")
        
        print("\nRunning a test query...")
        test_result = test_ollama()
        if test_result['status'] == 'success':
            print(f"Test successful! Response time: {test_result['response_time']}")
            print(f"Response: {test_result['response'][:100]}...")
        else:
            print(f"Test failed: {test_result['message']}")