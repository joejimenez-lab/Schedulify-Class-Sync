import os
import sys
from dotenv import load_dotenv, find_dotenv
import google.generativeai as genai

# Always print immediately
sys.stdout.reconfigure(line_buffering=True)

print("🔍 Starting .env + Gemini API key test...")

# --- Load .env file ---
env_path = find_dotenv(usecwd=True)
if not env_path:
    # fallback: look one level up (from backend/app → backend)
    alt_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(alt_path):
        env_path = alt_path

if env_path:
    load_dotenv(env_path, override=True)
    print(f"✅ Loaded environment from: {os.path.abspath(env_path)}")
else:
    print("⚠️ No .env file found.")

# --- Check key presence ---
api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ No GOOGLE_API_KEY or GEMINI_API_KEY found in environment!")
    sys.exit(1)

print(f"🔑 API key starts with: {api_key[:6]}...")

# --- Validate key by calling Gemini ---
try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("models/gemini-2.0-flash")
    response = model.generate_content("Say 'pong' if this key works.")
    text = response.text.strip() if response and hasattr(response, "text") else None

    if text and "pong" in text.lower():
        print("✅ Gemini API key is valid! Response:", text)
    else:
        print("⚠️ Got a response, but not expected:", text)

except Exception as e:
    print("❌ Gemini API key test failed:")
    print(e)

print("✅ Test finished.")
