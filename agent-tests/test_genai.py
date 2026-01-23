import google.generativeai as genai
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env
env_path = Path(__file__).parent.parent / "backend" / ".env"
load_dotenv(env_path)

api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key loaded: {api_key[:10] if api_key else 'None'}...")
genai.configure(api_key=api_key)

# Test 1: Without system_instruction
print("Test 1: Without system_instruction")
try:
    model = genai.GenerativeModel(model_name="gemini-3-flash-preview")
    response = model.generate_content("Hello")
    print(f"Success: {response.text[:50]}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: With system_instruction  
print("\nTest 2: With system_instruction")
try:
    model = genai.GenerativeModel(
        model_name="gemini-3-flash-preview",
        system_instruction="You are a helpful assistant."
    )
    response = model.generate_content("Hello")
    print(f"Success: {response.text[:50]}")
except Exception as e:
    print(f"Error: {e}")
